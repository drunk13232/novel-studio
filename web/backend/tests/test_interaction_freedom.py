"""Real local notebook/persistence services, isolated author data, no model calls."""
import json
import hashlib
import pytest
from pydantic import ValidationError
from test_writing_assist import service
from app.author_workbench import Entry,EntryStates
from app.errors import ConsoleError
from app.studio import Preferences,scoped_preferences
from app.library.storage import write


def create(workbench,project,text='Isolated idea',kind='inspiration'):
    return workbench.save_entry(project,Entry(etag=workbench.entries(project)['etag'],kind=kind,text=text))


def test_batch_restore_undo_and_story_files_unchanged(service):
    s,p,root=service;w=s.workbench
    protected={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for area in ['chapters','characters','settings','state'] for f in (root/area).rglob('*') if f.is_file()}
    create(w,p,'First');before=create(w,p,'Second');ids=[x['id'] for x in before['notes']]
    saved=w.update_entry_states(p,EntryStates(etag=before['etag'],kind='inspiration',updates=[{'id':id,'status':'ARCHIVED','trashed':True} for id in ids]))
    assert all(row['status']=='ARCHIVED' and row['trashed'] for row in saved['notes'])
    # Same declared state API is the undo; no text or arbitrary fields accepted.
    restored=w.update_entry_states(p,EntryStates(etag=saved['etag'],kind='inspiration',updates=[{'id':id,'status':'OPEN','trashed':False} for id in ids]))
    assert all(row['status']=='OPEN' and not row['trashed'] for row in restored['notes'])
    assert w.entries(p)==restored
    assert protected=={name:hashlib.sha256(open(name,'rb').read()).hexdigest() for name in protected}


def test_batch_is_atomic_on_missing_or_duplicate_ids(service):
    s,p,root=service;w=s.workbench;before=create(w,p);id=before['notes'][0]['id'];path=w.shelf.path(p);original=path.read_bytes()
    for ids in [[id,'not-from-this-project'],[id,id]]:
        with pytest.raises(ConsoleError):w.update_entry_states(p,EntryStates(etag=before['etag'],kind='inspiration',updates=[{'id':x,'trashed':True} for x in ids]))
        assert path.read_bytes()==original
    with pytest.raises(ConsoleError):w.update_entry_states(p,EntryStates(etag=before['etag'],kind='todo',updates=[{'id':id,'status':'DONE'}]))
    assert path.read_bytes()==original


def test_stale_undo_cannot_erase_later_edit(service):
    s,p,_=service;w=s.workbench;before=create(w,p);id=before['notes'][0]['id']
    changed=w.update_entry_states(p,EntryStates(etag=before['etag'],kind='inspiration',updates=[{'id':id,'status':'DONE'}]))
    edited=w.save_entry(p,Entry(etag=changed['etag'],id=id,kind='inspiration',text='Author edited after organizing',status='DONE'))
    with pytest.raises(ConsoleError):w.update_entry_states(p,EntryStates(etag=changed['etag'],kind='inspiration',updates=[{'id':id,'status':'OPEN'}]))
    assert w.entries(p)==edited


def test_edit_preserves_unknown_provenance_and_does_not_restore_trash(service):
    s,p,_=service;w=s.workbench;row=create(w,p);id=row['notes'][0]['id'];row['notes'][0].update(custom_provenance={'source':'test-author'},trashed=True)
    created=row['notes'][0]['at'];row.pop('etag');write(w.shelf.path(p),row)
    edited=w.save_entry(p,Entry(etag=w.entries(p)['etag'],id=id,kind='inspiration',text='Edited safely'))['notes'][0]
    assert edited['custom_provenance']=={'source':'test-author'} and edited['at']==created and edited['trashed']


@pytest.mark.parametrize('update',[{'id':'x','sql':'DELETE'},{'id':'x','text':'arbitrary'},{'id':'x','status':'FINAL'},{'id':'x','status':'DONE','path':'../../secret'}])
def test_batch_allows_only_bounded_notebook_state(update):
    with pytest.raises(ValidationError):EntryStates(etag='0'*64,kind='todo',updates=[update])


def test_workspace_layouts_roundtrip_and_project_scope():
    view={'nav_open':False,'ai_open':False,'focus_mode':False,'nav_width':260,'ai_width':340,'reference_width':420,'referenceOpen':True,'layout':{'manuscript':62,'reference':38}}
    value=Preferences(workspaces={'novel_A':{'tabs':[],'view':view,'personal_layout':view,'appearance':'rem-night'},'novel_B':{'tabs':[]}}).model_dump()
    assert Preferences.model_validate(json.loads(json.dumps(value))).workspaces['novel_A']['view']==view
    assert list(scoped_preferences(value,'novel_A')['workspaces'])==['novel_A']
    assert value['workspaces']['novel_A']['appearance']=='rem-night'
    for bad in [{'layout':{'manuscript':50,'reference':200}},{'nav_width':20000},{'shell':'arbitrary'}]:
        with pytest.raises(ValidationError):Preferences(workspaces={'novel_A':{'view':{**view,**bad}}})
