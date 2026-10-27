"""Focused guard tests. Semantic reports below are MOCK fixtures, not real AI evidence."""
import copy,json,asyncio
import pytest
from test_writing_assist import service,context,approve
from app.creative.state_bridge import Source,Stage,Commit,status,start,commit
from app.creative.writing import ContextChoice
from app.tasks.router import core_workflow
from app.errors import ConsoleError

def prepared(service):
 s,p,root=service;c=context(service);path=c['choice']['path'];revision=c['choice']['revision'];w=core_workflow(s.registry.engine)
 reviews={}
 for kind in w.REVIEW_KINDS:
  rel=f'reviews/chapter-2/mock-{kind}.yaml';w.y.write(root/rel,{'body_sha256':revision,'result':'PASS','coverage':'SEMANTIC_REVIEW','reviewer':'MOCK_STRUCTURAL_FIXTURE_NOT_REAL_AI','reviewed_rules':['fixture guard'],'findings_resolved':True});reviews[kind]=rel
 witness=w.final_witness(root,path,2,reviews);w.y.write(root/'reviews/chapter-2/final.yaml',witness)
 from model import MEMORY_KEYS,ITEM,VIEW
 actor=c['packet']['pov'];item=copy.deepcopy(ITEM);item.update(name='隔离测试钥匙',holder=actor,status='已交还',writer_view=[{**VIEW,'text':'测试钥匙已经交还江予。','visibility':'PUBLIC','since_chapter':2,'story_time':'2041-10-03T19:20:00+08:00'}]);evidence='江予把信放进柜子。'
 observations={k:[] for k in MEMORY_KEYS};observations['operations']=[{'file':'items.yaml','pointer':'/items/FIXTURE_KEY','before':None,'after':item,'evidence':evidence}]
 extraction=w.extract(root,witness,observations);v=w.propose(root,witness,extraction,'chapter-2-fixture');w.y.write(root/'state/proposed/chapter-2-fixture.review.yaml',{'result':'PASS','coverage':'SEMANTIC_DIFF_REVIEW','reviewer':'MOCK_STRUCTURAL_FIXTURE_NOT_REAL_AI','proposal_sha256':w.digest(v),'verified_operations':['items.yaml/items/FIXTURE_KEY'],'extraction_complete':True});w.validate_proposal(root,v)
 return s,p,root,c,w,v

def test_confirmed_exact_diff_commit_and_next_context_item(service):
 s,p,root,c,w,v=prepared(service);st=status(s,p,c['choice']['path'],c['choice']['revision']);assert st['proposals'][0]['valid']
 b=Commit(path=c['choice']['path'],revision=c['choice']['revision'],proposal_id=v['proposal_id'],proposal_sha256=w.digest(v),base_sha256=v['base_sha256'])
 with pytest.raises(ConsoleError,match='明确确认'):commit(s,p,b)
 b.confirm=True;out=commit(s,p,b);assert out['action']=='COMMITTED' and out['workflow']['current_chapter']==2
 assert commit(s,p,b)['action']=='ALREADY_COMMITTED'
 path='chapters/chapter-3/draft.txt';(root/path).parent.mkdir(parents=True,exist_ok=True);(root/path).write_text('江予打开门。','utf8');doc=s.tools.doc(p,path)
 following=s.preview(p,ContextChoice(path=path,revision=doc['etag'],pov=c['packet']['pov']))
 assert '测试钥匙已经交还' in json.dumps(following['packet'],ensure_ascii=False)
 assert (root/'reviews/chapter-2/author-state-commit-chapter-2-fixture.json').is_file()

def test_commit_rejects_stale_body_changed_proposal_and_missing_review(service):
 s,p,root,c,w,v=prepared(service);b=Commit(path=c['choice']['path'],revision=c['choice']['revision'],proposal_id=v['proposal_id'],proposal_sha256='0'*64,base_sha256=v['base_sha256'],confirm=True)
 with pytest.raises(ConsoleError,match='确认对象'):commit(s,p,b)
 b.proposal_sha256=w.digest(v);(root/'state/proposed/chapter-2-fixture.review.yaml').unlink()
 with pytest.raises(ConsoleError):commit(s,p,b)
 assert w.load_state(root)['current-story-state.yaml']['project']['current_chapter']==1
 (root/c['choice']['path']).write_text('不同正文。','utf8')
 with pytest.raises(ConsoleError):commit(s,p,b)

def test_unconfirmed_fact_or_counterfactual_has_no_state_authority(service):
 s,p,root=service;c=context(service);w=core_workflow(s.registry.engine);before=w.digest(w.load_state(root))
 with pytest.raises(ConsoleError):start(s,p,Stage(path=c['choice']['path'],revision=c['choice']['revision'],stage='memory'))
 assert w.digest(w.load_state(root))==before
 assert status(s,p,c['choice']['path'],c['choice']['revision'])['proposals']==[]

def test_local_compatible_provider_delegates_distinct_models_without_codex_impersonation(service):
 """MOCK protocol only: actual OpenAI SDK HTTP transport, synthetic responses."""
 from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
 import threading
 from app.ai.models import Provider,Model,Parameters
 from app.creative.director import Director,Create,Control,Plan,Step
 calls=[]
 plan=Plan(summary='本地协议夹具',steps=[Step(title='测试场景',instruction='保留合作边界。')],methods=['context'],method_application=['只用批准的参考包。'])
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(data)
   text=plan.model_dump_json() if data['model']=='fixture-planner' else '江予把门留着。'
   result={'id':'mock-response','object':'chat.completion','created':0,'model':data['model'],'choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':8,'total_tokens':18}}
   body=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 s,p,root=service;c=context(service);approve(s,p,c)
 try:
  provider=Provider(provider_id='protocol-fixture',display_name='MOCK local transport',base_url=f'http://127.0.0.1:{server.server_port}/v1',available_models=[Model(id=id,parameters=Parameters(streaming=False,timeout=15)) for id in ['fixture-planner','fixture-writer']]);s.center.put(provider)
  d=Director(s,None)
  async def scenario():
   row=d.create(p,Create(path=c['choice']['path'],revision=c['choice']['revision'],context_id=c['id'],goal='协议检查，非真实模型质量。',mode='director',commander='protocol-fixture::fixture-planner',executor='protocol-fixture::fixture-writer',skills=['context']))
   for action in ['plan','run']:
    row=await d.control(p,row['id'],Control(etag=row['etag'],action=action,confirm_plan=True));await asyncio.wait_for(s.manager(p).get(row['active_task']).runner,30);row=d.get(p,row['id']);assert not row.get('last_error'),row.get('last_error')
   assert [v['model'] for v in calls]==['fixture-planner','fixture-writer']
   assert 'WriterView' in json.dumps(calls[1]) and row['draft']=='江予把门留着。'
   assert all(v['backend']=='llm' for v in row['usage'])
  asyncio.run(scenario())
 finally:server.shutdown();server.server_close();thread.join(2)

def test_explicit_proposal_id_does_not_depend_on_legacy_filename_discovery(service):
 s,p,root,c,w,v=prepared(service)
 from app.models.requests import TaskRequest,TaskOptions
 from app.tasks.router import TaskRouter
 v['proposal_id']='author-chosen-name';w.y.write(root/'state/proposed/author-chosen-name.yaml',v)
 router=TaskRouter(s.registry.workspace(p),s.registry.engine)
 prompt,read_only,_=router.build(TaskRequest(type='state_validate',chapter=2,options=TaskOptions(proposal_path='state/proposed/author-chosen-name.yaml')))
 assert 'author-chosen-name.yaml' in prompt
 with pytest.raises(ConsoleError,match='不属于选定章节'):router.build(TaskRequest(type='state_validate',chapter=3,options=TaskOptions(proposal_path='state/proposed/author-chosen-name.yaml')))

def test_state_array_append_rejects_negative_indices_without_source_mutation(service):
 s,p,root=service;w=core_workflow(s.registry.engine);initial=w.load_state(root);size=len(initial['timeline.yaml']['events']);old=copy.deepcopy(initial)
 row=copy.deepcopy(initial['timeline.yaml']['events'][0]);row['id']='FIXTURE_APPEND'
 updated=w.apply_operations(initial,[{'file':'timeline.yaml','pointer':'/events/'+str(size),'before':None,'after':row}])
 assert len(updated['timeline.yaml']['events'])==size+1 and initial==old
 with pytest.raises(ValueError):w.apply_operations(initial,[{'file':'timeline.yaml','pointer':'/events/-1','before':None,'after':row}])
 assert initial==old

def test_data_only_final_rejects_fabricated_semantic_evidence(service,monkeypatch):
 s,p,root=service;c=context(service)
 from app.creative.state_tasks import prepare
 class A:selected_ai={'backend':'MOCK_STRUCTURAL_FIXTURE_NOT_REAL_AI','model':'fixture'}
 monkeypatch.setattr('app.creative.state_tasks.adapter',lambda *a,**kw:A())
 captured={}
 class T:
  private_text=False
 def prepared(*args,**kw):captured.update(prompt=args[1],complete=args[5],kwargs=kw);return T()
 monkeypatch.setattr(s.manager(p),'prepared',prepared)
 prepare(s,p,c['choice']['path'],c['choice']['revision'],'final')
 assert 'novel-contract-checker' in captured['prompt'] and 'No tools' in captured['prompt']
 kinds=['contract','continuity','character','scene_plot','style']
 output={'reviews':[{'kind':k,'result':'PASS','reviewed_rules':['MOCK guard fixture'],'findings':[]} for k in kinds]}
 output['reviews'][0]['findings']=[{'priority':'STYLE ONLY','message':'mock','evidence':'不存在的原文'}]
 with pytest.raises(ConsoleError,match='引用不存在'):captured['complete'](json.dumps(output))
 assert not (root/'reviews/chapter-2/final.yaml').exists()

def test_memory_time_is_explicit_and_reviewed_observations_are_read_in_scope(service,monkeypatch):
 s,p,root,c,w,v=prepared(service)
 from app.creative.state_tasks import prepare
 from app.library.storage import write
 with pytest.raises(ConsoleError,match='作者明确填写'):prepare(s,p,c['choice']['path'],c['choice']['revision'],'memory')
 with pytest.raises(ConsoleError,match='不能早于'):prepare(s,p,c['choice']['path'],c['choice']['revision'],'memory',story_time='2041-10-02T01:00:00+08:00')
 class A:selected_ai={'backend':'MOCK_STRUCTURAL_FIXTURE_NOT_REAL_AI','model':'fixture'}
 monkeypatch.setattr('app.creative.state_tasks.adapter',lambda *a,**kw:A())
 captured={}
 class T:private_text=False
 def prepared_task(*args,**kw):captured['prompt']=args[1];return T()
 monkeypatch.setattr(s.manager(p),'prepared',prepared_task)
 rel='reviews/chapter-2/observations.json';write(root/rel,{'status':'AUTHOR_REVIEWED_NOT_STATE','facts':[]})
 prepare(s,p,c['choice']['path'],c['choice']['revision'],'memory',writing_report=rel,story_time='2041-10-03T19:30:00+08:00')
 assert 'EXPLICIT_AUTHOR_END_STATE_ANCHOR' in captured['prompt'] and 'AUTHOR_REVIEWED_NOT_STATE' in captured['prompt']

def test_committed_semantic_reports_cannot_be_overwritten(service):
 s,p,root,c,w,v=prepared(service)
 b=Commit(path=c['choice']['path'],revision=c['choice']['revision'],proposal_id=v['proposal_id'],proposal_sha256=w.digest(v),base_sha256=v['base_sha256'],confirm=True);commit(s,p,b)
 before={str(f):f.read_bytes() for f in (root/'reviews/chapter-2').rglob('*') if f.is_file()}
 with pytest.raises(ConsoleError,match='已提交'):start(s,p,Stage(path=c['choice']['path'],revision=c['choice']['revision'],stage='final'))
 from app.creative.state_tasks import prepare
 with pytest.raises(ConsoleError,match='已提交'):prepare(s,p,c['choice']['path'],c['choice']['revision'],'final')
 from app.tasks.router import TaskRouter
 availability=TaskRouter(s.registry.workspace(p),s.registry.engine).availability(2)
 assert not availability['final_check']['enabled'] and not availability['memory_extract']['enabled']
 assert before=={str(f):f.read_bytes() for f in (root/'reviews/chapter-2').rglob('*') if f.is_file()}
