"""Actual launcher Bridge logic with fake window/backups; no native UI acceptance."""
import importlib.util,threading
from pathlib import Path
from types import SimpleNamespace
import pytest

@pytest.fixture
def launcher(monkeypatch,tmp_path):
 root=Path(__file__).resolve().parents[3]
 monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'local'))
 monkeypatch.setenv('NOVEL_STUDIO_HOME',str(tmp_path/'home'))
 monkeypatch.syspath_prepend(str(root/'desktop'))
 spec=importlib.util.spec_from_file_location('desktop_exit_contract',root/'desktop/launcher.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 monkeypatch.setattr(module,'native',lambda key:key)
 return module

class Window:
 def __init__(self):self.destroyed=threading.Event();self.calls=0
 def destroy(self):self.calls+=1;self.destroyed.set()

def bridge(launcher,active=None,backup=None):
 calls=[]
 def scheduled(**kw):
  assert kw=={'exit':True};calls.append(kw)
  if backup:backup()
 state=SimpleNamespace(active_tasks=active or (lambda:[]),data_center=SimpleNamespace(scheduled=scheduled))
 b=launcher.Bridge(SimpleNamespace(state=state),{});b._window=Window();return b,calls

def join_close(b):
 if b._exit_thread:b._exit_thread.join(3)

def test_active_task_blocks_before_backup(launcher):
 b,calls=bridge(launcher,active=lambda:['owned-task']);result=b.request_exit()
 assert not result['ok'] and not calls and not b._allow_close and not b._window.calls

def test_new_task_after_backup_blocks_close(launcher):
 active=[]
 b,calls=bridge(launcher,active=lambda:active,backup=lambda:active.append('new-task'))
 result=b.request_exit();join_close(b)
 assert result['ok'] is False
 assert len(calls)==1 and not b._allow_close and b._window.calls==0

def test_repeated_accepted_close_does_not_repeat_backup_or_destroy(launcher):
 b,calls=bridge(launcher)
 assert b.request_exit()['ok'];join_close(b)
 assert b.request_exit()['ok'];join_close(b)
 assert len(calls)==1 and b._window.calls==1

def test_backup_failure_is_retryable_without_allowing_close(launcher):
 fail=[True]
 def backup():
  if fail[0]:raise OSError('ISOLATED_BACKUP_FAILURE')
 b,calls=bridge(launcher,backup=backup);result=b.request_exit()
 assert not result['ok'] and not b._allow_close and not b._window.calls
 fail[0]=False;assert b.request_exit()['ok'];join_close(b)
 assert len(calls)==2 and b._window.calls==1

def test_concurrent_preparation_has_one_owner(launcher):
 entered=threading.Event();release=threading.Event();result=[]
 def backup():entered.set();assert release.wait(3)
 b,calls=bridge(launcher,backup=backup)
 first=threading.Thread(target=lambda:result.append(b.request_exit()),name='IsolatedExitCaller');first.start()
 try:
  assert entered.wait(2);second=b.request_exit();assert second['ok'] is False
  assert second['error']=='exitAlreadyPreparing' and len(calls)==1 and not b._window.calls
 finally:release.set();first.join(3);join_close(b)
 assert result==[{'ok':True}] and b._window.calls==1

def test_window_waits_for_actual_reply_worker_to_finish(launcher):
 ready=threading.Event();release=threading.Event();result=[]
 b,calls=bridge(launcher)
 def caller():
  result.append(b.request_exit());ready.set();assert release.wait(3)
 thread=threading.Thread(target=caller,name='IsolatedReplyWorker');thread.start()
 try:assert ready.wait(2);assert not b._window.destroyed.is_set()
 finally:release.set();thread.join(3);join_close(b)
 assert result==[{'ok':True}] and len(calls)==1 and b._window.calls==1
def test_close_worker_start_failure_can_retry(launcher,monkeypatch):
 b,calls=bridge(launcher);original=launcher.threading.Thread
 def fail(*args,**kwargs):raise RuntimeError('ISOLATED_THREAD_START_FAILURE')
 monkeypatch.setattr(launcher.threading,'Thread',fail)
 result=b.request_exit();assert result=={'ok':False,'error':'exitCloseFailed'}
 assert not b._allow_close and b._exit_thread is None and not b._window.calls
 monkeypatch.setattr(launcher.threading,'Thread',original)
 assert b.request_exit()['ok'];join_close(b)
 assert len(calls)==2 and b._window.calls==1

def test_exit_native_messages_have_real_english_and_chinese():
 import json
 root=Path(__file__).resolve().parents[3]/'web/frontend/public/locales'
 for key in ['exitAlreadyPreparing','exitCloseFailed']:
  values=[json.loads((root/lang/'desktop.json').read_text('utf8'))[key] for lang in ['en','zh-CN']]
  assert all(isinstance(v,str) and len(v)>8 for v in values) and values[0]!=values[1]
