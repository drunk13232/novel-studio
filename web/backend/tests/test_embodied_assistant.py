from types import SimpleNamespace
import threading
import pytest
from pydantic import ValidationError
from app.assistant.models import Start,Context,AssistantSettings
from app.assistant.service import AssistantCenter
from app.errors import ConsoleError
from app.creative.reviews import Start as ReviewStart,ReviewCenter

def center(tmp_path):
    c=AssistantCenter.__new__(AssistantCenter);c.root=tmp_path;c.lock=threading.RLock();return c

def test_persona_configuration_isolated_and_default_backward_compatible(tmp_path):
    c=center(tmp_path);c.configure(AssistantSettings(model='codex-software'))
    c.configure(AssistantSettings(mode='suggest',selection=True),'rem')
    assert c.settings('rem').selection
    assert not c.settings('yoshino').selection
    assert not c.settings().selection
    assert center(tmp_path).settings('rem').mode=='suggest'
    with pytest.raises(ConsoleError):c.settings('../private')

def test_persona_schema_rejects_unregistered_identity():
    with pytest.raises(ValidationError):Start(instruction='hello',context=Context(),persona='other-project')

@pytest.mark.parametrize('name',['run_shell','create_project_backup','create_character_draft','create_chapter_draft','open_project'])
def test_visual_shortcut_does_not_expose_all_actions(tmp_path,name):
    with pytest.raises(ConsoleError,match='未开放'):center(tmp_path).start_local_action(Start(instruction='test',context=Context()),name,{})

def test_review_selection_rejects_stale_or_mismatched_text_before_any_model():
    c=ReviewCenter.__new__(ReviewCenter)
    c.tools=SimpleNamespace(writable=lambda p:None,doc=lambda p,path:{'content':'😀公开选段，私密尾部','line_ending':'LF','etag':'a'*64})
    for b in [ReviewStart(path='draft.md',selection='公开选段',selection_start=2,selection_end=6,source_revision='b'*64),ReviewStart(path='draft.md',selection='错误文本',selection_start=2,selection_end=6,source_revision='a'*64)]:
        with pytest.raises(ConsoleError,match='选段或正文版本已变化'):c.start('isolated',b)


def test_approved_review_uses_existing_frontend_task_receipt():
    from app.assistant.actions import Actions
    actions=Actions.__new__(Actions)
    actions.registry=SimpleNamespace(get=lambda p:{'id':p})
    calls=[]
    session=SimpleNamespace(project='isolated',persona='rem',request_model=None,settings=AssistantSettings(selection=True),center=SimpleNamespace(settings=lambda *args:AssistantSettings(selection=True)),front=lambda name,args:calls.append((name,args)) or {'ok':True,'id':'task','review_id':'review'})
    result=actions.execute(session,'start_literary_review',{'path':'chapters/chapter-1/draft.md','selection':'测试','selection_start':0,'selection_end':2,'source_revision':'a'*64})
    assert result['review_id']=='review'
    assert calls[0][0]=='start_literary_review'
    assert calls[0][1]['selection']=='测试'


def test_failed_frontend_wait_clears_pending_receipt():
    from app.assistant.service import Session
    session=Session.__new__(Session)
    session.cv=threading.Condition();session.project='isolated';session.pending=None;session.response=None
    session.timing=SimpleNamespace(mark=lambda *a,**k:None)
    count=[0]
    def check():
        count[0]+=1
        if count[0]>1:raise ConsoleError('cancelled',409)
    session.check=check
    with pytest.raises(ConsoleError):session.wait('frontend','set_theme',{'theme':'mist'})
    assert session.pending is None and session.response is None


@pytest.mark.parametrize('kind,payload,expected',[
    ('frontend',{'ok':False,'error':'CONTROLLED_PREFLIGHT_TIMEOUT'},'CONTROLLED_PREFLIGHT_TIMEOUT'),
    ('confirm',{'ok':False,'error':'CONTROLLED_PREFLIGHT_TIMEOUT'},'用户拒绝'),
    ('frontend',{'ok':True,'error':'CONTROLLED_FAKE_SUCCESS'},'用户拒绝'),
    ('frontend',{'ok':False,'error':{'untrusted':'object'}},'用户拒绝'),
])
def test_unapproved_receipts_keep_failure_reason_without_granting_permission(kind,payload,expected):
    from app.assistant.service import Session
    session=Session.__new__(Session)
    session.cv=threading.Condition();session.project='isolated';session.pending=None;session.response=None
    session.timing=SimpleNamespace(mark=lambda *a,**k:None)
    def deliver_failed_receipt():
        if session.pending:session.response={'approved':False,'result':payload}
    session.check=deliver_failed_receipt
    with pytest.raises(ConsoleError,match=expected):session.wait(kind,'set_theme',{'theme':'mist'})
    assert session.pending is None and session.response is None


def test_live_confirmation_execution_cancellation_is_checked_after_planner_turn_ends():
    import time
    from app.assistant.service import Session
    s=Session.__new__(Session)
    s.ended=True;s.confirming=True;s.cancelled=False;s.deadline=time.monotonic()+10
    s.task=SimpleNamespace(cancel_requested=False)
    s.execution_task=SimpleNamespace(cancel_requested=True)
    with pytest.raises(ConsoleError,match='助手已停止'):s.check()
    s.execution_task.cancel_requested=False
    s.check()  # A completed planner does not invalidate a live author-confirmed execution.
