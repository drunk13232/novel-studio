"""Focus summaries read existing saved deltas; they never infer writing time."""
import copy
from datetime import date
from types import SimpleNamespace
import pytest
from app.writing_metrics import Metrics,FocusSummaryRequest
from app.library.storage import write
from app.errors import ConsoleError

def metrics(tmp_path):
    registry=SimpleNamespace(workspace=lambda project:SimpleNamespace(root=tmp_path/project))
    return Metrics(SimpleNamespace(registry=registry))

def state(service,project,events):
    write(service.path(project),{'events':events,'snapshots':{},'goals':{},'notes':{}})

def event(value,source='MANUAL',method='NET_SAVE_DIFF'):
    return {'id':str(value)+source,'at':'2026-10-24T12:00:00+08:00','path':'chapters/story/draft.txt','han':value,'characters':value,'source':source,'method':method}

def test_focus_cursor_reads_only_new_saved_events_and_stays_project_bound(tmp_path,monkeypatch):
    monkeypatch.setattr('app.writing_metrics._today',lambda:date(2026,10,24))
    service=metrics(tmp_path);state(service,'one',[event(100)])
    boundary=service.focus_boundary('one');original=service.path('one').read_bytes()
    assert service.path('one').read_bytes()==original
    state(service,'one',[event(100),event(6),event(-4),event(5,'AI_ACCEPT'),event(99,'UNKNOWN','OBSERVED_EXTERNAL_ESTIMATE')])
    original=service.path('one').read_bytes();summary=service.focus_summary('one',FocusSummaryRequest(cursor=boundary['cursor']))
    assert summary['net_han']==7 and summary['manual_han']==2 and summary['ai_han']==5 and summary['save_count']==3
    assert summary['excluded_estimates']==1 and service.path('one').read_bytes()==original
    state(service,'two',[event(100)])
    with pytest.raises(ConsoleError):service.focus_summary('two',FocusSummaryRequest(cursor=boundary['cursor']))

def test_empty_focus_no_events_does_not_create_stat_file(tmp_path):
    service=metrics(tmp_path);boundary=service.focus_boundary('empty')
    value=service.focus_summary('empty',FocusSummaryRequest(cursor=boundary['cursor']))
    assert value['net_han']==0 and value['save_count']==0
    assert not service.path('empty').exists()

@pytest.mark.parametrize('events',[[],[event(99)]])
def test_focus_summary_rejects_changed_history(tmp_path,events):
    service=metrics(tmp_path);state(service,'one',[event(100)])
    b=service.focus_boundary('one');state(service,'one',events)
    with pytest.raises(ConsoleError):service.focus_summary('one',FocusSummaryRequest(cursor=b['cursor']))


def test_focus_end_cursor_excludes_saves_after_timer_end(tmp_path,monkeypatch):
    monkeypatch.setattr('app.writing_metrics._today',lambda:date(2026,10,24))
    service=metrics(tmp_path);start=service.focus_boundary('one')
    state(service,'one',[event(20)]);end=service.focus_boundary('one')
    state(service,'one',[event(20),event(999)])
    value=service.focus_summary('one',FocusSummaryRequest(cursor=start['cursor'],end_cursor=end['cursor']))
    assert value['net_han']==20 and value['save_count']==1 and value['end_event_count']==1
    with pytest.raises(ConsoleError):
        service.focus_summary('one',FocusSummaryRequest(cursor=end['cursor'],end_cursor=start['cursor']))
