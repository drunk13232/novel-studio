"""2.11.2 focused regressions. Local HTTP fixtures are MOCK, not remote AI."""
import copy,json,threading,time,zipfile,uuid
from types import SimpleNamespace
from pathlib import Path
import pytest
from test_writing_assist import service,context
from test_workflow_reliability import prepared
from test_world_logic import example
from app.errors import ConsoleError
from app.creative.state_bridge import status,commit,Commit
from app.library.storage import write,read,digest,now
from app.world_logic.engine import run
from app.world_logic.service import WorldLogic,ManualReview,fingerprint
from app.world_logic.models import Freeze


def test_large_state_history_filters_before_stable_pagination(service):
 s,p,root,c,w,v=prepared(service);folder=root/'state/proposed';path=c['choice']['path'];revision=c['choice']['revision']
 for i in range(190):
  write(folder/f'old-{i:03}.review.yaml',{'result':'PASS'})
  other=copy.deepcopy(v);other['proposal_id']=f'old-{i:03}';other['final']['chapter']=1;other['final']['body_path']='chapters/chapter-1/final.md';w.y.write(folder/(other['proposal_id']+'.yaml'),other)
 for i in range(45):
  item=copy.deepcopy(v);item['proposal_id']=f'current-{i:03}';w.y.write(folder/(item['proposal_id']+'.yaml'),item)
 foreign=copy.deepcopy(v);foreign['proposal_id']='foreign';foreign['project_id']='novel_'+'0'*32;w.y.write(folder/'foreign.yaml',foreign)
 started=time.monotonic();first=status(s,p,path,revision,page_size=10);cold=time.monotonic()-started
 assert first['pagination']['total']==46
 ids=[r['id'] for r in first['proposals']];token=first['pagination']['snapshot']
 started=time.monotonic()
 for page in range(1,5):ids.extend(r['id'] for r in status(s,p,path,revision,page=page,page_size=10,snapshot=token)['proposals'])
 assert ids==sorted(ids) and len(ids)==len(set(ids))==46
 assert status(s,p,path,revision,page_size=10)['proposals']==first['proposals']
 b=Commit(path=path,revision=revision,proposal_id=v['proposal_id'],proposal_sha256=w.digest(v),base_sha256=v['base_sha256'],confirm=True)
 assert commit(s,p,b)['action']=='COMMITTED'
 assert status(s,p,path,revision,filter='committed')['pagination']['total']==1
 pending=status(s,p,path,revision,filter='pending');assert pending['pagination']['total']==45
 with pytest.raises(ConsoleError,match='列表已变化'):status(s,p,path,revision,snapshot=token)
 print('STATE_META cold_seconds=',round(cold,3),'subsequent_seconds=',round(time.monotonic()-started,3),'files=',len(list(folder.glob('*.yaml'))))


def experiment_report(service,fail=False):
 s,p,root=service;lab=WorldLogic(s.registry,None,s.manager,s.center)
 d=example('event-order');d['experiment_id']='exp_'+uuid.uuid4().hex
 d['acceptance_rules'].append({'id':'manual_rule','name':'作者核对叙事顺序','target':'dependencies','type':'QUALITATIVE','automatic':False,'basis':'作者逐项核对'})
 if fail:d['dependencies'].append({'id':'cycle','before':'meeting','after':'departure','meaning':'确定冲突','source_ids':[]})
 row=lab.save(p,d);frozen=lab.freeze(p,row['id'],Freeze(etag=row['etag'],reason='隔离人工验收测试',confirm=True))['frozen']
 rid='run_'+uuid.uuid4().hex
 report={**run(frozen['definition']),'id':rid,'experiment_id':row['id'],'definition':frozen['definition'],'definition_version':frozen['version'],'definition_fingerprint':frozen['fingerprint'],'acceptance_fingerprint':frozen['acceptance_fingerprint'],'created_at':now(),'finished_at':now()}
 write(lab.root(p)/'reports'/(rid+'.json'),report)
 return lab,p,rid


def decide(lab,p,rid,verdict='PASS'):
 r=lab.report(p,rid);rule=next(x for x in r['acceptance_results'] if x.get('manual'))
 return lab.manual_review(p,rid,ManualReview(rule_id=rule['id'],status=verdict,note='作者明确核对后的判断',definition_fingerprint=r['definition_fingerprint'],acceptance_fingerprint=r['acceptance_fingerprint'],rule_fingerprint=rule['rule_fingerprint'],review_revision=r['review_revision'],confirm=True))


def test_math_pass_manual_pending_fail_pass_and_changed_rules(service):
 lab,p,rid=experiment_report(service);path=lab.root(p)/'reports'/(rid+'.json');original=path.read_bytes()
 r=lab.report(p,rid);assert r['status']=='INCONCLUSIVE' and r['manual_pending']==1 and r['mathematical_status']=='PASS'
 assert decide(lab,p,rid,'FAIL')['status']=='FAIL'
 passed=decide(lab,p,rid);assert passed['status']=='PASS' and len(passed['manual_reviews'])==2
 assert lab.reports(p)[0]['status']=='PASS'
 assert path.read_bytes()==original  # Solver report remains immutable.
 current=lab.get(p,r['experiment_id']);d=copy.deepcopy(current['definition']);d['acceptance_rules'][-1]['basis']='作者改变了验收条件'
 lab.save(p,d,current['etag'])
 assert lab.report(p,rid)['status']=='INCONCLUSIVE'
 with pytest.raises(ConsoleError,match='失效'):decide(lab,p,rid)
 frozen=lab.freeze(p,r['experiment_id'],Freeze(etag=lab.get(p,r['experiment_id'])['etag'],reason='规则更新',confirm=True))['frozen']
 assert frozen['version']==2 and lab.report(p,rid)['manual_pending']==1


def test_math_fail_cannot_be_overridden_by_manual_pass(service):
 lab,p,rid=experiment_report(service,True)
 r=decide(lab,p,rid);assert r['status']=='FAIL' and r['mathematical_status']=='FAIL'


def test_manual_graph_condition_is_not_automatically_approved():
 d=example('event-order')
 for r in d['acceptance_rules']:r['automatic']=False
 assert run(d)['status']=='INCONCLUSIVE'


def chat_row(id='saved-chat'):
 return {'id':id,'at':now(),'instruction':'继续讨论测试写作任务','output':'已保存讨论，不包含正式作品。','status':'SUCCEEDED','pending_confirmation':False,'provider':'Codex','model':'fixture-model','steps':[]}


def test_project_backup_restores_chats_personas_and_dormant_records(service,tmp_path):
 from app.assistant.conversations import Conversations
 from app.ai.models import Provider,Model
 s,p,root=service;center=s.center;data=s.workbench.data
 center.put(Provider(provider_id='local',display_name='MOCK',base_url='http://127.0.0.1:1234/v1',available_models=[Model(id='model')]))
 prefs=center.settings();prefs.projects[p]={'polish':'local::model'};center.save(prefs)
 write(center.root/'assistant-personas.json',{'rem':{'model':'local::model','mode':'suggest','selection':True}})
 write(center.root/'assistant-settings.json',{'mode':'navigate','selection':False})
 chats=Conversations(center.root)
 write(chats.path(p,'rem','local::model'),[chat_row(),{**chat_row('waiting'),'status':'WAITING_CONFIRMATION','pending_confirmation':True}]);chats.register(p,'rem','local::model')
 other='novel_'+'0'*32;write(chats.path(other,'rem','local::model'),[{**chat_row(),'output':'OTHER_PROJECT_SENTINEL'}]);chats.register(other,'rem','local::model')
 # An older list-only conversation is discovered by its known scoped filename.
 write(chats.path(p,'yoshino','codex-software'),[chat_row('legacy')])
 from app.roleplay.service import Roleplay
 from app.roleplay.models import Create as RoleCreate,Persona,Actor
 roles=Roleplay(s.registry,s.tools.characters,s.workbench,s.manager,s.center,None)
 actor=s.tools.characters.list(p)[0]['canonical']['id']
 role=roles.create(p,RoleCreate(title='真实本地测试会话',persona=Persona(name='测试作者'),actors=[Actor(source_id=actor)]));session=role['id']
 role['pending_task']='old-task';roles.save(p,role)
 from app.creative.director import Director,Create as DirectorCreate
 from test_writing_assist import approve
 ctx=context(service);approve(s,p,ctx);directors=Director(s,None)
 row=directors.create(p,DirectorCreate(path=ctx['choice']['path'],revision=ctx['choice']['revision'],context_id=ctx['id'],goal='隔离历史测试',mode='quick',executor='local::model'))
 director=row['id'];row.update(active_task='old-task',status='GENERATING',auto_continue=True);directors.put(p,row)
 before=(center.root/'assistant-personas.json').read_bytes();global_settings=(center.root/'assistant-settings.json').read_bytes()
 backup=data.backup(p,True,'RELIABILITY_TEST');blob=Path(backup['path']).read_bytes()
 with zipfile.ZipFile(backup['path']) as z:
  assert 'application/project-assistant.json' in z.namelist()
  app=json.loads(z.read('application/project-assistant.json'));assert len(app['conversations'])==2
  assert b'OTHER_PROJECT_SENTINEL' not in z.read('application/project-assistant.json')
  assert not any('auth.json' in n or 'companion/' in n for n in z.namelist())
 staged=data.stage(blob);result=data.restore(staged['token'],expected_hash=staged['sha256']);new=result['project_id'];newroot=s.registry.workspace(new).root
 assert new!=p and result['application_state']['project_assistant']
 restored=Conversations(center.root);rows=restored.page(new,'rem','local::model')['rows'];assert len(rows)==2 and rows[-1]['status']=='INTERRUPTED' and not rows[-1]['pending_confirmation']
 assert restored.context(new,'rem','local::model') and restored.page(new,'yoshino','codex-software')['rows'][0]['id']=='legacy'
 assert not restored.page(other,'yoshino','codex-software')['rows']
 from app.assistant.service import AssistantCenter
 assistant=AssistantCenter.__new__(AssistantCenter);assistant.root=center.root;assistant.app=SimpleNamespace(state=SimpleNamespace(registry=s.registry))
 assert assistant.settings('rem',new).selection and not assistant.settings('yoshino',new).selection
 assert center.settings().projects[new]['polish']=='local::model'
 assert (center.root/'assistant-personas.json').read_bytes()==before and (center.root/'assistant-settings.json').read_bytes()==global_settings
 role=read(newroot/f'metadata/roleplay/{session}.json');assert role['project_id']==new and role['pending_task'] is None
 d=read(s.tools.local(new,'director/'+director+'.json'));assert d['project_id']==new and d['status']=='INTERRUPTED' and d['active_task'] is None and not d['auto_continue']
 assert roles.get(new,session)['title']=='真实本地测试会话'
 assert directors.get(new,director)['goal']=='隔离历史测试' and directors.history(new)[0]['id']==director
 assert s.get(new,'context',ctx['id'])['project_id']==new
 assert not s.manager(new).tasks
 lite=data.backup(p,True,'NO_CHAT',private_history=False)
 with zipfile.ZipFile(lite['path']) as z:
  assert not json.loads(z.read('application/project-assistant.json'))['conversations']
  assert 'project/metadata/roleplay/'+session+'.json' not in z.namelist()
 # A v1 backup without the additive assistant entry remains restorable.
 old=tmp_path/'old.zip'
 with zipfile.ZipFile(backup['path']) as source,zipfile.ZipFile(old,'w',zipfile.ZIP_DEFLATED) as target:
  manifest=json.loads(source.read('manifest.json'));manifest['files']=[x for x in manifest['files'] if x['path']!='application/project-assistant.json']
  for n in source.namelist():
   if n not in {'manifest.json','application/project-assistant.json'}:target.writestr(n,source.read(n))
  target.writestr('manifest.json',json.dumps(manifest))
 staged=data.stage(old.read_bytes());assert data.restore(staged['token'],expected_hash=staged['sha256'])['project_id']!=new


@pytest.fixture
def protocol_server():
 from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
 calls=[]
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append((self.path,body));model=body['model']
   code={'auth-bad':401,'model-bad':404,'unsupported':400}.get(model,200)
   if model=='timeout':time.sleep(5.5)
   if code!=200:result={'error':{'message':'unsupported parameter max_tokens' if code==400 else 'fixture error','type':'invalid_request_error'}}
   elif self.path.endswith('/responses'):result={'id':'resp_fixture','object':'response','status':'completed','model':model,'output':[{'id':'msg_fixture','type':'message','status':'completed','role':'assistant','content':[{'type':'output_text','text':'OK','annotations':[]}]}],'usage':{'input_tokens':3,'output_tokens':1,'total_tokens':4}}
   else:result={'id':'chat_fixture','object':'chat.completion','created':0,'model':model,'choices':[{'index':0,'message':{'role':'assistant','content':'OK'},'finish_reason':'stop'}],'usage':{'prompt_tokens':3,'completion_tokens':1,'total_tokens':4}}
   raw=json.dumps(result).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
   try:self.wfile.write(raw)
   except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:yield server,calls
 finally:server.shutdown();server.server_close();thread.join(2)


def test_compatible_provider_default_omitted_mapping_responses_and_errors(service,protocol_server):
 from app.ai.models import Provider,Model,Test as ConnectionTest
 s,p,root=service;server,calls=protocol_server
 models=[Model(id='default',chat_token_parameter='max_tokens'),Model(id='completion',chat_token_parameter='max_completion_tokens'),Model(id='omitted'),Model(id='responses',protocol='responses'),*[Model(id=id) for id in ['auth-bad','model-bad','unsupported','timeout']]]
 s.center.put(Provider(provider_id='fixture',display_name='MOCK protocol only',timeout=5,base_url=f'http://127.0.0.1:{server.server_port}/v1/v1',available_models=models))
 for id in ['default','completion','omitted','responses']:
  r=s.center.test('fixture',ConnectionTest(model=id,confirm_cost=True));assert r['category']=='TEXT_GENERATION_OK',r
 assert calls[0][1]['max_tokens']==16 and calls[1][1]['max_completion_tokens']==16
 assert not {'max_tokens','max_completion_tokens'}&calls[2][1].keys() and calls[3][0]=='/v1/responses'
 for id,category in [('auth-bad','AUTH_FAILED'),('model-bad','MODEL_OR_ENDPOINT_NOT_FOUND'),('unsupported','UNSUPPORTED_PARAMETER'),('timeout','TIMEOUT'),('not-saved','LOCAL_CONFIGURATION')]:
  r=s.center.test('fixture',ConnectionTest(model=id,confirm_cost=True));assert r['category']==category,r
 assert len([x for _,x in calls if x['model']=='timeout'])==1
 assert all('temperature' not in x and 'top_p' not in x for _,x in calls)


@pytest.mark.parametrize('expression,expected',[('2**-1',.5),('2**+2',4),('-2**2',-4),('(-2)**2',4),('2**(-3)',.125)])
def test_signed_integer_powers_and_precedence(expression,expected):
 from app.world_logic.expressions import evaluate
 assert float(evaluate(expression,{}).magnitude)==expected
 assert float(evaluate(expression,{},'symbolic'))==expected


@pytest.mark.parametrize('expression',['2**-9','2**True','2**(1-2)','2**2**2','2**x','__import__(1)','0**-1'])
def test_unsafe_power_expressions_are_blocked(expression):
 from app.world_logic.expressions import evaluate
 with pytest.raises(Exception):evaluate(expression,{})
