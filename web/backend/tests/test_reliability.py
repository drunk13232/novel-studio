import asyncio
import json
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from app.projects.models import Idea
from app.projects.service import DraftStore
from app.tasks.storage import TaskStore,atomic_json
from app.tasks.manager import TaskManager,Task
from app.tasks.router import TaskRouter
from app.workspace.service import WorkspaceService
from app.models.requests import TaskRequest

ENGINE=Path(__file__).resolve().parents[3]

def engine(tmp_path):
    shutil.copytree(ENGINE/'engine',tmp_path/'engine');shutil.copytree(ENGINE/'templates',tmp_path/'templates')
    return tmp_path

def test_task_restart_metadata_result_and_paged_evidence(tmp_path):
    root=engine(tmp_path);ws=WorkspaceService(root)
    m=TaskManager(ws,TaskRouter(ws));t=Task('a'*32,TaskRequest(type='custom_prompt',prompt='fixture'), 'project-main',workspace=root)
    m.tasks[t.id]=t;t.status='SUCCEEDED';t.finished_at='2026-10-26T00:00:00+00:00';t.result={'output':'Fixture result'};t.codex_thread_id='thread_fixture'
    for n in range(750):m.emit(t,'message',str(n))
    restarted=TaskManager(ws,TaskRouter(ws));restored=restarted.get(t.id)
    assert restored.status=='SUCCEEDED' and restored.result==t.result and restored.codex_thread_id=='thread_fixture'
    assert len((m.store.path(t.id)/'events.jsonl').read_text().splitlines())==750
    tail=m.store.page(t.id,limit=50);earlier=m.store.page(t.id,before=tail['next_before'],limit=50)
    assert tail['has_more'] and tail['events'][0]['id']==701 and earlier['events'][-1]['id']==700

def test_restart_running_interrupted_not_success(tmp_path,monkeypatch):
    monkeypatch.setattr('app.tasks.storage.process_alive',lambda pid:False)
    root=engine(tmp_path);store=TaskStore(root)
    t=Task('b'*32,TaskRequest(type='custom_prompt',prompt='fixture'),'project-main',status='RUNNING',workspace=root)
    store.save(t);store.recover();row=store.rows()[0]
    assert row['status']=='INTERRUPTED' and row['reason']=='backend_restart' and row['finished_at']
    assert store.page(t.id)['events'][-1]['type']=='task_interrupted'

def test_wizard_step_proposal_restart_and_confirmed_discard(tmp_path):
    root=engine(tmp_path);d=DraftStore(root);r=d.create(Idea(title='Fixture Novel',premise='A discovers B.'))
    r=d.update(r['id'],r['version'],wizard_step=4)
    # Already generated proposal persistence is tested without rerunning a model.
    from tests.test_projects import fixture_proposal
    r=d.update(r['id'],r['version'],input=Idea(title='Fixture Novel',locked_constraints=fixture_proposal()['user_locked']).model_dump())
    r=d.update(r['id'],r['version'],proposal=fixture_proposal(),wizard_step=5)
    restored=DraftStore(root).get(r['id']);assert restored['wizard_step']==5 and restored['proposal']==r['proposal'] and restored['proposal_revision']==1
    app=create_app(Settings(workspace=root));app.state.testing=True;c=TestClient(app)
    c.headers['X-Novel-Request']=c.get('/api/session').json()['request_token']
    assert len(c.get('/api/drafts').json())==1
    assert c.post('/api/drafts/'+r['id']+'/discard',json={'version':r['version'],'confirm':False}).status_code==422
    assert c.post('/api/drafts/'+r['id']+'/discard',json={'version':r['version'],'confirm':True}).status_code==200
    assert not d.path(r['id']).exists() and c.get('/api/drafts').json()==[]

def test_draft_input_equal_does_not_erase_proposal(tmp_path):
    root=engine(tmp_path);d=DraftStore(root);r=d.create(Idea(title='Fixture Novel'))
    r['proposal']={'fixture':'persisted'};d.rows[r['id']]=r;d.persist(r)
    saved=d.update(r['id'],r['version'],input=r['input'],wizard_step=4)
    assert saved['proposal']==r['proposal']
def test_windows_transient_replace_retry(tmp_path,monkeypatch):
    import app.atomic as atomic
    original=atomic.os.replace;calls=[]
    def blocked_once(a,b):
        calls.append(1)
        if len(calls)==1:raise PermissionError('temporary reader')
        return original(a,b)
    monkeypatch.setattr(atomic.os,'replace',blocked_once)
    monkeypatch.setattr(atomic.time,'sleep',lambda t:None)
    source=tmp_path/'new';target=tmp_path/'old';source.write_text('new');target.write_text('old')
    atomic.replace(source,target)
    assert target.read_text()=='new' and len(calls)==2
