"""Local deterministic evidence checks; model fixtures are explicitly MOCK."""
import asyncio,copy,json,time
from pathlib import Path
import pytest
from test_writing_assist import service,context,approve
from test_literary_evaluation import setup,request,create,output,batch
from test_workflow_reliability import prepared
from app.creative.narrative_memory import temporal_state,inspect,Query,cached_revision
from app.creative.state_view import read_state
from app.creative.evaluation_models import Bridge
from app.creative.state_bridge import Commit,commit
from app.errors import ConsoleError

def history(s,p,root,count=40):
    import importlib.util
    spec=importlib.util.spec_from_file_location('long_form_fixture',Path(__file__).resolve().parents[3]/'scripts/long_form_fixture.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.seed(s,p,root,count)

def test_40_chapter_historical_holder_condition_and_originals_unchanged(service):
    s,p,root=service;w,state,a,b=history(s,p,root);before=w.digest(state)
    cases=[(11,'完好',a),(12,'损坏',a),(30,'损坏',a),(37,'修复',a),(40,'可用',b)]
    for n,status,holder in cases:
        projection,audit=temporal_state(s.registry.workspace(p),s.registry.engine,state,n)
        item=projection['items.yaml']['items']['TEST_WEAPON'];assert item['status']==status and item['holder']==holder
        assert audit['history_status']=='VERIFIED_PROJECTION'
    earlier,_=temporal_state(s.registry.workspace(p),s.registry.engine,state,40,'2041-10-02T05:00:00+08:00')
    assert earlier['items.yaml']['items']['TEST_WEAPON']['status']=='损坏'
    assert w.digest(read_state(s.registry.workspace(p),s.registry.engine))==before

def test_missing_or_stale_history_is_unknown_not_latest_profile(service):
    s,p,root=service;w,state,a,b=history(s,p,root)
    (root/'state/proposed/isolated-40.yaml').rename(root/'state/proposed/isolated-40.hidden')
    value,audit=temporal_state(s.registry.workspace(p),s.registry.engine,state,20)
    assert audit['history_status']=='UNKNOWN' and not value['items.yaml']
    (root/'state/proposed/isolated-40.hidden').rename(root/'state/proposed/isolated-40.yaml')
    (root/'chapters/chapter-12/draft.txt').write_text('作者已修订，不再证明原状态。','utf8')
    value,audit=temporal_state(s.registry.workspace(p),s.registry.engine,state,40)
    assert 'STATE_SOURCE_STALE' in audit['warnings'] and not value['knowledge-state.yaml']['facts']

def test_unrecorded_runtime_change_cannot_claim_verified_projection(service):
    s,p,root=service;w,state,a,b=history(s,p,root);state['items.yaml']['items']['TEST_WEAPON']['holder']='unrecorded'
    value,audit=temporal_state(s.registry.workspace(p),s.registry.engine,state,40)
    assert audit['history_status']=='UNKNOWN' and 'INCOMPLETE_PATCH_LINEAGE' in audit['warnings']
    assert not value['items.yaml']

def test_warm_history_cache_no_rehash_and_foreign_actor_rejected(service):
    s,p,root=service;w,state,a,b=history(s,p,root)
    temporal_state(s.registry.workspace(p),s.registry.engine,state,30);first=cached_revision.cache_info()
    temporal_state(s.registry.workspace(p),s.registry.engine,state,30);second=cached_revision.cache_info()
    assert second.misses==first.misses and second.hits>=first.hits+40
    with pytest.raises(ConsoleError):inspect(s,p,Query(character_id='foreign'))
    with pytest.raises(ConsoleError):inspect(s,p,Query(story_time='2041-10-01'))

def test_fts_filters_numeric_chapter_before_limit_and_does_not_promote_claim(service):
    s,p,root=service;w,state,a,b=history(s,p,root,120)
    hits=s.tools.search(p,'隔离原文',before_chapter=12)
    assert hits and all(int(h['number'])<12 for h in hits) and max(int(h['number']) for h in hits)==11
    assert int(s.tools.search(p,'原文',before_chapter=12)[0]['number'])==11
    r=inspect(s,p,Query(through_chapter=30,queries=['猜测'],character_id=a))
    assert r['evidence'] and all(e['basis']=='TEXT_NOT_OBJECTIVE_FACT' for e in r['evidence'])
    assert not r['knowledge']['known'] and r['writer_context'] is False

def test_real_commit_gate_still_supplies_next_writer_context(service):
    s,p,root,c,w,v=prepared(service)
    commit(s,p,Commit(path=c['choice']['path'],revision=c['choice']['revision'],proposal_id=v['proposal_id'],proposal_sha256=w.digest(v),base_sha256=v['base_sha256'],confirm=True))
    path='chapters/chapter-3/draft.txt';(root/path).parent.mkdir(exist_ok=True);(root/path).write_text('江予把钥匙放进衣袋。','utf8')
    from app.creative.writing import ContextChoice
    doc=s.tools.doc(p,path);packet=s.preview(p,ContextChoice(path=path,revision=doc['etag'],pov=c['packet']['pov']))
    assert '测试钥匙已经交还' in json.dumps(packet['packet'],ensure_ascii=False)

def editorial_output(packet,invalid=False):
    data=json.loads(packet.split('\nEVALUATION_DATA\n')[1]);value=json.loads(output(packet))
    if 'full_text_segments' in data:
        src=data['full_text_segments'][0];q={'source_id':src['source_id'],'quote':src['text'][:24]}
    else:q=data['completed_full_text_reading_cards'][0]['assessment']['editorial']['findings'][0]['evidence'][0]
    value['editorial']={'declared_lens':'尊重非线性叙事和开放结局。','intended_shape':'根据作者目标核对人物选择。','set_aside_rules':['不强制积极成长。'],'findings':[{'dimension':'thought','priority':'MEDIUM','classification':'AI_INTERPRETATION','diagnosis':'需要作者核对人物选择的代价。','why':'局部证据只支持条件性解释。','evidence':[{**q,'quote':'模型伪造的证据'}] if invalid else [q],'alternatives':['停顿也可以是有意留白。'],'revision_options':['作者可以选择保留。'],'tradeoffs':'解释更多可能损伤留白。','uncertainty':'MOCK 结构验证，不是真实文学判断。'}],'questions':[]}
    return json.dumps(value,ensure_ascii=False)

def test_editorial_reuses_full_reading_checkpoints_no_score_and_existing_todo(service,monkeypatch):
    ev,p,root=setup(service,monkeypatch);seen=[]
    def call(a,packet,*args,**kw):seen.append(packet);return {'status':'completed','output':editorial_output(packet)}
    monkeypatch.setattr('app.creative.tasks.call',call)
    req=request(ev,p);req.purpose='editorial';req.editorial_goal='只检查思想与人物行动，不强制成长。'
    job=create(ev,p,req);result=asyncio.run(batch(ev,p,job['id']))
    assert result['status']=='COMPLETED' and result['models'][0]['weighted']['score'] is None
    assert result['models'][0]['coverage']['result_available'] and not result['models'][0]['coverage']['final_score_available']
    actual=result['models'][0]['result'];assert actual['editorial_anchors'][0]['evidence'] and 'professional_methods' in seen[0]
    raw=ev.raw(p,job['id']);raw['last_error']='Earlier interrupted attempt';ev.put(p,raw)
    result=ev.get(p,job['id']);assert not result['last_error'] and result['previous_attempt_error']=='Earlier interrupted attempt'
    bridge=ev.bridge(p,job['id'],Bridge(model=0,node=result['root_node'],dimension='thought',editorial_issue=0,etag=result['etag'],confirm=True))
    from app.creative.reviews import Decide
    report=ev.center.get(p,bridge['review_id']);ev.center.decide(p,bridge['review_id'],Decide(etag=report['etag'],issue=0,action='todo'))
    assert ev.center.get(p,bridge['review_id'])['decisions']['0']['saved_as_revision_item']

def test_invalid_editorial_quote_withdrawn_and_past_score_records_compatible(service,monkeypatch):
    ev,p,root=setup(service,monkeypatch);req=request(ev,p);req.purpose='editorial';job=create(ev,p,req);row=ev.raw(p,job['id']);node=row['nodes'][0];packet=ev.packet(p,row,node,0)
    r=ev.validate_result(p,row,node,0,editorial_output(packet,True))
    assert r['assessment']['editorial']['findings'][0]['classification']=='INSUFFICIENT_EVIDENCE' and r['withdrawn_quotes']
    assert not r['editorial_anchors'][0]['evidence'] and r['weighted']['score'] is None

def test_cold_frozen_source_metadata_does_not_read_all_bodies_per_check(service,monkeypatch):
    ev,p,root=setup(service,monkeypatch)
    for n in range(3,43):
        f=root/f'chapters/chapter-{n}/draft.txt';f.parent.mkdir(exist_ok=True);f.write_text(f'第{n}章。江予回到门口。','utf8')
    job=create(ev,p,request(ev,p,'book'));row=ev.raw(p,job['id']);counter=[]
    monkeypatch.setattr(ev,'source',lambda *a:(_ for _ in ()).throw(AssertionError('snapshot body loaded during metadata freshness check')))
    assert ev.current(p,row)['is_current']
    (root/'chapters/chapter-17/draft.txt').write_text('作者修改。','utf8')
    assert not ev.current(p,row)['is_current']

def test_editorial_grouped_full_text_coverage_and_exact_unit_boundaries(service,monkeypatch):
    ev,p,root=setup(service,monkeypatch)
    for n in range(3,43):
        f=root/f'chapters/chapter-{n}/draft.txt';f.parent.mkdir(exist_ok=True);f.write_text(f'第{n}章。独立阅读段落编号{n}。','utf8')
    req=request(ev,p,'book');req.purpose='editorial';job=create(ev,p,req);row=ev.raw(p,job['id']);leaves=[n for n in row['nodes'] if n['stage']=='read']
    assert len(leaves)<row['source_count'] and all(len(n['source_ids'])<=6 for n in leaves)
    assert sum(n['end']-n['start'] for n in leaves)==sum(s['length'] for s in row['source_manifest'])
    node=leaves[0];packet=ev.packet(p,row,node,0)
    data=json.loads(packet.split('\nEVALUATION_DATA\n')[1]);assert {s['source_id'] for s in data['full_text_segments']}==set(node['source_ids'])
    assert data['maximum_horizon']=='SELECTED_RANGE'
    assert not ev.coverage(row,0)['final_score_available'] and ev.coverage(row,0)['status']=='PARTIAL_COVERAGE'

def test_chapter_cache_invalidates_changes_and_never_shares_mutable_rows(service):
    s,p,root=service;planning=s.tools.planning
    original=planning.rows(p,'chapter');id=original[0]['id'];original[0]['title']='仅修改返回值'
    assert planning.rows(p,'chapter')[0]['title']!='仅修改返回值'
    file=root/'outlines/chapters'/f'{id}.yaml';value=s.registry.workspace(p).yaml_file(file.relative_to(root).as_posix());value['title']='作者修改后的标题'
    from app.projects.service import write_yaml
    write_yaml(file,value);assert planning.rows(p,'chapter')[0]['title']=='作者修改后的标题'

def test_memory_http_reuses_mutation_lease_and_no_remote_calls(service):
    s,p,root=service;history(s,p,root)
    # Test the actual app route/middleware, not just the pure projection.
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import Settings
    client=TestClient(create_app(Settings(workspace=root.parent.parent)),base_url='http://127.0.0.1')
    token=client.get('/api/session').json()['request_token']
    r=client.post('/api/projects/'+p+'/writing-assist/memory',headers={'X-Novel-Request':token},json={'through_chapter':30,'queries':['原文']})
    assert r.status_code==200,r.text
    assert r.json()['audit']['cutoff']==30
    with pytest.raises(ConsoleError):
        from app.creative.evaluation import Evaluation
        Evaluation(s.literary_core.reviews,s.literary_core).document(p,'state/knowledge-state.yaml')

def test_legacy_timeline_list_patches_keep_index_semantics(service):
    s,p,root=service;w,state,a,b=history(s,p,root);events=[]
    for n in [12,38]:
        v=w.y.read(root/f'state/proposed/isolated-{n}.yaml');e={'id':'HIST_E'+str(n),'chapter':n,'story_time':v['author_state_time']['value'],'writer_view':[]}
        v['extraction']['operations'].append({'file':'timeline.yaml','pointer':'/events/'+str(len(events)),'before':None,'after':e,'evidence':'隔离原文'});events.append(e)
        w.y.write(root/f'state/proposed/isolated-{n}.yaml',v);state['chapter-ledger.yaml']['entries'][n-1]['proposal_sha256']=w.digest(v)
    w.y.write(root/'state/timeline.yaml',{'events':events});w.y.write(root/'state/chapter-ledger.yaml',state['chapter-ledger.yaml'])
    state=read_state(s.registry.workspace(p),s.registry.engine);result,audit=temporal_state(s.registry.workspace(p),s.registry.engine,state,20)
    assert audit['history_status']=='VERIFIED_PROJECTION'
    assert set(result['timeline.yaml']['events'])=={'HIST_E12'}
