"""Public synthetic fixture only. Local TaskManager events are controlled; no AI model runs."""
import os,sys,shutil,json,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
import argparse
parser=argparse.ArgumentParser(description='Isolated public-demo Director UI fixture; never use personal data')
parser.add_argument('--root',required=True,type=Path)
parser.add_argument('--port',type=int,default=8917)
parser.add_argument('--local-writer',action='store_true',help='Fixed local test response only; never a real AI')
parser.add_argument('--mixed-source',action='store_true',help='Synthetic read-only mixed-newline chapter for selection checks')
args=parser.parse_args();A=args.root.resolve()
if not A.is_relative_to((ROOT/'desktop/build').resolve()) or A==(ROOT/'desktop/build').resolve():raise SystemExit('Fixture must use a dedicated directory below desktop/build')
if not 1024<=args.port<=65535:raise SystemExit('Use an unprivileged loopback port')
W=A/'workspace'
for child in [W,A/'app-data']:
 if child.is_symlink() or not child.resolve().is_relative_to(A):raise SystemExit('Fixture children must stay inside the owned directory')
if W.exists() and (not(A/'config.json').is_file() or json.loads((A/'config.json').read_text('utf8')).get('fixture')!='public-demo-only'):raise SystemExit('Existing workspace is not this owned public-demo fixture')
A.mkdir(parents=True,exist_ok=True)
if not W.exists():shutil.copytree(ROOT/'desktop/preview-template',W)
if args.mixed_source:
 source=next((W/'projects').glob('novel_*'))/'chapters/chapter-2/draft.md'
 assert source.resolve().is_relative_to(W.resolve());source.write_bytes('第一段。\r\n\r\n🌧️第二段的回答。\n\n尾段保留。\n'.encode('utf8'))
os.environ.update(NOVEL_WORKSPACE=str(W),NOVEL_STUDIO_HOME=str(A/'app-data'),NOVEL_STUDIO_DATA=str(A/'app-data/workspaces'),NOVEL_PORT=str(args.port),NOVEL_DEMO='1')
sys.path.insert(0,str(ROOT/'web/backend'));sys.path.insert(0,str(ROOT/'scripts'))
from app.main import create_app
from app.config import Settings
from app.assistant.service import Session
from app.assistant.models import Start,Context,AssistantSettings
from app.studio_tools import normalized
app=create_app(Settings(workspace=W,port=args.port,static_dir=ROOT/'web/frontend/dist'));p=next((W/'projects').glob('novel_*')).name
path='chapters/chapter-2/draft.md';doc=app.state.studio_tools.doc(p,path)
s=Session(app.state.assistant,Start(instruction='LOCAL_SERVICE_TEST: 保存可查看的正文候选，不调用模型',context=Context(project=p,page='write',path=path)),AssistantSettings(mode='draft',manuscript=True,save_conversation=True));s.manager=app.state.assistant.manager(p);s.model=SimpleNamespace(id='LOCAL_SERVICE_TEST',capabilities={'tools':True});s.provider=SimpleNamespace(provider_id='local-action',display_name='LOCAL_SERVICE_TEST');s.ai_metadata={'backend':'local-service','remote_model_called':False}
r=s.call('stage_chapter_draft',{'number':2,'revision':doc['etag'],'content':'第2章 海边的试写\n\n这是一份独立演示候选，用来验证保存、重开和继续写作。\n\n所有测试文字均为临时示例，不是用户的作品。','note':'LOCAL_SERVICE_TEST'});assert r['ok'],r
from app.creative.writing import ContextChoice,Approval
from app.creative.director import Create,Patch
from app.creative.director_delivery import checkpoint
ctx=app.state.writing_assist.preview(p,ContextChoice(path=path,revision=doc['etag']))
app.state.writing_assist.approve(p,ctx['id'],Approval(context_hash=ctx['context_hash'],confirm=True))
if args.local_writer:
 import app.creative.director as director_module
 class LocalWriter:
  role='WRITER';selected_ai={'backend':'MOCK','provider_name':'CONTROLLED_LOCAL_WRITER','model':'fixed-local-response'}
  def close(self):pass
  interrupt=close
  def start_task(self,prompt,emit,**kw):
   text='【局部修订示例】';emit('llm_delta',text,{'delta':text});return {'status':'completed','output':text}
 def local_adapter(center,project,group,prompt,*other,**kw):
  assert project==p and group=='cowrite';return LocalWriter()
 director_module.adapter=local_adapter
record=app.state.creative_director.create(p,Create(path=path,revision=doc['etag'],context_id=ctx['id'],goal='LOCAL_SERVICE_TEST: open a saved task only; no model is called',executor='codex',commander='codex',mode='quick',goal_han=3000))
record=app.state.creative_director.patch(p,record['id'],Patch(etag=record['etag'],draft='她把信纸折好，放在窗边。门外的人没有马上回答，她先把杯子移开，给对方留下坐下的位置。她把信纸折好，放在窗边。门外的人没有马上回答，她先把杯子移开，给对方留下坐下的位置。她把信纸折好，放在窗边。门外的人没有马上回答，她先把杯子移开，给对方留下坐下的位置。\n\n她把信纸折好，放在窗边。门外的人没有马上回答，她先把杯子移开，给对方留下坐下的位置。她把信纸折好，放在窗边。门外的人没有马上回答，她先把杯子移开，给对方留下坐下的位置。她把信纸折好，放在窗边。门外的人没有马上回答，她先把杯子移开，给对方留下坐下的位置。'))
record.update(status='FAILED',failure={'code':'TIMEOUT','automatic_retry':False},last_error='LOCAL_SERVICE_TEST: timeout after retained output')
record['resume_checkpoint']=checkpoint(record,0,'TIMEOUT');app.state.creative_director.put(p,record)
read=s.call('read_creative_writing',{'id':record['id'],'limit':1});assert read['ok'],read
s.output='LOCAL_SERVICE_TEST：候选已保存，未采用，未调用 AI。';s.chat_status='SUCCEEDED';s.ended=True;app.state.assistant.remember(s)
# The fixture carries a second task and explicit synthetic saved reports.
from app.library.storage import uid,write,now
from app.creative.director import Fork,Candidate
secondary=app.state.creative_director.fork(p,record['id'],Fork(etag=app.state.creative_director.get(p,record['id'])['etag'],goal='LOCAL_SECONDARY_'+uid('fixture')[-10:],keep_draft=True))
fixture_reports={}
for kind in ['ALPHA','BETA']:
 rid=uid('review');fixture_reports[kind]=rid
 write(app.state.creative_director.reviews.path(p,rid),{'id':rid,'project_id':p,'source_path':path,'source_revision':doc['etag'],'mode':'character','created_at':now(),'criteria':['SYNTHETIC LOCAL FIXTURE — not AI review'],'ai_metadata':{'backend':'CONTROLLED_LOCAL_FIXTURE'},'report':{'summary':'LOCAL_REPORT_'+kind,'issues':[]},'sources':[]})
(A/'config.json').write_text(json.dumps({'url':'http://127.0.0.1:'+str(args.port),'project':p,'path':path,'candidate_id':r['result']['id'],'record_id':record['id'],'secondary_id':secondary['id'],'secondary_goal':secondary['goal'],'fixture_reports':fixture_reports,'fixture':'public-demo-only','local_writer':args.local_writer,'mixed_source':args.mixed_source}),encoding='utf-8')
import threading
from app.models.requests import TaskRequest,TaskOptions
from app.tasks.manager import now as task_now
fixture_gate=threading.Event()
fixture_review=None
@app.post('/api/test-fixture-arm-review')
def arm_review(kind:str='ALPHA'):
 global fixture_review
 assert kind=='NONE' or kind in fixture_reports;fixture_review=None if kind=='NONE' else fixture_reports[kind];return {'review_id':fixture_review}
@app.post('/api/test-fixture-bind-review')
def bind_review(kind:str='ALPHA',basis:str='legacy',part:int=0):
 assert part in {0,1,2}
 assert kind in fixture_reports and basis in {'legacy','current','missing_hash','wrong_scope','old_source'}
 service=app.state.creative_director;row=service.get(p,record['id']);assert not row.get('active_task');rid=fixture_reports[kind]
 if basis!='legacy':
  from app.studio_tools import text_hash
  from app.creative.reviews import locate
  staged=service.stage(p,row['id'],Candidate(etag=row['etag']));row=staged['record'];rid=uid('review');text=row['draft'];quote=text.split('。')[0]+'。' if '。' in text else text[:12]
  if part==1:quote=text.splitlines()[2]
  if part==2:quote=text[:text.index('。',text.index('。')+1)+1]
  report={'id':rid,'project_id':p,'source_path':path,'source_revision':doc['etag'],'mode':'character','created_at':now(),'criteria':['SYNTHETIC LOCAL FIXTURE — not AI review'],'ai_metadata':{'backend':'CONTROLLED_LOCAL_FIXTURE'},'source_kind':'CREATIVE_CANDIDATE','source_candidate':staged['candidate']['id'],'candidate_sha256':text_hash(text),'body_sha256':text_hash(text),'report':{'summary':'LOCAL_REPORT_'+kind,'issues':[{'message':'SYNTHETIC_EVIDENCE_FINDING','priority':'SUGGESTION','evidence':[quote,'THIS_QUOTE_IS_NOT_IN_THE_CANDIDATE']}]},'anchors':[{'issue':0,'evidence':[locate(quote,text),locate('THIS_QUOTE_IS_NOT_IN_THE_CANDIDATE',text)]}],'sources':[]}
  if basis=='missing_hash':report.pop('candidate_sha256')
  if basis=='wrong_scope':report['project_id']='novel_'+'0'*32
  if basis=='old_source':report['source_revision']='0'*64
  write(service.reviews.path(p,rid),report)
 row.update(review_id=rid,review_stale=False);service.put(p,row);return {'review_id':rid}
@app.post('/api/test-fixture-stage')
async def stage_fixture(later:bool=False):
 service=app.state.creative_director;row=service.get(p,record['id']);assert row.get('active_task');row['draft']='SERVER_SNAPSHOT_LATER' if later else 'SERVER_SNAPSHOT_EARLIER';row['phase']=row['draft'];service.put(p,row);service.manager(p).emit(service.manager(p).get(row['active_task']),'director_stage',row['phase']);return {'stage':row['phase']}
@app.post('/api/test-fixture-start')
async def start_fixture():
 fixture_gate.clear();service=app.state.creative_director;current=service.get(p,record['id']);assert not current.get('active_task');manager=service.manager(p)
 def execute(emit,cancelled):
  while not fixture_gate.wait(.02):
   if cancelled():return {'status':'interrupted','output':'','ai_metadata':{'backend':'CONTROLLED_LOCAL_FIXTURE'}}
  return {'status':'completed','output':'','ai_metadata':{'backend':'CONTROLLED_LOCAL_FIXTURE'}}
 def finished(task):
  with service.lock:
   row=service.get(p,record['id'])
   if not task.cancel_requested:row['draft']+='\n\n本地可控任务结束后的保留文字。'
   if fixture_review and not task.cancel_requested:row.update(review_id=fixture_review,review_stale=False)
   row.update(active_task=None,active_step=None,status='PAUSED',phase='CONTROLLED_LOCAL_FIXTURE: stopped or completed; no AI')
   service.put(p,row)
 task=manager.prepared(TaskRequest(type='custom_prompt',prompt='CONTROLLED_LOCAL_FIXTURE',options=TaskOptions(timeout_seconds=30)),'CONTROLLED_LOCAL_FIXTURE',True,'chapter-002',execute=execute,finished=finished,application_actions=True,orchestrator=True,provider='CONTROLLED_LOCAL_FIXTURE')
 current.update(active_task=task.id,active_step=0,status='GENERATING',phase='CONTROLLED_LOCAL_FIXTURE: waiting')
 service.put(p,current);return {'task':task.public(),'record_id':record['id']}
@app.post('/api/test-fixture-finish')
def finish_fixture():fixture_gate.set();return {'released':True}
import uvicorn
(A/'server.pid').write_text(str(os.getpid()),'ascii')
server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_level='warning'))
@app.post('/api/test-fixture-exit')
def fixture_exit():fixture_gate.set();server.should_exit=True;return {'closing':True}
server.run()
