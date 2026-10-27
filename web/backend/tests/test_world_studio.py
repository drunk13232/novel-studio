"""Focused author workflows. Captured model results are MOCK, never real AI proof."""
import copy,json
import pytest
from test_writing_assist import service,context
from app.library.world_studio import Design,Start,Result,SaveReview,Adopt,BlueprintSave,Upgrade,LinkAdopt,FieldValue
from app.library.bible import Category
from app.library.world_templates import value_schema
from app.creative.writing import ContextChoice
from app.errors import ConsoleError

def setup(service):
    s,p,root=service;return s.world_studio,p,root
def category(s,p,id='economy_test'):
    return s.bible.category(p,{'id':id,'name':'经济组织模板','fields':[{'id':'income','name':'收入来源','type':'longtext','required':True},{'id':'stock','name':'资源库存','type':'quantity','minimum':0,'unit':'kg'}]})
def result(category='country',key='country_one',name='澄屿共和国'):
    return Result(summary='候选设定，不是结论',entries=[{'key':key,'name':name,'category':category,'summary':'近未来群岛国家，公共能源预算受议会监督。','details':'能源供应不足时，必须说明补给和财政条件。','values':[]}],unknowns=['财政口径未知'],limitations=['未进行社会行为预测'])
def design(s,p,categories=['country']):return s.create(p,Design(goal='设计一个近未来国家，明确政治、经济、军事和社会条件。',categories=categories))
def reviewed(s,p,r,v=None):return s.review(p,r['id'],SaveReview(etag=r['etag'],result=v or result()))
def adopt(s,p,r,key='country_one',formal=False):return s.adopt(p,r['id'],Adopt(etag=r['etag'],entry_key=key,formal=formal,confirm=True))

def test_templates_snapshot_versions_roundtrip_and_independent_values(service):
    s,p,_=setup(service);c=category(s,p)
    a=s.bible.save(p,{'name':'北境','category':c['id'],'fields':{'income':'矿业'}})
    b=s.bible.save(p,{'name':'南岸','category':c['id'],'fields':{'income':'贸易'}})
    c['fields'].append({'id':'cost','name':'支出条件','type':'longtext','options':[]});c=s.bible.category(p,c)
    assert c['version']==2 and a['template_version']==1 and b['fields']['income']=='贸易'
    old=s.bible.get(p,a['id']);old['summary']='仅修改简介';etag=old.pop('etag');saved=s.bible.save(p,old,etag)
    assert saved['template_version']==1 and saved['fields']=={'income':'矿业'}
    package=s.template_export(p,c['id']);package['template']['id']='shared_copy';s.template_import(p,package)
    assert next(v for v in s.bible.categories(p) if v['id']=='shared_copy')['fields']==c['fields']
    bad=copy.deepcopy(c);bad['fields']=bad['fields'][1:]
    with pytest.raises(ConsoleError):s.bible.category(p,bad)

def test_required_quantity_nested_fields_and_untrusted_template(service):
    s,p,_=setup(service);c=category(s,p)
    with pytest.raises(ConsoleError):s.bible.save(p,{'name':'缺条件','category':c['id'],'status':'FORMAL'})
    with pytest.raises(ConsoleError):s.bible.save(p,{'name':'负数','category':c['id'],'fields':{'stock':{'value':-1,'unit':'kg'}}})
    c['id']='nested_test';c['fields']=[{'id':'group','name':'条件','type':'group','children':[{'id':'ref','name':'关联','type':'entity','target_types':['entity']}]}];s.bible.category(p,c)
    with pytest.raises(ConsoleError):s.bible.save(p,{'name':'越界关联','category':c['id'],'fields':{'group':{'ref':'entity_'+'f'*32}}})
    c['script']='__import__("os").system("echo unsafe")'
    with pytest.raises(Exception):s.bible.category(p,c)
    assert value_schema({'fields':[]})['$schema'].endswith('/2020-12/schema')

def test_proposals_do_not_write_until_adoption_and_stable_id_survives_retry(service):
    s,p,root=setup(service);before={str(f):f.read_bytes() for area in ['state','settings','characters','chapters'] for f in (root/area).rglob('*') if f.is_file()}
    baseline=len(s.bible.list(p));d=reviewed(s,p,design(s,p));assert len(s.bible.list(p))==baseline
    a=adopt(s,p,d);assert a['entity']['status']=='PENDING' and a['entity']['canon_level']=='REFERENCE'
    assert adopt(s,p,d)['entity']['id']==a['entity']['id'] and len(s.bible.list(p))==baseline+1
    # Simulate a crash between entity persistence and adoption receipt persistence.
    row=s.get(p,d['id']);row['adoptions']={};s.save(p,row);again=adopt(s,p,s.get(p,d['id']))
    assert again['entity']['id']==a['entity']['id'] and len(s.bible.list(p))==baseline+1
    assert all(__import__('pathlib').Path(f).read_bytes()==v for f,v in before.items())

def test_formal_confirmation_per_item_edit_and_source_staleness(service):
    s,p,root=setup(service);d=design(s,p);v=result();v.entries.append(v.entries[0].model_copy(update={'key':'country_two','name':'另一国家'}));d=reviewed(s,p,d,v)
    first=adopt(s,p,d,formal=True);assert first['entity']['status']=='FORMAL'
    d=first['design'];v=Result(**d['result']);v.entries[1].summary='只改未采用条目';d=reviewed(s,p,d,v)
    assert adopt(s,p,d,'country_two')['entity']['summary']=='只改未采用条目'
    with pytest.raises(ConsoleError):s.get(p+'bad',d['id'])
    src=first['entity'];d=s.create(p,Design(goal='深化所选设定',categories=['country'],entity_ids=[src['id']]))
    old=s.bible.get(p,src['id']);etag=old.pop('etag');old['summary']='作者改变前提';s.bible.save(p,old,etag,True)
    with pytest.raises(ConsoleError):s.current_sources(p,d)

def test_writer_only_uses_explicit_safe_summary_and_pov_scope(service):
    s,p,_=setup(service);d=reviewed(s,p,design(s,p));e=adopt(s,p,d,formal=True)['entity']
    c=context(service);raw=copy.deepcopy(c['choice']);raw['world_ids']=[e['id']]
    with pytest.raises(ConsoleError):s.writing.preview(p,ContextChoice(**raw))
    e['writer_view']='本地能源设施无法脱离燃料长期运作。';e['writer_known_by']=[c['packet']['pov']];e['details']='作者秘密不得进入 Writer';etag=e.pop('etag')
    with pytest.raises(ConsoleError):s.bible.save(p,e,etag)
    e=s.bible.save(p,e,etag,True);package=s.writing.preview(p,ContextChoice(**raw))
    text=json.dumps(package['packet'],ensure_ascii=False);assert e['writer_view'] in text and '作者秘密不得进入 Writer' not in text

def capture(s,p,monkeypatch):
    box={}
    # Retain the actual new source-control contract while intercepting execution.
    from app.creative.tasks import adapter as real_adapter
    def dry_adapter(*args,**kwargs):
        kwargs['preview']=True
        a=real_adapter(*args,**kwargs);a.selected_ai['backend']='MOCK_VALIDATION_NOT_REAL_AI';return a
    monkeypatch.setattr('app.library.world_studio.adapter',dry_adapter)
    class T:
        id='world-fixture';private_text=False;status='RUNNING';error=None
        def public(self):return {'id':self.id,'status':self.status}
    def prepared(*args,**kw):box.update(prompt=args[1],complete=args[5],task=T(),schema=args[4]);return box['task']
    monkeypatch.setattr(s.manager(p),'prepared',prepared);return box

def test_bounded_actual_template_prompt_checkpoint_and_cancelled_late_result(service,monkeypatch):
    s,p,_=setup(service);baseline=len(s.bible.list(p));c=category(s,p);d=design(s,p,[c['id'],'city']);box=capture(s,p,monkeypatch)
    task=s.start(p,d['id'],Start(etag=d['etag'],batch=0,confirm_send=True));assert '收入来源' in box['prompt'] and 'METHOD world' in box['prompt']
    v=result(c['id']);v.entries[0].values=[FieldValue(id='income',value_json='"贸易"',basis='AI_PROPOSED')]
    box['complete'](v.model_dump_json());row=s.get(p,d['id']);assert row['batches'][0]['status']=='DONE' and row['batches'][1]['status']=='NOT_RUN'
    assert row['batches'][0]['methods'][0]['sha256'] and len(s.bible.list(p))==baseline
    box=capture(s,p,monkeypatch);s.start(p,d['id'],Start(etag=row['etag'],batch=1,confirm_send=True));row=s.get(p,d['id']);row['batches'][1].update(status='CANCELLED',token='');s.save(p,row)
    with pytest.raises(ConsoleError):box['complete'](result('city','city_one').model_dump_json())
    assert s.get(p,d['id'])['batches'][0]['status']=='DONE'

def test_ai_cannot_invent_unknown_numbers_or_author_locked_fields(service):
    s,p,_=setup(service);c=category(s,p);d=design(s,p,[c['id']]);v=result(c['id']).model_dump()
    v['entries'][0]['values']=[{'id':'stock','value_json':'{"value":100,"unit":"kg"}','basis':'UNKNOWN','source_id':'','quote':'','uncertainty':''}]
    with pytest.raises(ConsoleError):s.validate_result(d,v)
    v['entries'][0]['values'][0].update(id='income',value_json='"猜测"',basis='SOURCE_QUOTE',quote='不存在的引用',source_id='not-authorized')
    with pytest.raises(ConsoleError):s.validate_result(d,v)

def test_blueprint_optimistic_save_and_no_auto_canon(service):
    s,p,root=setup(service);baseline=s.bible.list(p);rules=(root/'settings/rules.md').read_bytes() if (root/'settings/rules.md').exists() else None;v=s.blueprint(p);b=BlueprintSave(etag=v['etag'],value={'name':'临时反事实世界','rules':'仅为实验假设，不写正式规则'})
    saved=s.blueprint_save(p,b);assert saved['value']['name']==b.value.name
    with pytest.raises(ConsoleError):s.blueprint_save(p,b)
    assert s.bible.list(p)==baseline
    assert ((root/'settings/rules.md').read_bytes() if (root/'settings/rules.md').exists() else None)==rules

def test_template_upgrade_preview_preserves_values_and_source_bound_links(service):
    s,p,_=setup(service);c=category(s,p);e=s.bible.save(p,{'name':'北方工业','category':c['id'],'fields':{'income':'轻工业'}})
    c['fields'].append({'id':'workforce','name':'劳动组织','type':'longtext'});c=s.bible.category(p,c)
    preview=s.upgrade_preview(p,e['id']);assert preview['added_fields']==['劳动组织'] and preview['values_preserved']
    e=s.upgrade(p,e['id'],Upgrade(etag=e['etag'],confirm=True));assert e['template_version']==2 and e['fields']=={'income':'轻工业'}
    d=design(s,p,['country','city']);v=result();v.entries.append(result('city','capital_city','澄屿港').entries[0]);v.relations=[{'source':'capital_city','target':'country_one','relation':'属于','basis':'作者选定的行政关系候选'}]
    d=reviewed(s,p,d,v)
    with pytest.raises(ConsoleError):s.adopt_link(p,d['id'],LinkAdopt(etag=d['etag'],index=0,confirm=True))
    d=adopt(s,p,d)['design'];d=adopt(s,p,d,'capital_city')['design'];link=s.adopt_link(p,d['id'],LinkAdopt(etag=d['etag'],index=0,confirm=True))
    assert s.adopt_link(p,d['id'],LinkAdopt(etag=d['etag'],index=0,confirm=True))['reused']
    assert link['relation']['target_id']==d['adoptions']['country_one']

def test_exact_selection_extraction_and_stale_writer_release(service):
    s,p,root=setup(service);c=context(service,'港口的货运塔在雾里熄灯。')
    d=s.create(p,Design(goal='仅提取选段中明确描述的城市条件',mode='extract',categories=['city'],selection={'path':c['choice']['path'],'revision':c['choice']['revision'],'quote':'货运塔在雾里熄灯'}))
    assert d['sources'][0]['text']=='货运塔在雾里熄灯'
    bad=Design(goal='伪造引用',mode='extract',categories=['city'],selection={'path':c['choice']['path'],'revision':c['choice']['revision'],'quote':'没有的摩天塔'})
    with pytest.raises(ConsoleError):s.create(p,bad)
    (root/c['choice']['path']).write_text('作者修订了这一段。','utf8')
    with pytest.raises(ConsoleError):s.current_sources(p,d)

def test_real_http_mutations_borrow_held_os_lease_without_relocking(service):
    s,p,_=setup(service)
    from app.main import create_app
    from app.config import Settings
    from fastapi.testclient import TestClient
    app=create_app(Settings(workspace=s.registry.engine));app.state.testing=True
    with TestClient(app) as client:
        token=client.get('/api/session').json()['request_token'];headers={'x-novel-request':token}
        prefix='/api/projects/'+p+'/world-studio'
        current=client.get(prefix).json()['blueprint'];current['value']['name']='HTTP 隔离验证'
        response=client.put(prefix+'/blueprint',json=current,headers=headers)
        assert response.status_code==200,response.text
        d=client.post(prefix+'/designs',json=Design(goal='只创建待审候选',categories=['country']).model_dump(),headers=headers).json()
        response=client.put(prefix+'/designs/'+d['id'],json={'etag':d['etag'],'result':result().model_dump()},headers=headers)
        assert response.status_code==200,response.text
        d=response.json();response=client.post(prefix+'/designs/'+d['id']+'/adopt',json={'etag':d['etag'],'entry_key':'country_one','confirm':True,'formal':False},headers=headers)
        assert response.status_code==200,response.text
        assert response.json()['entity']['status']=='PENDING'

def test_existing_entity_revision_requires_explicit_adoption_and_respects_locks(service):
    s,p,_=setup(service);original=s.bible.save(p,{'name':'原有国家','category':'country','summary':'原设定','status':'FORMAL','canon_level':'HARD','locked_fields':['name']})
    d=s.create(p,Design(goal='深化已有国家的社会日常，保留锁定名称',mode='expand',categories=['country'],entity_ids=[original['id']]))
    v=result(name='试图改名');v.entries[0].target_id=original['id'];d=reviewed(s,p,d,v)
    with pytest.raises(ConsoleError):adopt(s,p,d,formal=True)
    v.entries[0].name=original['name'];d=reviewed(s,p,d,v)
    with pytest.raises(ConsoleError):adopt(s,p,d,formal=False)
    saved=adopt(s,p,d,formal=True);assert saved['entity']['id']==original['id'] and saved['entity']['canon_level']=='HARD'
    assert saved['entity']['locked_fields']==['name'] and saved['entity']['summary']!='原设定'
    assert adopt(s,p,d,formal=True)['reused']

def test_status_refresh_never_overwrites_a_just_completed_batch(service,monkeypatch):
    s,p,_=setup(service);d=design(s,p);d['batches'][0].update(status='RUNNING',task_id='mock-race');s.save(p,d)
    class T:status='SUCCEEDED';error=None
    def complete_during_status_read(id):
        fresh=s.get(p,d['id']);fresh['batches'][0]['status']='DONE';fresh['result']=result().model_dump();s.save(p,fresh);return T()
    monkeypatch.setattr(s.manager(p),'get',complete_during_status_read)
    current=s.refresh(p,d['id']);assert current['batches'][0]['status']=='DONE' and len(current['result']['entries'])==1
