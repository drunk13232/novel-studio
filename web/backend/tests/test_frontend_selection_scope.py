"""Existing frontend-operation ownership at selection task creation; no model inference."""
from types import SimpleNamespace
import threading
import pytest
from app.assistant.service import AssistantCenter
from app.errors import ConsoleError
from app.studio_tools import FrontendOrigin,SelectionRequest

def setup_scope():
    calls=[];remember=[]
    owner=FrontendOrigin(session_id='a'*32,token='b'*32)
    body=SelectionRequest(frontend_origin=owner,project_id='isolated',chapter_id='chapter-1',path='chapters/chapter-1/draft.md',document_revision='c'*64,originalHash='d'*64,start=0,end=2,selected_text='测试',instruction='CONTROLLED_SELECTION',ai_model='codex')
    s=SimpleNamespace(cv=threading.Condition(),project='isolated',response=None,context=SimpleNamespace(path=body.path,selection=body.selected_text),pending={'kind':'frontend','tool':'propose_chapter_revision','project':'isolated','token':owner.token,'arguments':{'instruction':body.instruction}},check=lambda:None)
    c=AssistantCenter.__new__(AssistantCenter);c.session=lambda id:s if id==owner.session_id else (_ for _ in ()).throw(ConsoleError('unknown',404))
    c.app=SimpleNamespace(state=SimpleNamespace(automation=SimpleNamespace(remember_task=lambda *v:remember.append(v))))
    def start(project,request):calls.append((project,request));return {'id':'actual-task','candidate_id':'candidate','status':'QUEUED'}
    return c,s,body,start,calls,remember

@pytest.mark.parametrize('change',['cancelled','project','token','tool','path','selection','instruction','already-replied'])
def test_invalid_frontend_origin_cannot_create_a_task(change):
    c,s,b,start,calls,_=setup_scope()
    if change=='cancelled':s.check=lambda:(_ for _ in ()).throw(ConsoleError('cancelled',409))
    elif change=='project':s.project='other'
    elif change=='token':s.pending['token']='e'*32
    elif change=='tool':s.pending['tool']='open_chapter'
    elif change=='path':s.context.path='another.md'
    elif change=='selection':s.context.selection='another range'
    elif change=='instruction':s.pending['arguments']['instruction']='different confirmed instruction'
    elif change=='already-replied':s.response={'approved':False}
    with pytest.raises(ConsoleError):c.start_frontend_selection('isolated',b,start)
    assert not calls


def test_live_operation_creates_one_task_and_reuses_existing_child_ownership():
    c,s,b,start,calls,remember=setup_scope()
    result=c.start_frontend_selection('isolated',b,start)
    assert result['id']=='actual-task' and len(calls)==1
    assert s.controlled_tasks==s.spawned_tasks=={'actual-task'} and len(remember)==1
    with pytest.raises(ConsoleError,match='已提交'):c.start_frontend_selection('isolated',b,start)
    assert len(calls)==1


def test_history_failure_keeps_actual_receipt_stop_link_and_duplicate_guard():
    c,s,b,start,calls,_=setup_scope()
    c.app.state.automation.remember_task=lambda *v:(_ for _ in ()).throw(OSError('controlled history failure'))
    result=c.start_frontend_selection('isolated',b,start)
    assert result['id']=='actual-task' and result['warning'] and s.spawned_tasks=={'actual-task'}
    with pytest.raises(ConsoleError,match='已提交'):c.start_frontend_selection('isolated',b,start)
    assert len(calls)==1


def test_preflight_failure_is_not_consumed_as_a_started_task():
    c,s,b,start,calls,_=setup_scope()
    def preflight(*v):raise ConsoleError('controlled preflight requires author notice',409)
    with pytest.raises(ConsoleError):c.start_frontend_selection('isolated',b,preflight)
    assert not s.pending.get('selection_submitted')
    assert c.start_frontend_selection('isolated',b,start)['id']=='actual-task' and len(calls)==1
