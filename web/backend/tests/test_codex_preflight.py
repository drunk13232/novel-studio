"""Focused transport contracts, not evidence of remote model availability."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import BaseModel,ConfigDict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.codex.adapter import CodexAdapter
from app.errors import CodexUnavailable
class Result(BaseModel):
    model_config=ConfigDict(extra='allow')
class Client:
    def __init__(self,root,fail=None):self.root=root;self.calls=[];self.fail=fail;self.closed=False
    def start(self):self.calls.append('process_start')
    def initialize(self):self.calls.append('initialize')
    def account_read(self):raise AssertionError('Redundant account discovery must not block a real task')
    def close(self):self.closed=True
    def request(self,method,params,**kwargs):
        self.calls.append(method)
        if method==self.fail:raise RuntimeError('workspace routing discovery timed out')
        if method=='config/read':return Result(config={'model':'test-only','mcp_servers':{}})
        if method=='skills/list':return Result(data=[])
        if method=='thread/start':
            assert params['approvalPolicy']=='never' and params['permissions']=='novel_isolated'
            assert params['config']['permissions']['novel_isolated']['filesystem'][str(self.root)]=='read'
            assert params['config']['features']['shell_tool'] is False
            return Result(cwd=str(self.root),thread={'id':'00000000-0000-0000-0000-000000000001'},activePermissionProfile={'id':'novel_isolated'})
        raise AssertionError(method)
    def turn_start(self,thread,prompt,params):
        self.calls.append('turn/start')
        assert params['permissions']=='novel_isolated' and params['approvalPolicy']=='never'
        if self.fail=='turn/start':raise RuntimeError('Authentication required; please log in')
        return SimpleNamespace(turn=SimpleNamespace(id='turn-test'))
    def next_turn_notification(self,turn):
        return SimpleNamespace(method='turn/completed',payload=Result(turn={'status':'completed'}))

def adapter(tmp_path,monkeypatch,fail=None):
    root=tmp_path/'isolated';root.mkdir();(root/'AGENTS.md').write_text('Only public diagnostic text. No tools.','utf8')
    engine=tmp_path/'engine';engine.mkdir()
    a=CodexAdapter(root,engine,'WRITER',capsule=True);c=Client(root,fail);monkeypatch.setattr(a,'_new_client',lambda:c)
    return a,c

def test_actual_request_without_account_preflight_keeps_permissions(tmp_path,monkeypatch):
    a,c=adapter(tmp_path,monkeypatch);events=[];v=a.start_task('public test',lambda *x:events.append(x),read_only=True)
    assert v['status']=='completed' and c.closed
    assert c.calls==['process_start','initialize','config/read','skills/list','thread/start','turn/start']
    assert [r['codex_phase'] for r in a.timings]==['process_start','initialize','config_read','skills_list','thread_start','turn_start']
    assert all(r['phase_status']=='completed' and r['duration_ms']>=0 for r in a.timings)
    assert 'public test' not in str(a.timings)
    assert not any('已登录' in x[1] for x in events)

def test_exact_failed_stage_and_no_automatic_retry(tmp_path,monkeypatch):
    a,c=adapter(tmp_path,monkeypatch,'thread/start')
    with pytest.raises(CodexUnavailable,match=r'\[thread_start\]') as e:a.start_task('private text',lambda *x:None,read_only=True)
    assert '登录未被判定失效' in str(e.value) and c.calls.count('thread/start')==1 and c.closed
    assert a.timings[-1]['phase_status']=='failed' and 'private text' not in str(a.timings)

def test_actual_authentication_failure_is_not_treated_as_success(tmp_path,monkeypatch):
    a,c=adapter(tmp_path,monkeypatch,'turn/start')
    with pytest.raises(CodexUnavailable,match='Authentication required'):a.start_task('public test',lambda *x:None,read_only=True)
    assert c.closed and a.timings[-1]['phase_status']=='failed'


def test_routing_probe_failure_is_not_reported_as_a_lost_login(tmp_path,monkeypatch):
    a,c=adapter(tmp_path,monkeypatch)
    monkeypatch.setattr('app.codex.adapter.codex_binary',lambda:Path('codex.exe'))
    monkeypatch.setattr('app.codex.adapter.subprocess.run',lambda *a,**kw:SimpleNamespace(returncode=0,stdout='codex-cli 0.160.0'))
    def unavailable():raise RuntimeError('workspace routing discovery timed out')
    monkeypatch.setattr(c,'account_read',unavailable)
    result=a.health()
    assert not result['codex'] and result['probe_status']=='ROUTING_UNAVAILABLE'
    assert '不证明登录失效' in result['reason'] and c.closed
