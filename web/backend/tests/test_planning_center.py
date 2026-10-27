"""Real project-local plans and recorded links; no model calls or author works."""
import hashlib,json
import pytest
from pydantic import ValidationError
from test_writing_assist import service
from app.author_workbench import Entry,EntryStates
from app.planning_center import Schedule,plan_overview,impact_preview
from app.errors import ConsoleError

def protected(root):
    return {str(f):hashlib.sha256(f.read_bytes()).hexdigest() for name in ['chapters','characters','bible','state','settings','outlines'] for f in (root/name).rglob('*') if f.is_file()}

def test_scheduled_plan_reopens_in_same_notebook_and_old_editor_preserves_schedule(service):
    s,p,root=service;w=s.workbench;before=protected(root)
    row=w.save_entry(p,Entry(etag=w.entries(p)['etag'],kind='todo',text='Review chapter',schedule=Schedule(start_date='2026-10-26',due_date='2026-11-01',progress=25,steps=[{'text':'Read sources','done':True},{'text':'Review draft'}])))
    plan=row['todos'][0];assert plan['canon'] is False
    # An older existing todo editor does not send the new optional field.
    row=w.save_entry(p,Entry(etag=row['etag'],id=plan['id'],kind='todo',text='Renamed by old todo editor'))
    reopened=plan_overview(w,p);assert reopened['todos'][0]['schedule']==plan['schedule'] and reopened['automatic_execution'] is False
    row=w.update_entry_states(p,EntryStates(etag=row['etag'],kind='todo',updates=[{'id':plan['id'],'status':'DONE'}]))
    assert row['todos'][0]['status']=='DONE' and row['todos'][0]['schedule']['progress']==25
    assert protected(root)==before

def test_explicit_clear_and_conflict_never_overwrite_schedule(service):
    s,p,_=service;w=s.workbench;before=w.entries(p)
    saved=w.save_entry(p,Entry(etag=before['etag'],kind='revision',text='Review',schedule={'due_date':'2027-01-01'}));item=saved['revision_tasks'][0]
    with pytest.raises(ConsoleError):w.save_entry(p,Entry(etag=before['etag'],id=item['id'],kind='revision',text='Stale edit',schedule=None))
    assert w.entries(p)==saved
    cleared=w.save_entry(p,Entry(etag=saved['etag'],id=item['id'],kind='revision',text='Review',schedule=None))
    assert cleared['revision_tasks'][0]['schedule'] is None

@pytest.mark.parametrize('value',[{'due_date':'2026-02-30'},{'due_date':'20261026'},{'start_date':'2026-10-28','due_date':'2026-10-26'},{'progress':101},{'progress':1.5},{'progress':True},{'steps':[{'text':'x','shell':'run'}]},{'automatic':True}])
def test_schedule_rejects_invalid_dates_progress_and_executable_fields(value):
    with pytest.raises(ValidationError):Schedule.model_validate(value)

def test_empty_plans_and_impact_are_read_only_and_project_scoped(service):
    s,p,root=service;w=s.workbench;before=protected(root)
    data=plan_overview(w,p);assert data['planning_only'] and not data['todos']
    actor=w.tools.characters.list(p)[0]['canonical']
    impact=impact_preview(w,p,'character',actor['id']);assert impact['entity']['id']==actor['id'] and impact['causal_prediction'] is False and not impact['writer_context']
    with pytest.raises(ConsoleError):impact_preview(w,p,'character','foreign_character')
    with pytest.raises(ConsoleError):plan_overview(w,'novel_foreign')
    assert protected(root)==before


def test_plans_survive_actual_backup_restore(service,tmp_path):
    from pathlib import Path
    s,p,root=service;w=s.workbench;center=w.data
    center.configure({'directory':str(tmp_path/'backups'),'schedule':'OFF','on_exit':False})
    saved=w.save_entry(p,Entry(etag=w.entries(p)['etag'],kind='todo',text='Dated backup fixture',schedule={'start_date':'2026-12-31','due_date':'2027-01-02','progress':40,'steps':[{'text':'Review','done':True}]}))
    backup=center.backup(p,private_history=False);staged=center.stage(Path(backup['path']).read_bytes());restored=center.restore(staged['token'],expected_hash=staged['sha256'])
    other=restored['project_id'];rows=plan_overview(w,other)['todos']
    assert other!=p and rows[0]['schedule']==saved['todos'][0]['schedule'] and rows[0]['project']==other
    assert plan_overview(w,p)['todos'][0]['schedule']==saved['todos'][0]['schedule']
