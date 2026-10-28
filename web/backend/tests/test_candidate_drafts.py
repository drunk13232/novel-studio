"""Real local candidate persistence and safety; no remote model calls."""
import copy,hashlib,json
from pathlib import Path
import pytest
from pydantic import ValidationError
from test_creative_maps_audio import local
from app.studio_tools import CandidateDraft,Decision,normalized,utf16_index
from app.author_workbench import Entry
from app.errors import ConsoleError
from app.library.storage import write

def stage(local,variants=False):
    client,app,p=local;t=app.state.studio_tools;path='chapters/story/draft.txt';d=t.doc(p,path);text=normalized(d);quote=text[:30]
    row=t.stage_replacement(p,path,d['etag'],0,utf16_index(quote,len(quote)),quote,quote+' proposed',{'kind':'ISOLATED_TEST'})
    if variants:
        row['variants']=[{'candidate':'first','label':'A'},{'candidate':'second','label':'B'}];write(t.candidate_path(p,row['id']),row)
    return t,p,row,d

def save(t,p,row,text='author draft',variant=0,**extra):
    view=t.draft_view(p,row['id'],variant)
    return t.save_draft(p,row['id'],CandidateDraft(etag=view['etag'],variant=variant,text=text,**extra))

def test_persist_restart_and_source_untouched(local):
    t,p,row,d=stage(local);root=t.root(p);before={f.relative_to(root).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for name in ['chapters','characters','state','bible','settings'] for f in (root/name).rglob('*') if f.is_file()}
    saved=save(t,p,row,text='Edited candidate with Chinese 中文',note='continue tomorrow',chosen_hunks=[0,2]);assert saved['draft']['text'].endswith('中文')
    fresh=type(t)(t.registry,t.planning,t.characters,t.bible,t.manager,t.config)
    assert fresh.draft_view(p,row['id'])['draft']==saved['draft']
    assert fresh.candidate(p,row['id'])['candidate']==row['candidate'] and fresh.candidate(p,row['id'])['status']=='PROPOSED'
    assert {n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in before}==before

def test_independent_variants(local):
    t,p,row,d=stage(local,True);save(t,p,row,'author A',0);save(t,p,row,'author B',1)
    assert t.draft_view(p,row['id'],0)['draft']['text']=='author A'
    assert t.draft_view(p,row['id'],1)['draft']['text']=='author B'
    assert t.draft_view(p,row['id'])['active_variant']==1
    with pytest.raises(ConsoleError):save(t,p,row,'invalid',2)

def test_concurrent_save_conflicts_without_overwrite(local):
    t,p,row,d=stage(local);etag=t.draft_view(p,row['id'])['etag'];save(t,p,row,'first window')
    with pytest.raises(ConsoleError):t.save_draft(p,row['id'],CandidateDraft(etag=etag,text='stale window'))
    assert t.draft_view(p,row['id'])['draft']['text']=='first window'

def test_stale_source_draft_is_preserved_but_not_adopted(local):
    t,p,row,d=stage(local);ws=t.registry.workspace(p);ws.save(d['path'],d['content']+'\nnew source',d['etag']);before=ws.content(d['path'])['content'];saved=save(t,p,row,'rescue old edits')
    assert saved['source_current'] is False and saved['draft']['text']=='rescue old edits'
    with pytest.raises(ConsoleError):t.decide(p,row['id'],Decision(action='accept',originalHash=row['originalHash'],candidate='wrong',candidate_etag=saved['etag']))
    assert ws.content(d['path'])['content']==before

def test_candidate_etag_blocks_late_adoption(local):
    t,p,row,d=stage(local);old=t.draft_view(p,row['id'])['etag'];save(t,p,row,'other edit')
    with pytest.raises(ConsoleError):t.decide(p,row['id'],Decision(action='accept',originalHash=row['originalHash'],candidate='late',candidate_etag=old))
    assert t.doc(p,d['path'])['etag']==d['etag']

def test_explicit_accept_once_uses_existing_guard(local):
    t,p,row,d=stage(local);saved=save(t,p,row,'explicit author choice');result=t.decide(p,row['id'],Decision(action='accept',originalHash=row['originalHash'],candidate=saved['draft']['text'],candidate_etag=saved['etag']))
    assert result['status']=='ACCEPTED' and 'explicit author choice' in result['file']['content']
    with pytest.raises(ConsoleError):save(t,p,row,'late edit')
    with pytest.raises(ConsoleError):t.decide(p,row['id'],Decision(action='accept',originalHash=row['originalHash'],candidate='repeat'))

def test_reject_never_writes_source(local):
    t,p,row,d=stage(local);save(t,p,row,'kept draft');t.decide(p,row['id'],Decision(action='reject',originalHash=row['originalHash']))
    assert t.doc(p,d['path'])['etag']==d['etag']
    with pytest.raises(ConsoleError):save(t,p,row,'late rejected edit')

def test_bad_schema_scope_and_owner(local):
    t,p,row,d=stage(local)
    for kwargs in [dict(text='x'*32001),dict(text='ok',chosen_hunks=[True]),dict(text='ok',variant=3)]:
        with pytest.raises(ValidationError):CandidateDraft(etag='a'*64,**kwargs)
    with pytest.raises(ConsoleError):t.draft_view(p,'../escape')
    with pytest.raises(ConsoleError):t.draft_view('missing_project',row['id'])
    altered=copy.deepcopy(row);altered['project_id']='another_project';write(t.candidate_path(p,row['id']),altered)
    with pytest.raises(ConsoleError):t.draft_view(p,row['id'])
    with pytest.raises(ConsoleError):t.save_draft(p,row['id'],CandidateDraft(etag='a'*64,text='no'))

def test_chapter_summary_is_scoped_and_reads_existing_entries(local):
    client,app,p=local;t,p,row,d=stage(local);work=app.state.writing_assist.workbench
    a=work.entries(p);work.save_entry(p,Entry(etag=a['etag'],kind='todo',text='This chapter task',path=d['path']))
    other=t.root(p)/'chapters/chapter-1/draft.md';other.parent.mkdir(parents=True,exist_ok=True);other.write_text('Isolated other chapter',encoding='utf-8')
    a=work.entries(p);work.save_entry(p,Entry(etag=a['etag'],kind='revision',text='Another chapter',path='chapters/chapter-1/draft.md'))
    view=work.chapter_work(p,d['path']);assert view['counts']=={'todos':1,'revisions':0};assert [c['id'] for c in view['candidates']]==[row['id']];assert view['plan']['planning_only'] is True
    assert 'author draft' not in json.dumps(view)
    with pytest.raises(ConsoleError):work.chapter_work(p,'../../outside.md')

def test_draft_backup_restore_new_project(local):
    client,app,p=local;t,p,row,d=stage(local,True);saved=save(t,p,row,'restore this draft',1,note='private note',chosen_hunks=[0]);data=app.state.data_center
    backup=data.backup(p,images=True,note='ISOLATED_CANDIDATE_BACKUP');staged=data.stage(Path(backup['path']).read_bytes());other=data.restore(staged['token'],expected_hash=staged['sha256'])['project_id']
    assert other!=p
    restored=t.draft_view(other,row['id'],1);assert restored['draft']==saved['draft'] and restored['project_id']==other
    assert t.candidate(p,row['id'])['project_id']==p


def test_changed_candidate_also_blocks_late_rejection(local):
    t,p,row,d=stage(local);old=t.draft_view(p,row['id'])['etag'];save(t,p,row,'other window retained edit')
    with pytest.raises(ConsoleError):t.decide(p,row['id'],Decision(action='reject',originalHash=row['originalHash'],candidate_etag=old))
    assert t.candidate(p,row['id'])['status']=='PROPOSED' and t.doc(p,d['path'])['etag']==d['etag']
