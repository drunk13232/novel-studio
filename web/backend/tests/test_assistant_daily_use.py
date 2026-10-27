from types import SimpleNamespace
import json
from app.assistant.local_commands import exact_action
from app.assistant.conversations import Conversations
from app.tasks.storage import atomic_json

def test_exact_ui_route_never_interprets_compound_or_ambiguous_instruction():
    assert exact_action('打开第八章')==('open_chapter',{'number':8})
    assert exact_action('打开第十二章')==('open_chapter',{'number':12})
    assert exact_action('打开第十十章') is None
    assert exact_action('打开第八章然后修改正文') is None
    assert exact_action('请解释切换青岚主题的风险') is None
    assert exact_action('把正文字号调到18号')==('set_editor_font_size',{'size':18})

def test_private_dialogue_scopes_and_budget(tmp_path):
    c=Conversations(tmp_path)
    rows=[{'id':str(i),'instruction':'问'*2200,'output':'答'*2200,'status':'SUCCEEDED','pending_confirmation':False} for i in range(30)]
    atomic_json(c.path('novel-one','rem','provider::one'),rows)
    assert not c.context('novel-one','yoshino','provider::one')
    assert not c.context('novel-two','rem','provider::one')
    assert not c.context('novel-one','rem','provider::two')
    replay=c.context('novel-one','rem','provider::one')
    assert 0<len(replay)<len(rows)
    assert len(json.dumps(replay,ensure_ascii=False))<10100
    # Reloading storage must not need a live model client or old Thread.
    assert Conversations(tmp_path).page('novel-one','rem','provider::one')['rows']==rows

def test_pending_or_failed_turns_do_not_authorize_replay(tmp_path):
    c=Conversations(tmp_path)
    atomic_json(c.path(None,'rem','codex'),[{'id':'x','instruction':'执行','output':'等待确认','status':'SUCCEEDED','pending_confirmation':True}])
    assert c.context(None,'rem','codex-software')==[]

def test_recognition_http_rejects_arbitrary_audio_path():
    from app.local_speech import RecognitionRequest
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):RecognitionRequest(owner='test',audio_file='C:/private.wav')


def test_codex_reuse_requires_identical_project_model_context_and_permissions():
    import copy,time
    from app.assistant.codex_mcp import Runner
    from app.assistant.models import AssistantSettings
    from app.ai.controls import RequestControls
    old=SimpleNamespace(ended=True,cancelled=False,pending=None,confirming=False,scope_changed=False,project='project-one',persona='rem',settings=AssistantSettings(),ai_controls=RequestControls(model='codex::model-a',parameters={'reasoning_effort':'low'}))
    runner=Runner.__new__(Runner);runner.session=old;runner.closed=False;runner.busy=False;runner.thread_id='owned-thread';runner.idle_until=time.monotonic()+120
    next=copy.deepcopy(old)
    assert runner.compatible(next)
    for key,value in [('project','project-two'),('persona','yoshino')]:
        changed=copy.deepcopy(next);setattr(changed,key,value);assert not runner.compatible(changed)
    for field,value in [('model','codex::model-b'),('parameters',{'reasoning_effort':'high'})]:
        changed=copy.deepcopy(next);setattr(changed.ai_controls,field,value);assert not runner.compatible(changed)
    changed=copy.deepcopy(next);changed.ai_controls.context.history='off';assert not runner.compatible(changed)
    changed=copy.deepcopy(next);changed.settings.manuscript=True;assert not runner.compatible(changed)
    old.pending={'kind':'confirm'};assert not runner.compatible(next)
    old.pending=None;old.scope_changed=True;assert not runner.compatible(next)
    old.scope_changed=False;old.cancelled=True;assert not runner.compatible(next)
