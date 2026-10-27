"""Focused deterministic checks. No mocked response counts as real AI evidence."""
import copy,io,json
from pathlib import Path
import pytest
from test_writing_assist import service,context
from app.errors import ConsoleError
from app.library.world_model import WorldModel,Prepare,SaveExperiment,Evidence
from app.library.world_rules import historical,writer_summary
from app.world_logic.engine import run

def model(service):
    s,p,root=service
    return WorldModel(s.world_studio,s.registry.knowledge,s.references),p,root

def definition(name='custom-constraint'):
    path=Path(__file__).parents[1]/'app/world_logic/resources/templates'/f'{name}.json'
    value=json.loads(path.read_text('utf8'))
    for a in value['assumptions']:a['accepted']=True
    return {k:value[k] for k in ['solver','inputs','constraints','outputs','acceptance_rules','assumptions','limitations']}

def rule(m,p,name='传送需要能源',formal=None,**fields):
    f={'rule_kind':'魔法能力','rule_strength':'HARD','rule_scope':'WORLD','confidence':'AUTHOR_CONFIRMED',**fields}
    if formal is not None:f['formal_model']=json.dumps(formal,ensure_ascii=False)
    return m.bible.save(p,{'name':name,'category':'world_rule','summary':name,'fields':f,'status':'FORMAL','writer_view':'传送必须支付能源代价。','writer_public':True},approve=True)

def test_rule_cards_use_bible_templates_versions_and_writer_release(service):
    m,p,root=model(service);e=rule(m,p,formal=definition())
    assert e['template_snapshot']['id']=='world_rule'
    old=e['etag'];e['summary']='能源阈值经作者补充';e.pop('etag');e=m.bible.save(p,e,old,True)
    assert e['version']==2 and list((root/'history/revisions').glob('*/revision.json'))
    c=context(service,world_ids=[e['id']]);assert '传送必须支付能源代价' in json.dumps(c['packet'],ensure_ascii=False)
    pending=m.bible.save(p,{'name':'AI 候选','category':'world_rule','source':'AI_PROPOSED'})
    assert pending['status']=='PENDING'

def test_solver_maps_unsat_core_to_rules_then_changes_with_real_input(service):
    m,p,_=model(service);a=rule(m,p,formal=definition())
    opposite=definition();opposite['constraints'][0].update(expression='energy < cost',meaning='相反约束')
    b=rule(m,p,'相反能源限制',opposite)
    prepared=m.prepare(p,Prepare(rule_ids=[a['id'],b['id']]))
    r=run(prepared['definition']);assert r['status']=='FAIL' and r['solver_result']['status']=='UNSAT'
    sources={s['id']:s['target_id'] for s in prepared['definition']['source_references']}
    assert {sources[sid] for item in r['solver_result']['unsat_core'] for sid in item['source_ids']}=={a['id'],b['id']}
    r=run(m.prepare(p,Prepare(rule_ids=[a['id']]))['definition']);assert r['status']=='PASS'
    old=b.pop('etag');b['fields']['formal_model']=json.dumps(definition());m.bible.save(p,b,old,True)
    assert run(m.prepare(p,Prepare(rule_ids=[a['id'],b['id']]))['definition'])['status']=='PASS'

def test_soft_scope_conditions_and_unmapped_rules_never_become_proof(service):
    m,p,_=model(service)
    a=rule(m,p,formal=definition(),conditions='设备正常',exceptions='紧急传送另有规则')
    assert run(m.prepare(p,Prepare(rule_ids=[a['id']]))['definition'])['status']=='INCONCLUSIVE'
    assert run(m.prepare(p,Prepare(rule_ids=[a['id']],accepted_conditions=[a['id']]))['definition'])['status']=='PASS'
    b=rule(m,p,'多数人住在城市',definition(),rule_strength='SOFT')
    d=m.prepare(p,Prepare(rule_ids=[b['id']]))['definition'];assert not d['constraints'] and d['acceptance_rules'][0]['type']=='QUALITATIVE'
    c=rule(m,p,'未知模型');assert run(m.prepare(p,Prepare(rule_ids=[c['id']]))['definition'])['status']=='INCONCLUSIVE'
    a['fields']['rule_scope']='SCENARIO'
    with pytest.raises(ConsoleError):writer_summary(a,'2041-10-03T00:00:00+08:00',[],None)

def test_mapping_is_version_bound_and_draft_only(service):
    m,p,root=model(service);e=rule(m,p,formal=definition());request=Prepare(rule_ids=[e['id']]);prepared=m.prepare(p,request)
    draft=m.experiment(p,SaveExperiment(**request.model_dump(),mapping_hash=prepared['mapping_hash'],confirm=True))
    assert draft['status']=='DRAFT' and draft['latest_version']==0
    old=e.pop('etag');e['summary']='作者改了前提';m.bible.save(p,e,old,True)
    with pytest.raises(ConsoleError):m.experiment(p,SaveExperiment(**request.model_dump(),mapping_hash=prepared['mapping_hash'],confirm=True))


def test_matching_time_cannot_override_entity_or_scenario_scope(service):
    m,p,_=model(service)
    target=rule(m,p,'指定对象')
    e=rule(m,p,formal=definition(),rule_scope='ENTITY',scope_ids=[target['id']])
    etag=e.pop('etag');e['valid_from']='2040-01-01';e['valid_to']='2050-01-01';e=m.bible.save(p,e,etag,True)
    missing=m.prepare(p,Prepare(rule_ids=[e['id']],story_time='2041-01-01'))
    assert missing['mapping'][0]['scope_status']=='UNKNOWN'
    assert run(missing['definition'])['status']=='INCONCLUSIVE'
    matched=m.prepare(p,Prepare(rule_ids=[e['id']],scope_ids=[target['id']],story_time='2041-01-01'))
    assert matched['mapping'][0]['scope_status']=='MATCH'
    etag=e.pop('etag');e['fields']['rule_scope']='SCENARIO';e=m.bible.save(p,e,etag,True)
    sandbox=m.prepare(p,Prepare(rule_ids=[e['id']],story_time='2041-01-01'))
    assert sandbox['mapping'][0]['scope_status']=='UNKNOWN'
    assert run(sandbox['definition'])['status']=='INCONCLUSIVE'


def test_current_math_cannot_backfill_a_historical_rule_model(service):
    m,p,_=model(service);e=rule(m,p,formal=definition())
    etag=e.pop('etag');e['periods']=[{'label':'旧时期','story_start':'2000-01-01','story_end':'2020-01-01','confirmed':True,'facts':{'代价':'未知'},'writer_view':'旧时期的消耗尚未确定。'}]
    e=m.bible.save(p,e,etag,True)
    prepared=m.prepare(p,Prepare(rule_ids=[e['id']],story_time='2010-01-01'))
    assert prepared['mapping'][0]['status']=='HISTORICAL_MODEL_UNAVAILABLE'
    assert not prepared['definition']['constraints']
    assert run(prepared['definition'])['status']=='INCONCLUSIVE'

def test_history_uses_confirmed_story_periods_not_latest_fields(service):
    m,p,_=model(service)
    periods=[{'label':'早期','story_start':'2000-01-01T00:00:00+08:00','story_end':'2020-01-01T00:00:00+08:00','confirmed':True,'facts':{'制度':'城市议会','技术':'燃料机'},'writer_view':'国家由城市议会治理。'},
             {'label':'晚期','story_start':'2020-01-01T00:00:00+08:00','confirmed':True,'facts':{'制度':'联邦议会','技术':'储能网'},'writer_view':'国家使用储能网。'}]
    e=m.bible.save(p,{'name':'潮屿国','category':'country','status':'FORMAL','fields':{'law':'最新字段不能倒推过去'},'periods':periods,'writer_view':'最新时期摘要','writer_public':True},approve=True)
    a=m.memory(p,id=e['id'],at='2010-01-01T00:00:00+08:00');b=m.memory(p,id=e['id'],at='2041-10-03T00:00:00+08:00')
    assert a['facts'][0]['historical']['facts']['制度']=='城市议会' and b['facts'][0]['historical']['facts']['制度']=='联邦议会'
    assert m.memory(p,id=e['id'],at='1990-01-01T00:00:00+08:00')['facts'][0]['historical']['status']=='UNKNOWN'
    assert '最新字段' not in json.dumps(a,ensure_ascii=False)
    e['periods'].append(periods[0]);assert historical(e,'2010-01-01T00:00:00+08:00')['status']=='CONFLICT'
    assert m.memory(p,q='二十年前的制度')['status']=='NEEDS_BOUNDARY'


def test_explicit_cross_project_copy_does_not_release_historical_evidence(service):
    import shutil
    m,p,root=model(service);target='novel_'+'f'*32;destination=root.parent/target
    shutil.copytree(Path(__file__).parents[3]/'desktop/preview-template/projects'/p,destination)
    manifest=destination/'project.yaml';manifest.write_text(manifest.read_text('utf8').replace(p,target),'utf8')
    e=m.bible.save(p,{'name':'历史条目','category':'country','status':'FORMAL','periods':[{'label':'早期','story_start':'2000-01-01','confirmed':True,'writer_view':'本作品已发布摘要','facts':{'制度':'议会'},'source_references':[{'kind':'manuscript','path':'chapters/chapter-1/final.txt'}]}]},approve=True)
    copied=m.bible.copy(p,e['id'],target)['entity']
    assert copied['status']=='DRAFT' and not copied['writer_public']
    period=copied['periods'][0]
    assert not period['confirmed'] and not period['writer_view'] and not period['source_references']
    assert m.bible.get(p,e['id'])['periods'][0]['confirmed']

def test_fts_memory_reuses_index_and_revalidates_updated_entries(service):
    m,p,_=model(service);e=rule(m,p,'空间传送能源规则',definition())
    a=m.memory(p,'空间传送');assert any(r['id']==e['id'] for r in a['facts'])
    old=e.pop('etag');e['summary']='冷却晶体限制';m.bible.save(p,e,old,True)
    assert any(r['id']==e['id'] for r in m.memory(p,'冷却晶体')['facts'])
    with pytest.raises(ConsoleError):m.memory(p+'invalid','能源')

def test_no_executable_formulas_or_remote_template_access(service):
    m,p,_=model(service);bad=definition();bad['constraints'][0]['expression']='__import__("os").system("echo bad")'
    with pytest.raises(ConsoleError):rule(m,p,formal=bad)

def test_manuscript_citation_is_versioned_and_never_changes_body(service):
    m,p,root=model(service);c=context(service,body='传送门必须有能源核心才能启动。');e=rule(m,p)
    before=(root/c['choice']['path']).read_bytes()
    e=m.attach(p,e['id'],Evidence(etag=e['etag'],kind='manuscript',path=c['choice']['path'],revision=c['choice']['revision'],quote='传送门必须有能源核心才能启动。',confirm=True))
    assert m.evidence(p,e['id'])['sources'][0]['current']=='CURRENT'
    assert (root/c['choice']['path']).read_bytes()==before
    (root/c['choice']['path']).write_text('作者另改正文。','utf8')
    assert m.evidence(p,e['id'])['sources'][0]['current']=='STALE'

def test_counterfactual_reuses_frozen_lab_baseline_and_keeps_criteria(service):
    from app.world_logic.models import Freeze
    from app.world_logic.service import Scenario
    m,p,_=model(service);e=rule(m,p,'能源库存收支',definition('resources'))
    b=Prepare(rule_ids=[e['id']],solver='formula');prepared=m.prepare(p,b)
    experiment=m.experiment(p,SaveExperiment(**b.model_dump(),mapping_hash=prepared['mapping_hash'],confirm=True))
    frozen=m.lab.freeze(p,experiment['id'],Freeze(etag=experiment['etag'],reason='确认演示模型与标准',confirm=True))
    baseline=copy.deepcopy(frozen['frozen'])
    scenario=m.lab.scenario(p,experiment['id'],Scenario(version=1,changes={'production':7.2},note='能源供应下降 40%',name='Scenario A'))
    assert m.lab.version(p,experiment['id'],1)==baseline
    assert run(baseline['definition'])['outputs'][0]['value']==110
    altered=run(scenario['definition']);assert altered['status']=='FAIL' and altered['outputs'][0]['value']==pytest.approx(-34)
    assert scenario['definition']['acceptance_rules']==baseline['definition']['acceptance_rules']

def test_impact_uses_explicit_dependencies_and_preserves_other_links(service):
    from app.library.world_model import RuleLink
    m,p,_=model(service);a=rule(m,p,'能源来源');b=rule(m,p,'传送设备');c=rule(m,p,'文化象征')
    m.link(p,b['id'],RuleLink(target_id=a['id'],relation='RULE_REQUIRES',etag=m.knowledge.associations(p)['etag'],confirm=True))
    m.link(p,c['id'],RuleLink(target_id=a['id'],relation='RULE_ASSOCIATED',etag=m.knowledge.associations(p)['etag'],confirm=True))
    result=m.impact(p,a['id']);assert [x['id'] for x in result['actual_dependents']]==[b['id']]
    assert len(result['ordinary_links'])==1 and not result['ai_possible']

@pytest.mark.parametrize('kind,text,expected',[('md','# 能源\n能源来源有限。','第 2 行'),('json','{"energy":{"stock":100}}','/energy/stock'),('yaml','energy:\n  stock: 100','/energy/stock'),('csv','name,stock\n能源,100','第 2 行'),('html','<h1>能源</h1><p>供应有限</p><script>alert(1)</script>','文本块')])
def test_real_text_parsers_preserve_format_specific_locations(tmp_path,monkeypatch,kind,text,expected):
    from app.library import document_parse as parser
    monkeypatch.setattr(parser,'memory_limit',lambda:None)
    source=tmp_path/('source.'+kind);source.write_text(text,'utf8');out=tmp_path/'out.json'
    parser.extract_worker(str(source),kind,str(out));result=json.loads(out.read_text('utf8'))
    assert result['status']=='READY' and any(expected in u['label'] for u in result['units'])
    assert 'alert(1)' not in json.dumps(result,ensure_ascii=False)

def test_reference_note_hash_offsets_and_stale_status(service,tmp_path,monkeypatch):
    from app.library import document_parse as parser
    from app.library.storage import write,safe
    m,p,_=model(service);monkeypatch.setattr(m.references,'parse',lambda *a:None)
    d=m.references.upload(p,b'{"energy":100}','energy.json','reference')
    monkeypatch.setattr(parser,'memory_limit',lambda:None)
    output=safe(m.references.root(p),'extracted/'+d['id']+'.json')
    parser.extract_worker(str(safe(m.references.root(p),d['original'])),'json',str(output))
    n=m.references.note(p,d['id'],{'unit_id':'1','quote':'100'})
    assert m.references.citation_status(p,n)['status']=='VERIFIED'
    assert n['location']['locator']['pointer']=='/energy'
    e=rule(m,p);e=m.attach(p,e['id'],Evidence(etag=e['etag'],note_id=n['id'],confirm=True))
    assert m.evidence(p,e['id'])['sources'][0]['current']=='CURRENT'
    safe(m.references.root(p),d['original']).write_text('{"energy":60}','utf8')
    assert m.references.citation_status(p,n)['status']=='STALE'
    assert m.evidence(p,e['id'])['sources'][0]['current']=='STALE'
