"""Focused writing adapters: synthetic model outputs test guards, not AI quality."""
import copy,json,os,shutil,sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
ROOT=Path(__file__).resolve().parents[3]
_BOOT=TemporaryDirectory(prefix='novel-writing-test-');_WS=Path(_BOOT.name)/'workspace'
shutil.copytree(ROOT/'desktop/preview-template',_WS)
os.environ['NOVEL_WORKSPACE']=str(_WS);os.environ['NOVEL_STUDIO_DATA']=str(Path(_BOOT.name)/'data/workspaces')
sys.path.insert(0,str(ROOT/'web/backend'))
from app.config import Settings
from app.creative.writing import ContextChoice,Approval,SceneStart,FactStart,FactReview,ConfirmReport
from app.studio_tools import SelectionRequest,Decision,normalized,text_hash,utf16_index
from app.errors import ConsoleError

@pytest.fixture
def service(tmp_path,monkeypatch):
    root=tmp_path/'workspace';shutil.copytree(ROOT/'desktop/preview-template',root)
    monkeypatch.setenv('NOVEL_WORKSPACE',str(root));monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'data/workspaces'))
    from app.main import create_app
    app=create_app(Settings(workspace=root));s=app.state.writing_assist;p=next((root/'projects').glob('novel_*')).name
    return s,p,root/'projects'/p

def context(service,body='江予把信放进柜子。周栖敲了两下门。',**extra):
    s,p,root=service;path='chapters/chapter-2/draft.txt';f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(body,encoding='utf-8')
    pov=s.tools.characters.list(p)[0]['canonical']['id'];doc=s.tools.doc(p,path)
    return s.preview(p,ContextChoice(path=path,revision=doc['etag'],pov=pov,**extra))

def approve(s,p,c):return s.approve(p,c['id'],Approval(context_hash=c['context_hash'],confirm=True))

def test_visible_bounded_sources_exclude_pin_and_context_isolation(service):
    s,p,root=service;c=context(service)
    assert c['packet']['as_of_committed_chapter']==1 and c['size']<=c['budget']
    assert any(x['kind']=='chapter' for x in c['sources'])
    id=next(x['id'] for x in c['sources'] if x['kind']=='character')
    b=ContextChoice(**{**c['choice'],'exclude':[id]});d=s.preview(p,b)
    assert id not in {x['id'] for x in d['packet']['sources']}
    assert any(x['id']==id and x['excluded'] for x in d['sources'])
    approve(s,p,d);assert s.use_context(p,d['id'])['context_hash']==d['context_hash']
    with pytest.raises(ConsoleError):s.get(p+'bad','context',d['id'])
    with pytest.raises(ConsoleError):s.preview(p,ContextChoice(**{**c['choice'],'pinned':[id],'exclude':[id]}))
    with pytest.raises(ConsoleError):s.preview(p,ContextChoice(**{**c['choice'],'previous_paths':[c['choice']['path']]}))

def test_context_review_is_hash_bound_and_stale_body_state_rejected(service):
    s,p,root=service;c=context(service)
    with pytest.raises(ConsoleError):s.use_context(p,c['id'])
    approve(s,p,c);s.use_context(p,c['id'])
    (root/c['choice']['path']).write_text('作者新内容。',encoding='utf-8')
    with pytest.raises(ConsoleError):s.use_context(p,c['id'])
    c=context(service);approve(s,p,c)
    from app.projects.service import write_yaml
    ws=s.registry.workspace(p);v=ws.yaml_file('state/current-story-state.yaml');v['revision']+=1;write_yaml(root/'state/current-story-state.yaml',v)
    with pytest.raises(ConsoleError):s.use_context(p,c['id'])

def test_pov_story_time_receipts_and_secrets_never_become_instructions(service):
    s,p,root=service;c=context(service);actor=c['packet']['pov'];ws=s.registry.workspace(p)
    from app.projects.service import write_yaml
    facts=ws.yaml_file('state/knowledge-state.yaml');secret='隐藏港口的真实负责人是严墨'
    facts['facts']['TEST_UNKNOWN']={'canonical_truth':secret,'known_by':[],'suspected_by':[],'false_beliefs':{},'public':False}
    facts['facts']['TEST_KNOWN']={'canonical_truth':'码头今晚停航。','introduced_chapter':1,'known_by':[{'character_id':actor,'acquired_chapter':1,'story_time':'2041-10-03T19:20:00+08:00','source_event':'DEMO_E01'}],'suspected_by':[],'false_beliefs':{},'public':False}
    write_yaml(root/'state/knowledge-state.yaml',facts)
    before=context(service,story_time='2041-10-03T19:00:00+08:00');after=context(service,story_time='2041-10-03T19:30:00+08:00')
    assert '码头今晚停航' not in json.dumps(before['packet'],ensure_ascii=False)
    assert '码头今晚停航' in json.dumps(after['packet'],ensure_ascii=False)
    assert secret not in json.dumps(after['packet'],ensure_ascii=False)
    approve(s,p,after)
    with pytest.raises(ValueError):s.start_scene(p,SceneStart(context_id=after['id'],goal='不要透露'+secret))

def capture(s,p,monkeypatch):
    box={}
    class A:
        selected_ai={'backend':'MOCK_VALIDATION_NOT_REAL_AI'}
    monkeypatch.setattr('app.creative.writing.adapter',lambda *a,**kw:A())
    class T:
        id='fixture';private_text=False
        def public(self):return {'id':self.id,'status':'QUEUED'}
    def prepared(*args,**kwargs):box.update(prompt=args[1],complete=args[5],kwargs=kwargs);return T()
    monkeypatch.setattr(s.manager(p),'prepared',prepared)
    return box

def test_scene_uses_shared_packet_distinct_options_and_confirmed_beats(service,monkeypatch):
    s,p,root=service;c=context(service);approve(s,p,c);box=capture(s,p,monkeypatch)
    s.start_scene(p,SceneStart(context_id=c['id'],goal='两人争执，仍保留合作空间。'))
    assert 'writer_view' in box['prompt'] and box['kwargs']['ai_task']=='scene_design'
    options=[{'title':label,'approach':label,'beats':beats,'emotion':'紧张后缓和','consequence':'需要承担不同代价'} for label,beats in [('先行动',['江予锁柜','周栖留下钥匙']),('先退让',['周栖收走信','江予独自去码头'])]]
    row=box['complete'](json.dumps({'options':options,'questions':[]}));assert row['canon_changed'] is False
    with pytest.raises(ConsoleError):s.start_scene(p,SceneStart(context_id=c['id'],goal='继续',kind='paragraph',confirmed_beats=['去码头']))
    s.start_scene(p,SceneStart(context_id=c['id'],goal='继续',kind='paragraph',confirm_beats=True,confirmed_beats=['江予独自去码头']))
    assert box['kwargs']['ai_task']=='cowrite'
    assert box['complete'](json.dumps({'candidate':'江予推开门。','advice':'段落候选'}))['kind']=='paragraph'

def test_facts_exact_evidence_epistemic_review_no_commit(service,monkeypatch):
    s,p,root=service;c=context(service,'😀江予说：“我昨夜见过他。”周栖把钥匙交给江予。');box=capture(s,p,monkeypatch)
    before={str(f.relative_to(root)):f.read_bytes() for f in (root/'state').rglob('*.yaml')}
    s.start_facts(p,FactStart(path=c['choice']['path'],revision=c['choice']['revision']))
    item={'category':'event','epistemic':'CLAIM','text':'江予声称昨夜见过对方。','quote':'江予说：“我昨夜见过他。”','actor':'','target':'','story_time':'','uncertainty':'无法确认陈述真假。'}
    row=box['complete'](json.dumps({'facts':[item,{**item,'quote':'模型捏造的引文'}],'unknowns':[]}));r=s.facts(p,row['id'])
    assert len(r['facts'])==1 and len(r['unverified'])==1 and r['facts'][0]['locations'][0]['start']==2
    decision={'fact_id':'f0','decision':'accept','text':item['text'],'epistemic':'CLAIM','location':0}
    r=s.review_facts(p,r['id'],FactReview(etag=r['etag'],items=[decision]));assert r['facts'][0]['epistemic']=='CLAIM'
    with pytest.raises(ConsoleError,match='Final witness'):s.handoff(p,r['id'],ConfirmReport(etag=r['etag'],confirm=True))
    assert before=={str(f.relative_to(root)):f.read_bytes() for f in (root/'state').rglob('*.yaml')}
    (root/c['choice']['path']).write_text('作者后来改写。',encoding='utf-8')
    assert not s.facts(p,r['id'])['source_current']
    with pytest.raises(ConsoleError):s.review_facts(p,r['id'],FactReview(etag=r['etag'],items=[decision]))

def test_multi_candidates_use_diff_rejection_acceptance_and_stale_guard(service,monkeypatch):
    s,p,root=service;c=context(service,'周栖站在门口。\n江予说：“我现在非常非常需要你留下。”\n门外船笛响了。');approve(s,p,c)
    box=capture(s,p,monkeypatch)
    monkeypatch.setattr('app.creative.tasks.adapter',lambda *a,**kw:None)
    doc=s.tools.doc(p,c['choice']['path']);text=normalized(doc);quote='我现在非常非常需要你留下。';i=text.index(quote)
    req=SelectionRequest(project_id=p,chapter_id=c['packet']['chapter_id'],path=doc['path'],document_revision=doc['etag'],originalHash=text_hash(text),start=utf16_index(text,i),end=utf16_index(text,i+len(quote)),selected_text=quote,action='polish',style='none',writing_context_id=c['id'],candidate_count=2,directions=['简短','保留迟疑'])
    task=s.tools.start(p,req)
    assert '周栖站在门口' in box['prompt'] and '门外船笛响了' in box['prompt']
    result=box['complete'](json.dumps({'candidates':[{'label':'简短','candidate':'留下，好吗？','advice':'请求'}, {'label':'迟疑','candidate':'我……想让你留下。','advice':'迟疑'}]}))
    assert len(result['variants'])==2
    before=(root/req.path).read_bytes();s.tools.decide(p,task['candidate_id'],Decision(action='reject',originalHash=req.originalHash));assert (root/req.path).read_bytes()==before
    task=s.tools.start(p,req);box['complete'](json.dumps({'candidates':[{'label':'简短','candidate':'留下，好吗？','advice':'请求'}, {'label':'迟疑','candidate':'我……想让你留下。','advice':'迟疑'}]}))
    saved=s.tools.decide(p,task['candidate_id'],Decision(action='accept',originalHash=req.originalHash,candidate='请你留下。'))
    assert '周栖站在门口。' in normalized(saved['file']) and '门外船笛响了。' in normalized(saved['file'])
    with pytest.raises(ConsoleError):s.tools.start(p,req)
