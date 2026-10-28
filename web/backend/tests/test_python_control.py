"""Real CPython/WASI and domain services; no remote AI or simulated UI claims."""
import json,os,shutil,sys,time,subprocess,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'web/backend'))

def guest(code):
    result=subprocess.run([sys.executable,'-m','app.automation.worker'],input=json.dumps({'code':code})+'\n',capture_output=True,text=True,encoding='utf-8',cwd=ROOT/'web/backend',timeout=40)
    return result

def test_real_python_wasi_has_no_host_mount_network_or_process(tmp_path):
    secret=tmp_path/'outside-wasi.txt';secret.write_text('PRIVATE FIXTURE',encoding='utf-8')
    code='''import os,sys,json
assert sys.platform == 'wasi'
assert os.environ.get('NOVEL_STUDIO_DATA') is None
blocked=[]
for name,operation in [
 ('host',lambda:open(PATH).read()),
 ('runtime-write',lambda:open('/runtime/host-write.txt','w')),
 ('network',lambda:__import__('socket').create_connection(('127.0.0.1',8765),timeout=1)),
 ('shell',lambda:os.system('echo NOT_ALLOWED'))]:
 try:
  operation()
  raise AssertionError(name+' escaped isolation')
 except (OSError,ImportError,AttributeError,NotImplementedError):blocked.append(name)
assert sum(i*i for i in range(5))==30
print(json.dumps({'blocked':blocked,'real_python':sys.version}))
'''.replace('PATH',repr(str(secret)))
    result=guest(code)
    assert result.returncode==0,result.stderr
    assert 'PRIVATE FIXTURE' not in result.stdout
    assert json.loads(result.stdout)['blocked']==['host','runtime-write','network','shell']

@pytest.fixture
def client(tmp_path,monkeypatch):
    engine=tmp_path/'engine';shutil.copytree(ROOT/'desktop/preview-template',engine)
    monkeypatch.setenv('NOVEL_WORKSPACE',str(engine));monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'data/workspaces'));monkeypatch.setenv('NOVEL_STATIC_DIR',str(tmp_path/'no-static-assets'))
    from app.config import Settings
    from app.main import create_app
    from fastapi.testclient import TestClient
    app=create_app(Settings(workspace=engine));app.state.testing=True
    project=next((engine/'projects').glob('novel_*')).name
    with TestClient(app) as c:
        c.headers['X-Novel-Request']=c.get('/api/session').json()['request_token']
        yield c,app,project,engine

def launch(c,p,code,persona='yoshino',previous=None):
    body={'persona':persona,'instruction':'隔离测试 Python','context':{'project':p,'page':'write','path':'chapters/chapter-2/draft.txt'},'code':code,'model':'codex-software','timeout':40,'previous_session':previous}
    response=c.post('/api/control/run',json=body)
    assert response.status_code==202,response.text
    return response.json()

def finish(c,s):
    until=time.monotonic()+45
    while time.monotonic()<until:
        row=c.get('/api/assistant/sessions/'+s['id']).json()
        if row['task']['status'] in ('SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'):
            return row
        time.sleep(.1)
    raise AssertionError('Control did not finish')

def configure(app,p,**options):
    from app.assistant.models import AssistantSettings
    app.state.assistant.configure(AssistantSettings(**options),'yoshino',p)

def test_real_sdk_calls_existing_notes_and_preserves_canon(client):
    c,app,p,engine=client;configure(app,p,mode='draft')
    root=engine/'projects'/p
    hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('chapters','characters','state','bible','settings') for f in (root/folder).rglob('*') if f.is_file()}
    row=finish(c,launch(c,p,'from novel_studio_api import Studio\ns=Studio.connect()\nprint(s.projects.current())\nprint(s.chapters.list())\nprint(s.notes.create("Python SDK real isolated note"))\n'))
    assert row['task']['status']=='SUCCEEDED',row
    notes=app.state.workbench.entries(p)['notes']
    assert any(n['text']=='Python SDK real isolated note' for n in notes)
    assert hashes=={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in hashes}
    assert app.state.automation.history(p,'yoshino')
    assert not app.state.automation.history(p,'rem')

def test_pending_proposal_outlives_python_and_duplicate_approval_is_safe(client):
    c,app,p,_=client;configure(app,p,mode='navigate')
    s=launch(c,p,'from novel_studio_api import Studio\nStudio.connect().notes.create("pending isolated note")\n')
    row=finish(c,s);assert row['pending']['kind']=='confirm'
    assert not app.state.workbench.entries(p)['notes']
    body={'token':row['pending']['token'],'approved':True,'context':{'project':p,'page':'write','path':'chapters/chapter-2/draft.txt'}}
    first=c.post('/api/assistant/sessions/'+s['id']+'/reply',json=body);assert first.status_code==200,first.text
    second=c.post('/api/assistant/sessions/'+s['id']+'/reply',json=body)
    # A simultaneous mutation may be rejected by the existing global lease;
    # either that or the one-shot duplicate receipt must not create another note.
    assert second.status_code in (200,409),second.text
    until=time.monotonic()+5
    while time.monotonic()<until and not app.state.workbench.entries(p)['notes']:time.sleep(.05)
    assert len(app.state.workbench.entries(p)['notes'])==1
    until=time.monotonic()+5
    while time.monotonic()<until:
        third=c.post('/api/assistant/sessions/'+s['id']+'/reply',json=body)
        if third.status_code==200:break
        assert third.status_code==409;time.sleep(.05)
    assert third.json().get('duplicate') is True
    assert len(app.state.workbench.entries(p)['notes'])==1

def test_cancel_python_revokes_late_writes(client):
    c,app,p,_=client;configure(app,p,mode='draft')
    row=launch(c,p,'import time\nfrom novel_studio_api import Studio\ntime.sleep(15)\nStudio.connect().notes.create("should not execute")\n')
    response=c.post('/api/assistant/sessions/'+row['id']+'/cancel');assert response.status_code==200,response.text
    row=finish(c,row)
    assert row['task']['status']=='CANCELLED'
    assert not app.state.workbench.entries(p)['notes']
    assert not app.state.automation.processes

def test_manuscript_read_requires_explicit_permission(client):
    c,app,p,_=client;configure(app,p,mode='draft')
    row=finish(c,launch(c,p,'from novel_studio_api import Studio\nprint(Studio.connect().chapters.read(1))\n'))
    assert row['task']['status']=='FAILED'
    assert '明确允许' in row['output']

def test_two_studio_clients_share_unique_stdio_request_ids(client):
    c,app,p,_=client
    row=finish(c,launch(c,p,'from novel_studio_api import Studio\na=Studio.connect()\nb=Studio.connect()\nprint(a.projects.current())\nprint(b.chapters.list())\nprint(a.projects.current())\n'))
    assert row['task']['status']=='SUCCEEDED',row
    assert [step['tool'] for step in row['steps']]==['get_active_project','list_chapters','get_active_project']

def test_convert_first_notebook_todos_preserves_sources_and_is_idempotent(client):
    c,app,p,_=client;configure(app,p,mode='draft',setting_context=True)
    row=finish(c,launch(c,p,'from novel_studio_api import Studio\ns=Studio.connect()\ns.notes.create("check source")\ns.notes.create("check source")\ns.notes.create("check time")\n'))
    assert row['task']['status']=='SUCCEEDED'
    notes=app.state.workbench.entries(p)['notes'];ids=[n['id'] for n in notes]
    from app.automation.service import Run
    s=app.state.automation.session(Run(persona='yoshino',instruction='Convert isolated ideas',context={'project':p},code='print(1)'))
    args={'ids':ids,'chapter':2}
    result=app.state.assistant.actions.execute(s,'inspirations_to_todos',args)
    assert len(result['created'])==3 and len(result['exact_duplicate_groups'])==1
    again=app.state.assistant.actions.execute(s,'inspirations_to_todos',args)
    assert not again['created'] and len(again['already_converted'])==3
    board=app.state.workbench.entries(p)
    assert len(board['notes'])==3 and len(board['todos'])==3
    assert {v['source'] for v in board['todos']}=={'INSPIRATION:'+id for id in ids}

def test_external_grant_has_schema_scope_idempotency_and_origin_guard(client):
    c,app,p,_=client
    response=c.post('/api/control/grants',json={'persona':'yoshino','instruction':'Author grants local SDK','context':{'project':p}})
    assert response.status_code==201,response.text
    grant=response.json();headers={'X-Novel-Control':grant['token']}
    body={'call_id':'first','action':'get_active_project','arguments':{}}
    created=c.post('/api/control/call',json=body,headers=headers);assert created.status_code==202,created.text
    assert c.post('/api/control/call',json=body,headers=headers).json()==created.json()
    assert c.post('/api/control/call',json={**body,'action':'get_project_status'},headers=headers).status_code==409
    until=time.monotonic()+5
    while time.monotonic()<until:
        result=c.get('/api/control/calls/'+created.json()['task_id'],headers=headers).json()
        if result['status']=='SUCCEEDED':break
        time.sleep(.05)
    assert result['result']['result']['id']==p
    assert c.post('/api/control/call',json=body,headers={**headers,'Origin':'https://untrusted.invalid'}).status_code==403
    assert c.post('/api/control/call',json=body,headers={'X-Novel-Control':'incorrect'}).status_code==403
    app.state.automation.active_project='other-project'
    assert c.post('/api/control/call',json={**body,'call_id':'next'},headers=headers).status_code==409

def test_registry_mcp_and_python_keep_one_permission_definition():
    from app.assistant.actions import TOOLS
    from app.assistant.mcp_bridge import MCP_ACTIONS
    assert set(TOOLS)==set(MCP_ACTIONS)
    assert TOOLS['run_python_plan'].level==2
    assert TOOLS['start_text_task'].level==3
    assert not {'run_shell','execute_sql','read_api_key'} & set(TOOLS)

def test_invalid_continuation_does_not_register_ghost_session(client):
    c,app,p,_=client
    before=set(app.state.assistant.sessions)
    response=c.post('/api/control/run',json={'persona':'yoshino','instruction':'invalid continuation','context':{'project':p},'code':'print(1)','previous_session':'a'*32})
    assert response.status_code==403
    assert set(app.state.assistant.sessions)==before

def test_task_ownership_is_durable_but_cross_persona_access_is_not_implicit(client):
    c,app,p,_=client
    from app.automation.service import Run
    first=app.state.automation.session(Run(persona='yoshino',instruction='Ownership fixture',context={'project':p},code='print(1)'))
    app.state.automation.remember_task(first,'controlled-fixture','codex::test')
    first.ended=True
    again=app.state.automation.session(Run(persona='yoshino',instruction='Reopen fixture',context={'project':p},code='print(1)'))
    other=app.state.automation.session(Run(persona='rem',instruction='Other persona fixture',context={'project':p},code='print(1)'))
    assert 'controlled-fixture' in again.controlled_tasks
    assert 'controlled-fixture' not in other.controlled_tasks
    assert not app.state.automation.task_access(p,'rem')

def test_explicit_completed_result_handoff_is_read_only(client,monkeypatch):
    c,app,p,_=client
    from app.automation.service import Run
    from app.assistant.models import TaskShare
    from app.assistant.actions import TOOLS
    from types import SimpleNamespace
    a=app.state.automation.session(Run(persona='yoshino',instruction='Handoff fixture',context={'project':p},code='print(1)'))
    a.controlled_tasks.add('completed-fixture')
    monkeypatch.setattr(a.manager,'get',lambda id:SimpleNamespace(id=id,status='SUCCEEDED'))
    assert TOOLS['share_task_result'].level==3
    receipt=app.state.automation.share_task(a,TaskShare(id='completed-fixture',persona='rem',note='Author-approved fixed fixture'))
    assert receipt['access']=='read-only' and receipt['includes_other_conversations'] is False
    assert not app.state.automation.task_access(p,'rem')
    b=app.state.automation.session(Run(persona='rem',instruction='Receiver fixture',context={'project':p},code='print(1)'))
    app.state.assistant.configure(__import__('app.assistant.models',fromlist=['AssistantSettings']).AssistantSettings(setting_context=True),'rem',p)
    b.settings=app.state.assistant.settings('rem',p)
    assert app.state.assistant.actions.execute(b,'list_shared_results',{})['results'][0]['id']=='completed-fixture'
    from app.errors import ConsoleError
    with pytest.raises(ConsoleError):app.state.assistant.actions.execute(b,'stop_controlled_task',{'id':'completed-fixture'})

def test_completed_result_uses_opted_in_private_project_history(client):
    c,app,p,_=client
    from app.automation.service import Run
    from types import SimpleNamespace
    s=app.state.automation.session(Run(persona='yoshino',instruction='Private result fixture',context={'project':p},code='print(1)'))
    task=SimpleNamespace(id='a'*32,status='SUCCEEDED',result={'output':'isolated task result'},error=None,ai_metadata={'model':'fixture, not actual AI'},finished_at='fixture')
    app.state.automation.remember_task(s,task.id,'fixture')
    s.controlled_tasks.add(task.id);app.state.automation.remember_task_result(s,task)
    assert app.state.automation.task_result(s,task.id)['result']['output']=='isolated task result'
    configure(app,p,save_conversation=False)
    task.id='b'*32;app.state.automation.remember_task_result(s,task)
    assert not (app.state.automation.folder(p,'yoshino')/('ai_'+task.id+'.json')).exists()


@pytest.mark.parametrize("flag,module", [
    ("--python-control-worker", "app.automation.worker"),
    ("--world-logic-worker", "app.world_logic.worker"),
    ("--assistant-mcp", "app.assistant.mcp_server"),
])
def test_launcher_workers_skip_desktop_data_initialization(monkeypatch, flag, module):
    import runpy
    from types import ModuleType
    sentinel=ModuleType(module); calls=[]
    sentinel.main=lambda:calls.append(flag)
    monkeypatch.setitem(sys.modules,module,sentinel)
    monkeypatch.setattr(sys,"argv",["NovelStudio.exe",flag])
    monkeypatch.setattr(Path,"home",classmethod(lambda cls: (_ for _ in ()).throw(AssertionError("Worker touched home"))))
    with pytest.raises(SystemExit) as exit:
        runpy.run_path(str(ROOT/"desktop/launcher.py"),run_name="__main__")
    assert exit.value.code==0
    assert calls==[flag]


def test_idle_external_grant_does_not_block_builtin_python(client):
    c,app,p,_=client
    response=c.post('/api/control/grants',json={'persona':'yoshino','instruction':'Idle local grant','context':{'project':p}})
    assert response.status_code==201
    grant=response.json()
    row=finish(c,launch(c,p,'print("builtin remains usable")'))
    assert row['task']['status']=='SUCCEEDED',row
    source=app.state.assistant.sessions[grant['session_id']]
    source.pending={'kind':'confirm','token':'isolated-fixed-confirmation'}
    blocked=c.post('/api/control/run',json={'persona':'yoshino','instruction':'Must serialize pending confirmation','context':{'project':p},'code':'print(1)'})
    assert blocked.status_code==409
    source.pending=None


def test_director_handoff_runs_real_wasi_without_granting_other_records(client):
    from app.creative.director import Create,Patch
    from app.creative.writing import ContextChoice,Approval
    c,app,p,engine=client;configure(app,p,mode='navigate')
    director=app.state.creative_director;path='chapters/chapter-90/draft.txt'
    f=engine/'projects'/p/path;f.parent.mkdir(parents=True);f.write_text('隔离测试正文，不作正式采用。\n',encoding='utf-8');doc=director.tools.doc(p,path)
    actor=director.tools.characters.list(p)[0]['canonical']['id']
    context=director.writing.preview(p,ContextChoice(path=path,revision=doc['etag'],pov=actor))
    director.writing.approve(p,context['id'],Approval(context_hash=context['context_hash'],confirm=True))
    row=director.create(p,Create(path=path,revision=doc['etag'],context_id=context['id'],goal='Local original fixture only',executor='codex'))
    row=director.patch(p,row['id'],Patch(etag=row['etag'],draft='隔离候选，尚未采用。'))
    original=(engine/'projects'/p/path).read_bytes()
    script='from novel_studio_api import Studio\ns=Studio.connect()\nr=s.call("get_director_result")\nassert r["draft"]=="隔离候选，尚未采用。"\nassert "context_id" not in r\nprint(r["draft_sha256"])\n'
    args={'persona':'yoshino','instruction':'Author-selected frozen candidate','context':{'project':p,'page':'write','path':path},'code':script,'model':'codex-software','timeout':40,'director_handoff':{'id':row['id'],'etag':row['etag']}}
    result=c.post('/api/control/run',json=args);assert result.status_code==202,result.text
    outcome=finish(c,result.json());assert outcome['task']['status']=='SUCCEEDED',outcome
    assert outcome.get('python_run_id')==result.json()['run_id']
    note={'project':p,'persona':'yoshino','record_id':row['id'],'run_id':result.json()['run_id'],'etag':row['etag'],'comment':'Author-only local counts'}
    saved=c.post('/api/control/director-note',json=note);assert saved.status_code==200,saved.text
    row=saved.json();assert len(row['analysis_notes'])==1 and row['draft']=='隔离候选，尚未采用。'
    duplicate=c.post('/api/control/director-note',json={**note,'etag':row['etag']});assert duplicate.status_code==200 and len(duplicate.json()['analysis_notes'])==1
    assert c.post('/api/control/director-note',json={**note,'persona':'rem','etag':row['etag']}).status_code==404
    assert c.post('/api/control/director-note',json={**note,'output':'forged result','etag':row['etag']}).status_code==422
    assert (engine/'projects'/p/path).read_bytes()==original
    no_grant=finish(c,launch(c,p,'from novel_studio_api import Studio\nStudio.connect().call("get_director_result")'))
    assert no_grant['task']['status']=='FAILED'
    updated=director.patch(p,row['id'],Patch(etag=row['etag'],draft='A new candidate version.'))
    stale=c.post('/api/control/run',json=args);assert stale.status_code==409
    invalid=dict(args,director_handoff={'id':row['id'],'etag':'0'*64})
    assert c.post('/api/control/run',json=invalid).status_code==409
    assert app.state.automation.history(p,'yoshino')[0].get('status') in ('SUCCEEDED','FAILED')
