"""Real local revision/save/catalog/search/backup checks; synthetic projects only."""
import copy
import json
import shutil
import threading
import uuid
from types import SimpleNamespace
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.chapter_versions import ChapterVersions,VersionSave,VersionArchive,VersionSwitch,VersionUndo,VersionRecovery,chapter_version_routes
from app.errors import ConsoleError
from app.projects.service import ProjectRegistry
from app.studio_tools import StudioTools
from app.book_center import BookCenter,ExportRequest
from app.library.data import DataCenter
from app.library.storage import write_bytes,write,safe,digest,rebuild,search
import app.chapter_versions as versions_module
import app.writing_metrics as metrics_module

@pytest.fixture
def setup(tmp_path):
    engine=tmp_path/'engine';engine.mkdir();root=engine/'projects';root.mkdir()
    project='novel_'+uuid.uuid4().hex;folder=root/project;folder.mkdir()
    manifest={'id':project,'title':'Synthetic only','status':{'phase':'WRITING','updated_at':'2026-10-25'},'genre':{'primary':'fiction'},'target':{},'current':{},'creative_direction':{},'workflow':{},'codex':{}}
    write_bytes(folder/'project.yaml',__import__('yaml').safe_dump(manifest).encode())
    write_bytes(safe(folder,'state/chapter-ledger.yaml'),b'entries: []\n')
    path='chapters/chapter-1/draft.txt';write_bytes(safe(folder,path),'第1章 测试\n\n主线原文。'.encode())
    registry=ProjectRegistry(engine);ws=registry.workspace(project)
    cards=[{'id':'chapter_'+uuid.uuid4().hex,'number':1,'title':'Synthetic chapter','volume':'v1','status':'DRAFT','order':0}]
    planning=SimpleNamespace(rows=lambda p,kind:cards if kind=='chapter' else [{'id':'v1','number':1,'title':'Volume'}])
    def writable(p):
        if registry.get(p)['status']['phase']=='ARCHIVED':raise ConsoleError('Archived',409)
        return registry.workspace(p)
    chars=SimpleNamespace(writable=writable,list=lambda p:[])
    tools=StudioTools(registry,planning,chars,SimpleNamespace(list=lambda p:[]),None,None)
    books=BookCenter(registry,planning,SimpleNamespace(list=lambda p:[]),engine/'config');registry.book_center=books
    service=ChapterVersions(tools)
    return SimpleNamespace(s=service,p=project,ws=ws,path=path,root=folder,engine=engine,registry=registry,tools=tools,books=books,tmp=tmp_path,cards=cards)

def create(x,name='If route',content='支线独有文本，主角作出另一个选择。',**extra):
    row=x.s.list(x.p,x.path)
    return x.s.save(x.p,VersionSave(path=x.path,state_etag=row['state_etag'],request_id=uuid.uuid4().hex,name=name,content=content,**extra))
def request(x,detail,mode='switch',**extra):
    state=x.s.list(x.p,x.path)
    return VersionSwitch(path=x.path,state_etag=state['state_etag'],main_etag=state['main_etag'],version_id=detail['version']['id'],version_etag=detail['version']['etag'],request_id=uuid.uuid4().hex,confirm=True,mode=mode,**extra)
def undo(x,receipt):
    state=x.s.list(x.p,x.path)
    return x.s.undo(x.p,receipt['id'],VersionUndo(path=x.path,state_etag=state['state_etag'],request_id=uuid.uuid4().hex,confirm=True))
def snapshot(x):return {str(p.relative_to(x.root)):digest(p.read_bytes()) for p in x.root.rglob('*') if p.is_file() and p.relative_to(x.root).parts[0] in {'state','bible','characters','settings'}}

def test_read_empty_is_side_effect_free_and_legacy_path_stable(setup):
    x=setup;before=set(x.root.rglob('*'));row=x.s.list(x.p,x.path)
    assert len(row['versions'])==1 and row['versions'][0]['canonical'] and row['main_path']==x.path
    assert before==set(x.root.rglob('*')) and not (x.root/'history/parallel-versions').exists()

def test_branch_create_update_archive_restore_and_idempotency(setup):
    x=setup;v=create(x);id=v['version']['id'];original=x.ws.content(x.path)['content']
    assert not v['version']['canonical'] and x.ws.content(x.path)['content']==original
    b=VersionSave(path=x.path,state_etag=v['state']['state_etag'],request_id=uuid.uuid4().hex,name='Renamed',description='Alternative',content='新的支线',version_etag=v['version']['etag'])
    changed=x.s.save(x.p,b,id);assert x.s.save(x.p,b,id)==changed
    row=x.s.archive(x.p,x.path,id,VersionArchive(path=x.path,state_etag=changed['state']['state_etag'],confirm=True));assert next(v for v in row['versions'] if v['id']==id)['archived']
    row=x.s.archive(x.p,x.path,id,VersionArchive(path=x.path,state_etag=row['state_etag'],confirm=True,archived=False));assert not next(v for v in row['versions'] if v['id']==id)['archived']
    assert x.s.download(x.p,x.path,id).decode('utf-8-sig')=='新的支线'

def test_create_stable_request_does_not_duplicate(setup):
    x=setup;state=x.s.list(x.p,x.path);b=VersionSave(path=x.path,state_etag=state['state_etag'],request_id=uuid.uuid4().hex,name='A',content='一')
    one=x.s.save(x.p,b);two=x.s.save(x.p,b);assert one['version']['id']==two['version']['id'] and len(two['state']['versions'])==2
    with pytest.raises(ConsoleError):x.s.save(x.p,b.model_copy(update={'content':'Different'}))

def test_switch_and_whole_undo_preserve_bytes_and_can_reopen(setup):
    x=setup;original=x.ws.resolve(x.path).read_bytes();protected=snapshot(x);a=create(x);r=x.s.switch(x.p,request(x,a))
    assert r['canonical_changed'] and x.ws.content(x.path)['content']==a['version']['content']
    state=x.s.list(x.p,x.path);assert sum(v['canonical'] for v in state['versions'])==1 and state['canonical_id']==a['version']['id']
    previous=x.s.detail(x.p,x.path,state['versions'][0]['id']);assert previous['version']['content']==original.decode()
    reopened=ChapterVersions(x.tools);assert reopened.list(x.p,x.path)['canonical_id']==a['version']['id']
    undone=undo(x,r);assert undone['status']=='UNDONE' and x.ws.resolve(x.path).read_bytes()==original and snapshot(x)==protected

def test_switch_request_retry_is_idempotent_and_key_reuse_refused(setup):
    x=setup;a=create(x);b=request(x,a);one=x.s.switch(x.p,b);two=x.s.switch(x.p,b)
    assert one['id']==two['id'] and two['replayed'] and len(x.s.operations(x.p,x.path)['operations'])==1
    with pytest.raises(ConsoleError):x.s.switch(x.p,b.model_copy(update={'mode':'revision'}))

def test_main_content_cannot_be_changed_through_branch_edit(setup):
    x=setup;row=x.s.list(x.p,x.path);main=x.s.detail(x.p,x.path,row['canonical_id'])
    with pytest.raises(ConsoleError) as e:x.s.save(x.p,VersionSave(path=x.path,state_etag=row['state_etag'],request_id=uuid.uuid4().hex,name='Main',content='overwrite',version_etag=main['version']['etag']),row['canonical_id'])
    assert e.value.code=='VERSIONS_EDIT_MAIN_IN_EDITOR'

def test_stale_main_and_branch_and_metadata_rejected_before_switch(setup):
    x=setup;a=create(x);b=request(x,a);x.ws.save(x.path,'外部保存',b.main_etag)
    with pytest.raises(ConsoleError):x.s.switch(x.p,b)
    b=request(x,a);create(x,name='B')
    with pytest.raises(ConsoleError):x.s.switch(x.p,b)

def test_confirmation_mandatory_and_archiving_canonical_prohibited(setup):
    x=setup;a=create(x)
    with pytest.raises(ConsoleError):x.s.switch(x.p,request(x,a).model_copy(update={'confirm':False}))
    state=x.s.list(x.p,x.path)
    with pytest.raises(ConsoleError):x.s.archive(x.p,x.path,state['canonical_id'],VersionArchive(path=x.path,state_etag=state['state_etag'],confirm=True))

def test_undo_refuses_external_main_or_metadata_change(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));x.ws.save(x.path,'后续正文',x.ws.content(x.path)['etag'])
    with pytest.raises(ConsoleError):undo(x,r)
    assert x.ws.content(x.path)['content']=='后续正文'

def test_undo_refuses_to_drop_later_created_branch(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));later=create(x,name='Later')
    with pytest.raises(ConsoleError):undo(x,r)
    assert any(v['id']==later['version']['id'] for v in x.s.list(x.p,x.path)['versions'])

def test_final_and_committed_are_not_overwritten_and_revision_outcome_honest(setup):
    x=setup;final='chapters/chapter-1/final.txt';write_bytes(x.ws.resolve(final),'第1章\n\n正式不可变。'.encode());x.path=final
    original=x.ws.resolve(final).read_bytes();protected=snapshot(x);a=create(x)
    with pytest.raises(ConsoleError) as e:x.s.switch(x.p,request(x,a))
    assert e.value.code=='VERSIONS_PROTECTED'
    before=x.s.list(x.p,x.path)['canonical_id'];r=x.s.switch(x.p,request(x,a,mode='revision'))
    assert r['status']=='REVIEW_CANDIDATE' and not r['canonical_changed'] and r['requires_review'] and not r['paths']
    assert x.ws.resolve(final).read_bytes()==original and x.s.list(x.p,x.path)['canonical_id']==before
    assert x.ws.content(r['path'])['content']==original.decode() and snapshot(x)==protected
    assert not list((x.root/'chapters/chapter-1').glob('manual-*'))
    frozen=x.s.comparison(x.p,x.path,r['id']);assert frozen['modified']==a['version']['content'] and frozen['original']==original.decode()
    assert not x.tools.search(x.p,'支线独有文本')
    assert x.books.assemble(x.p,ExportRequest())[1][0]['text']=='正式不可变。'
    u=undo(x,r);assert u['path']==final and x.ws.resolve(final).read_bytes()==original and u['paths']==[]


def test_committed_draft_protection(setup):
    x=setup;write_bytes(safe(x.root,'state/chapter-ledger.yaml'),b'entries:\n- chapter: 1\n');a=create(x)
    with pytest.raises(ConsoleError) as e:x.s.switch(x.p,request(x,a))
    assert e.value.code=='VERSIONS_PROTECTED'


def test_crlf_bom_preserved_and_no_extra_manuscript_paths(setup):
    x=setup;write_bytes(x.ws.resolve(x.path),'第1章\r\n\r\n原文\r\n'.encode('utf-8-sig'));a=create(x,content='第1章\n\n变体\n');original=x.ws.resolve(x.path).read_bytes();r=x.s.switch(x.p,request(x,a))
    assert x.ws.content(x.path)['bom'] and x.ws.content(x.path)['line_ending']=='CRLF'
    assert len(list((x.root/'chapters').rglob('*.txt')))==1
    undo(x,r);assert x.ws.resolve(x.path).read_bytes()==original


def test_alternatives_absent_from_catalog_search_context_paths_and_export(setup):
    x=setup;original=x.books.assemble(x.p,ExportRequest(drafts=True))[1][0]['text'];a=create(x,content='ONLY_ALTERNATIVE_SECRET_7 绝不应作为主线')
    assert x.books.assemble(x.p,ExportRequest(drafts=True))[1][0]['text']==original
    assert not x.tools.search(x.p,'ONLY_ALTERNATIVE_SECRET_7')
    rebuild(x.root);assert not search(x.root,'ONLY_ALTERNATIVE_SECRET_7')
    assert not any('parallel-versions' in r['path'] for r in x.ws.list_files())
    assert len(x.books.catalog(x.p,include_auxiliary=False)['chapters'])==1
    x.s.switch(x.p,request(x,a));assert 'ONLY_ALTERNATIVE_SECRET_7' in x.books.assemble(x.p,ExportRequest(drafts=True))[1][0]['text']


def test_real_metrics_exclude_version_switch_but_stock_tracks_current(setup,monkeypatch):
    x=setup;metrics=metrics_module.Metrics(x.books);monkeypatch.setattr(metrics_module,'observer',metrics.saved)
    x.ws.save(x.path,'第1章\n\n写下新的正文',x.ws.content(x.path)['etag']);before=copy.deepcopy(metrics.state(x.p)['events']);a=create(x,content='第1章\n\n'+('支线很长。'*100));r=x.s.switch(x.p,request(x,a))
    assert metrics.state(x.p)['events']==before
    assert metrics.summary(x.p)['total_han']==x.books.catalog(x.p,include_auxiliary=False)['chapters'][0]['han']
    undo(x,r);assert metrics.state(x.p)['events']==before


def test_metadata_write_failure_compensates_main_safely(setup,monkeypatch):
    x=setup;a=create(x);before=x.ws.resolve(x.path).read_bytes();original=versions_module.write_bytes;statefile=x.s._load(x.p,x.path)[2];failed=False
    def fail_once(path,data):
        nonlocal failed
        if path==statefile and not failed:failed=True;raise OSError('isolated state publication failure')
        return original(path,data)
    monkeypatch.setattr(versions_module,'write_bytes',fail_once)
    with pytest.raises(OSError):x.s.switch(x.p,request(x,a))
    assert x.ws.resolve(x.path).read_bytes()==before and x.s.operations(x.p,x.path)['operations'][0]['status']=='ROLLED_BACK'


def test_compensation_never_overwrites_external_late_write(setup,monkeypatch):
    x=setup;a=create(x);original=versions_module.write_bytes;statefile=x.s._load(x.p,x.path)[2];failed=False
    def fail_once(path,data):
        nonlocal failed
        if path==statefile and not failed:
            failed=True;x.ws.resolve(x.path).write_bytes('外部后到数据'.encode());raise OSError('isolated state failure')
        return original(path,data)
    monkeypatch.setattr(versions_module,'write_bytes',fail_once)
    with pytest.raises(ConsoleError) as e:x.s.switch(x.p,request(x,a))
    assert e.value.code=='VERSIONS_RECOVERY_REQUIRED' and x.ws.content(x.path)['content']=='外部后到数据'


def test_size_invalid_text_scope_archive_and_json_api(setup):
    x=setup;before=x.ws.content(x.path)['content']
    for text in ['a\rb','a\x00b','文'*(x.ws.max_bytes//3+1)]:
        with pytest.raises(ConsoleError):create(x,content=text)
    with pytest.raises(ConsoleError):x.s.list(x.p,'state/chapter-ledger.yaml')
    with pytest.raises(ConsoleError):x.s.list(x.p,'../outside.txt')
    app=FastAPI();app.include_router(chapter_version_routes(x.s));client=TestClient(app)
    assert client.get('/api/projects/'+x.p+'/chapter-versions',params={'path':x.path}).status_code==200
    assert x.ws.content(x.path)['content']==before


def test_backup_restore_new_project_keeps_versions_without_private_ids(setup):
    x=setup;a=create(x);dc=DataCenter(x.registry,x.engine/'config/backup.json');write(dc.settings_path,{'directory':str(x.tmp/'backups'),'schedule':'OFF','on_exit':False})
    backup=dc.backup(x.p,images=False,private_history=False);blob=Path(backup['path']).read_bytes();staged=dc.stage(blob)
    restored=dc.restore(staged['token'],expected_hash=staged['sha256']);new=restored['project_id']
    assert new!=x.p and x.s.detail(new,x.path,a['version']['id'])['version']['content']==a['version']['content']
    assert x.s.list(new,x.path)['project_id']==new and x.ws.content(x.path)['content'].endswith('主线原文。')


def test_review_candidate_log_failure_never_changes_manuscript(setup,monkeypatch):
    x=setup;final='chapters/chapter-1/final.txt';write_bytes(x.ws.resolve(final),'正式。'.encode());x.path=final;a=create(x);before=x.ws.resolve(final).read_bytes();original=versions_module.write
    def fail_record(path,value):
        if '/operations/' in path.as_posix():raise OSError('isolated candidate record failure')
        return original(path,value)
    monkeypatch.setattr(versions_module,'write',fail_record)
    with pytest.raises(OSError):x.s.switch(x.p,request(x,a,mode='revision'))
    assert x.ws.resolve(final).read_bytes()==before and not list(x.ws.resolve(final).parent.glob('manual-if-*'))


def test_review_candidate_creates_no_new_chapter_paths(setup):
    x=setup;a=create(x);b=request(x,a,mode='revision');before={str(f.relative_to(x.root)):f.read_bytes() for f in (x.root/'chapters').rglob('*') if f.is_file()}
    receipt=x.s.switch(x.p,b)
    assert receipt['status']=='REVIEW_CANDIDATE' and {str(f.relative_to(x.root)):f.read_bytes() for f in (x.root/'chapters').rglob('*') if f.is_file()}==before
    assert x.s.list(x.p,x.path)['canonical_id']!=a['version']['id']


def test_undo_failure_compensates_completed_state_without_losing_switch(setup,monkeypatch):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));before=x.ws.resolve(x.path).read_bytes();original=versions_module.write_bytes;statefile=x.s._load(x.p,x.path)[2];failed=False
    def fail_once(path,data):
        nonlocal failed
        if path==statefile and not failed:failed=True;raise OSError('isolated undo state failure')
        return original(path,data)
    monkeypatch.setattr(versions_module,'write_bytes',fail_once)
    with pytest.raises(OSError):undo(x,r)
    assert x.ws.resolve(x.path).read_bytes()==before and x.s.list(x.p,x.path)['canonical_id']==a['version']['id']
    assert x.s.operations(x.p,x.path)['operations'][0]['status']=='APPLIED'


def test_archived_project_remains_read_only_and_cross_project_id_is_not_visible(setup):
    x=setup;a=create(x);assert not x.s.list(x.p,x.path)['versions'][0]['archived']
    with pytest.raises(ConsoleError):x.s.list('novel_'+uuid.uuid4().hex,x.path)
    manifest=x.registry.get(x.p);manifest['status']['phase']='ARCHIVED';write_bytes(x.root/'project.yaml',__import__('yaml').safe_dump(manifest).encode())
    with pytest.raises(ConsoleError):create(x)
    with pytest.raises(ConsoleError):x.s.switch(x.p,request(x,a))


def test_full_app_authenticated_http_mutations_use_single_existing_lease(setup):
    # Child interpreter isolates app.main's module-level app before import. No real
    # user-data configuration, GUI, lifespan workers or network model calls.
    import subprocess,os
    x=setup;source=Path(__file__).resolve().parents[3]
    for folder in ('engine','templates'):
        shutil.copytree(source/folder,x.engine/folder,dirs_exist_ok=True)
    code=r'''
import json,uuid
from app.main import create_app
from app.config import Settings
from app.chapter_versions import ChapterVersions,chapter_version_routes
from fastapi.testclient import TestClient
app=create_app(Settings());app.state.testing=True
if not any('/chapter-versions' in getattr(route,'path','') for route in app.routes):app.include_router(chapter_version_routes(ChapterVersions(app.state.studio_tools)))
p=next(iter(app.state.registry.rows));path='chapters/chapter-1/draft.txt';url='/api/projects/'+p+'/chapter-versions';c=TestClient(app)
state=c.get(url,params={'path':path}).json();original=app.state.registry.workspace(p).content(path)['content']
body={'path':path,'state_etag':state['state_etag'],'request_id':uuid.uuid4().hex,'name':'HTTP alternative','content':'HTTP_ALT_ONLY 合成支线'}
assert c.post(url+'/versions',json=body).status_code==403
c.headers['X-Novel-Request']=c.get('/api/session').json()['request_token']
created=c.post(url+'/versions',json=body);assert created.status_code==201,created.text
value=created.json();state=value['state'];request={'path':path,'state_etag':state['state_etag'],'main_etag':state['main_etag'],'version_id':value['version']['id'],'version_etag':value['version']['etag'],'request_id':uuid.uuid4().hex,'confirm':False}
assert c.post(url+'/switch',json=request).status_code==422
request['confirm']=True;switched=c.post(url+'/switch',json=request);assert switched.status_code==200,switched.text
assert c.post(url+'/switch',json=request).json()['replayed'] is True
state=c.get(url,params={'path':path}).json();receipt=switched.json();restored=c.post(url+'/operations/'+receipt['id']+'/undo',json={'path':path,'state_etag':state['state_etag'],'request_id':uuid.uuid4().hex,'confirm':True});assert restored.status_code==200,restored.text
assert app.state.registry.workspace(p).content(path)['content']==original
from app.chapter_versions import VersionSwitch
service=app.state.chapter_versions;workspace=app.state.registry.workspace(p);real_save=workspace.save
state=c.get(url,params={'path':path}).json();request.update(state_etag=state['state_etag'],main_etag=state['main_etag'],request_id=uuid.uuid4().hex)
def interrupted(path,content,etag):
    real_save(path,content,etag);raise KeyboardInterrupt('isolated crash')
workspace.save=interrupted
try:service.switch(p,VersionSwitch.model_validate(request))
except KeyboardInterrupt:pass
finally:workspace.save=real_save
preview=c.get(url+'/recovery',params={'path':path});assert preview.status_code==200,preview.text
plan=preview.json();assert plan['required'] and plan['can_recover']
body={key:plan[key] for key in ('state_etag','main_etag','operation_id','recovery_etag')};body.update(path=path,request_id=uuid.uuid4().hex,confirm=False)
assert c.post(url+'/recovery',json=body).status_code==422
body['confirm']=True;restored=c.post(url+'/recovery',json=body);assert restored.status_code==200,restored.text
assert restored.json()['status']=='RECOVERED' and c.post(url+'/recovery',json=body).json()['replayed']
assert workspace.content(path)['content']==original
print('LOCAL HTTP PASS session guard, create, fixed confirmation, switch, idempotent retry, undo; one existing mutation lease; explicit interrupted-transaction recovery.')
'''
    env={**os.environ,'NOVEL_WORKSPACE':str(x.engine),'PYTHONPATH':str(source/'web/backend'),'NOVEL_STUDIO_DATA':str(x.tmp/'app-data'),'NOVEL_STUDIO_USER_DATA':str(x.tmp/'app-user-data')}
    result=subprocess.run([__import__('sys').executable,'-c',code],cwd=source,env=env,capture_output=True,text=True,timeout=70)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'LOCAL HTTP PASS' in result.stdout


def test_undo_rejects_tampered_cross_chapter_target(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));second='chapters/chapter-2/draft.txt';write_bytes(x.ws.resolve(second),x.ws.resolve(x.path).read_bytes())
    ws,folder,*_=x.s._load(x.p,x.path);opfile=x.s._op_path(ws,folder,r['id']);op=__import__('json').loads(opfile.read_text());op['target']=second;write(opfile,op)
    before=x.ws.resolve(second).read_bytes()
    with pytest.raises(ConsoleError) as e:undo(x,r)
    assert e.value.code=='VERSIONS_CORRUPT' and x.ws.resolve(second).read_bytes()==before


def test_external_metadata_change_during_branch_checkpoint_not_overwritten(setup,monkeypatch):
    x=setup;a=create(x);statefile=x.s._load(x.p,x.path)[2];before=statefile.read_bytes();original=versions_module.checkpoint;external=__import__('json').loads(before);external['versions'][0]['description']='External author note'
    def raced_checkpoint(root,path,*args,**kwargs):
        result=original(root,path,*args,**kwargs)
        if path==statefile.relative_to(x.root).as_posix():write(statefile,external)
        return result
    monkeypatch.setattr(versions_module,'checkpoint',raced_checkpoint)
    with pytest.raises(ConsoleError) as e:create(x,name='Must not replace external metadata')
    assert e.value.code=='VERSIONS_CHANGED' and __import__('json').loads(statefile.read_text())==external


def test_only_confirmed_protected_revision_can_be_withdrawn_and_undo_is_idempotent(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a,mode='revision'));state=x.s.list(x.p,x.path);b=VersionUndo(path=x.path,state_etag=state['state_etag'],request_id=uuid.uuid4().hex,confirm=True)
    one=x.s.undo(x.p,r['id'],b);two=x.s.undo(x.p,r['id'],b)
    assert one['id']==two['id'] and two['replayed'] and two['path']==x.path
    assert x.ws.resolve(x.path).exists() and x.s.comparison(x.p,x.path,r['id'])['status']=='UNDONE'


def test_review_diff_remains_frozen_after_alternative_edit(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a,mode='revision'));current=x.s.detail(x.p,x.path,a['version']['id'])
    x.s.save(x.p,VersionSave(path=x.path,state_etag=current['state']['state_etag'],request_id=uuid.uuid4().hex,name='Edited later',content='后续完全不同',version_etag=current['version']['etag']),current['version']['id'])
    comparison=x.s.comparison(x.p,x.path,r['id'])
    assert comparison['modified']==a['version']['content'] and comparison['modified']!='后续完全不同' and comparison['readonly']


def test_interrupted_publication_blocks_later_version_writes_without_replay(setup,monkeypatch):
    x=setup;a=create(x);b=request(x,a);original=x.ws.save
    def interrupted(path,content,etag):
        original(path,content,etag)
        raise KeyboardInterrupt('isolated process-interruption boundary')
    monkeypatch.setattr(x.ws,'save',interrupted)
    with pytest.raises(KeyboardInterrupt):x.s.switch(x.p,b)
    reopened=ChapterVersions(x.tools);assert reopened.list(x.p,x.path)['recovery_required']
    with pytest.raises(ConsoleError) as e:create(x,name='Do not write through unresolved state')
    assert e.value.code=='VERSIONS_RECOVERY_REQUIRED'
    assert reopened.detail(x.p,x.path,a['version']['id'])['version']['content']==a['version']['content']


def interrupt_switch(x,monkeypatch,stage='main'):
    a=create(x);b=request(x,a);original=x.ws.save;original_write=versions_module.write
    with monkeypatch.context() as m:
        if stage in {'before','main'}:
            def interrupted(path,content,etag):
                if stage=='main':original(path,content,etag)
                raise KeyboardInterrupt('isolated transaction stop')
            m.setattr(x.ws,'save',interrupted)
        else:
            def interrupted_record(path,value):
                if value.get('action')=='switch' and value.get('status')=='APPLIED':raise KeyboardInterrupt('isolated final publication stop')
                return original_write(path,value)
            m.setattr(versions_module,'write',interrupted_record)
        with pytest.raises(KeyboardInterrupt):x.s.switch(x.p,b)
    return a,b

def recovery_request(x,plan=None,**extra):
    plan=plan or x.s.recovery(x.p,x.path)
    return VersionRecovery(path=x.path,state_etag=plan['state_etag'],main_etag=plan['main_etag'],operation_id=plan['operation_id'],recovery_etag=plan.get('recovery_etag','0'*64),request_id=uuid.uuid4().hex,confirm=True,**extra)

@pytest.mark.parametrize('stage',['before','main','metadata'])
def test_explicit_recovery_of_known_interrupted_switch_is_readonly_until_confirmed(setup,monkeypatch,stage):
    x=setup;before=x.ws.resolve(x.path).read_bytes();protected=snapshot(x);a,b=interrupt_switch(x,monkeypatch,stage)
    file=x.s._load(x.p,x.path)[2];before_plan={str(f.relative_to(x.root)):digest(f.read_bytes()) for f in x.root.rglob('*') if f.is_file()}
    plan=ChapterVersions(x.tools).recovery(x.p,x.path)
    assert plan['required'] and plan['can_recover'] and plan['reason']=='KNOWN_STATE'
    assert plan['operation_id']==b.request_id and plan['modified']==before.decode() and plan['original']==x.ws.content(x.path)['content']
    assert {str(f.relative_to(x.root)):digest(f.read_bytes()) for f in x.root.rglob('*') if f.is_file()}==before_plan
    req=recovery_request(x,plan)
    with pytest.raises(ConsoleError) as e:x.s.recover(x.p,req.model_copy(update={'confirm':False}))
    assert e.value.code=='VERSIONS_CONFIRM' and x.s.list(x.p,x.path)['recovery_required']
    result=x.s.recover(x.p,req);files_after={str(f.relative_to(x.root)):digest(f.read_bytes()) for f in x.root.rglob('*') if f.is_file()}
    replay=x.s.recover(x.p,req)
    assert result['status']=='RECOVERED' and replay['replayed'] and replay['id']==result['id']
    assert {str(f.relative_to(x.root)):digest(f.read_bytes()) for f in x.root.rglob('*') if f.is_file()}==files_after
    assert not x.s.list(x.p,x.path)['recovery_required'] and x.ws.resolve(x.path).read_bytes()==before and snapshot(x)==protected
    assert x.s.detail(x.p,x.path,a['version']['id'])['version']['content']==a['version']['content']
    assert x.s.operations(x.p,x.path)['operations'][0]['status']=='ROLLED_BACK'
    assert x.s.comparison(x.p,x.path,b.request_id)['modified']==a['version']['content']

@pytest.mark.parametrize('external',['main','metadata'])
def test_recovery_preserves_later_author_work_and_refuses_stale_preview(setup,monkeypatch,external):
    x=setup;a,b=interrupt_switch(x,monkeypatch);plan=x.s.recovery(x.p,x.path);req=recovery_request(x,plan)
    if external=='main':x.ws.save(x.path,'后来的作者正文，不能覆盖。',x.ws.content(x.path)['etag'])
    else:
        file=x.s._load(x.p,x.path)[2];value=json.loads(file.read_bytes());value['versions'][0]['description']='Later author metadata';write(file,value)
    before={str(f.relative_to(x.root)):digest(f.read_bytes()) for f in x.root.rglob('*') if f.is_file()}
    assert x.s.recovery(x.p,x.path)['reason']=='EXTERNAL_CHANGED'
    with pytest.raises(ConsoleError) as e:x.s.recover(x.p,req)
    assert e.value.code=='VERSIONS_RECOVERY_UNAVAILABLE'
    assert {str(f.relative_to(x.root)):digest(f.read_bytes()) for f in x.root.rglob('*') if f.is_file()}==before
    assert x.s.list(x.p,x.path)['recovery_required']

@pytest.mark.parametrize('protection',['committed','final'])
def test_recovery_never_expands_protected_manuscript_permissions(setup,monkeypatch,protection):
    x=setup;a,b=interrupt_switch(x,monkeypatch);plan=x.s.recovery(x.p,x.path);req=recovery_request(x,plan)
    if protection=='committed':write_bytes(safe(x.root,'state/chapter-ledger.yaml'),b'entries:\n- chapter: 1\n')
    else:write_bytes(safe(x.root,'chapters/chapter-1/final.txt'),'正式稿。'.encode())
    before=x.ws.resolve(x.path).read_bytes();newplan=x.s.recovery(x.p,x.path)
    assert newplan['reason']=='PROTECTED' and not newplan['can_recover']
    with pytest.raises(ConsoleError):x.s.recover(x.p,req)
    assert x.ws.resolve(x.path).read_bytes()==before and x.s.list(x.p,x.path)['recovery_required']


def test_recovery_rechecks_after_checkpoint_and_never_overwrites_racing_external_text(setup,monkeypatch):
    x=setup;a,b=interrupt_switch(x,monkeypatch);req=recovery_request(x);original=versions_module.checkpoint
    def raced(root,path,source,*args,**kwargs):
        result=original(root,path,source,*args,**kwargs)
        if source=='PRE_PARALLEL_RECOVERY' and path==x.path:x.ws.resolve(x.path).write_bytes('Checkpoint race must survive'.encode())
        return result
    monkeypatch.setattr(versions_module,'checkpoint',raced)
    with pytest.raises(ConsoleError) as e:x.s.recover(x.p,req)
    assert e.value.code=='VERSIONS_CHANGED' and x.ws.content(x.path)['content']=='Checkpoint race must survive'


@pytest.mark.parametrize('stage',['main','source'])
def test_interrupted_undo_can_only_restore_its_own_before_state(setup,monkeypatch,stage):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));switched=x.ws.resolve(x.path).read_bytes();state_before=x.s._load(x.p,x.path)[2].read_bytes();original_save=x.ws.save;original_write=versions_module.write
    with monkeypatch.context() as m:
        if stage=='main':
            def stop_save(path,content,etag):
                original_save(path,content,etag);raise KeyboardInterrupt('isolated undo interruption')
            m.setattr(x.ws,'save',stop_save)
        else:
            def stop_record(path,value):
                if value.get('action')=='undo' and value.get('status')=='UNDONE':raise KeyboardInterrupt('isolated undo completion interruption')
                return original_write(path,value)
            m.setattr(versions_module,'write',stop_record)
        with pytest.raises(KeyboardInterrupt):undo(x,r)
    assert x.s.list(x.p,x.path)['recovery_required']
    plan=x.s.recovery(x.p,x.path);assert plan['can_recover'] and plan['action']=='undo'
    recovered=x.s.recover(x.p,recovery_request(x,plan))
    assert recovered['status']=='RECOVERED' and x.ws.resolve(x.path).read_bytes()==switched
    assert x.s._load(x.p,x.path)[2].read_bytes()==state_before and x.s.operations(x.p,x.path)['operations'][0]['status']=='APPLIED'
    assert undo(x,r)['status']=='UNDONE'


def test_recovery_of_old_incomplete_undo_without_snapshots_stays_manual(setup,monkeypatch):
    x=setup;a,b=interrupt_switch(x,monkeypatch);ws,folder,*_=x.s._load(x.p,x.path);opfile=x.s._op_path(ws,folder,b.request_id);op=json.loads(opfile.read_text());op['action']='undo';op.pop('before_state_revision');write(opfile,op)
    plan=x.s.recovery(x.p,x.path);assert plan['required'] and not plan['can_recover'] and plan['reason']=='INCOMPLETE_HISTORY'


def test_interrupted_recovery_is_not_automatically_replayed(setup,monkeypatch):
    x=setup;a,b=interrupt_switch(x,monkeypatch,stage='metadata');original=x.ws.save;req=recovery_request(x)
    with monkeypatch.context() as m:
        def stop_save(path,content,etag):
            original(path,content,etag);raise KeyboardInterrupt('isolated recovery interruption')
        m.setattr(x.ws,'save',stop_save)
        with pytest.raises(KeyboardInterrupt):x.s.recover(x.p,req)
    assert x.s.list(x.p,x.path)['recovery_required']
    with pytest.raises(ConsoleError):x.s.recover(x.p,req)
    fresh=x.s.recovery(x.p,x.path);assert fresh['can_recover']
    assert x.s.recover(x.p,recovery_request(x,fresh))['status']=='RECOVERED'
    assert not x.s.list(x.p,x.path)['recovery_required']


def test_recovery_does_not_generate_writing_events(setup,monkeypatch):
    x=setup;metrics=metrics_module.Metrics(x.books);monkeypatch.setattr(metrics_module,'observer',metrics.saved)
    x.ws.save(x.path,'第1章\n\n手动写作',x.ws.content(x.path)['etag']);before=copy.deepcopy(metrics.state(x.p)['events'])
    a,b=interrupt_switch(x,monkeypatch);x.s.recover(x.p,recovery_request(x))
    assert metrics.state(x.p)['events']==before
    assert metrics.summary(x.p)['total_han']==x.books.catalog(x.p,include_auxiliary=False)['chapters'][0]['han']


def test_normal_switch_diff_is_frozen_and_legacy_receipts_work(setup):
    x=setup;write_bytes(x.ws.resolve(x.path),'第1章\r\n\r\n原始稿\r\n'.encode('utf-8-sig'));a=create(x,content='第1章\n\n当时的支线\n');b=request(x,a);r=x.s.switch(x.p,b)
    ws,folder,*_=x.s._load(x.p,x.path);opfile=x.s._op_path(ws,folder,r['id']);op=json.loads(opfile.read_text());op.pop('version_etag');write(opfile,op)
    comp=x.s.comparison(x.p,x.path,r['id']);assert not comp['review_only'] and comp['modified']==a['version']['content'] and comp['original']=='第1章\n\n原始稿\n'
    undo(x,r);assert x.s.comparison(x.p,x.path,r['id'])['status']=='UNDONE'
    current=x.s.detail(x.p,x.path,a['version']['id']);x.s.save(x.p,VersionSave(path=x.path,state_etag=current['state']['state_etag'],request_id=uuid.uuid4().hex,name='Later edit',content='后来的支线',version_etag=current['version']['etag']),a['version']['id'])
    assert x.s.comparison(x.p,x.path,r['id'])['modified']==a['version']['content']


def test_history_skips_single_corrupt_records_and_counts_switches_not_undo_files(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));ws,folder,*_=x.s._load(x.p,x.path);opfile=x.s._op_path(ws,folder,r['id']);valid=json.loads(opfile.read_text())
    write_bytes(x.s._op_path(ws,folder,uuid.uuid4().hex),b'{broken')
    bad=dict(valid,id=uuid.uuid4().hex,target='chapters/chapter-2/draft.txt');write(x.s._op_path(ws,folder,bad['id']),bad)
    bad_shape=dict(valid,id=uuid.uuid4().hex,before_name={'not':'renderable'});write(x.s._op_path(ws,folder,bad_shape['id']),bad_shape)
    write_bytes(x.s._op_path(ws,folder,uuid.uuid4().hex),b'['*2000+b']'*2000)
    for _ in range(110):
        id=uuid.uuid4().hex;write(x.s._op_path(ws,folder,id),{'id':id,'action':'undo','status':'UNDONE'})
    result=x.s.operations(x.p,x.path)
    assert len(result['operations'])==1 and result['operations'][0]['id']==r['id'] and result['unavailable']==4 and not result['truncated']


def test_history_discloses_bounded_older_record_coverage(setup):
    x=setup;a=create(x);r=x.s.switch(x.p,request(x,a));ws,folder,*_=x.s._load(x.p,x.path);template=json.loads(x.s._op_path(ws,folder,r['id']).read_text())
    for _ in range(105):
        id=uuid.uuid4().hex;write(x.s._op_path(ws,folder,id),dict(template,id=id))
    result=x.s.operations(x.p,x.path);assert len(result['operations'])==100 and result['truncated']


def test_recovery_preserves_exact_crlf_bom_and_rejects_malformed_snapshot(setup,monkeypatch):
    x=setup;original='第1章\r\n\r\n原始换行\r\n'.encode('utf-8-sig');write_bytes(x.ws.resolve(x.path),original)
    a,b=interrupt_switch(x,monkeypatch,stage='metadata');plan=x.s.recovery(x.p,x.path);x.s.recover(x.p,recovery_request(x,plan))
    assert x.ws.resolve(x.path).read_bytes()==original
    a,b=interrupt_switch(x,monkeypatch);ws,folder,*_=x.s._load(x.p,x.path);op=json.loads(x.s._op_path(ws,folder,b.request_id).read_text())
    meta=safe(x.root,'history/revisions/'+op['before_revision']+'/revision.json');row=json.loads(meta.read_text());row['path']='chapters/chapter-2/draft.txt';write(meta,row)
    plan=x.s.recovery(x.p,x.path);assert plan['required'] and not plan['can_recover'] and plan['reason']=='INCOMPLETE_HISTORY'
    with pytest.raises(ConsoleError):x.s.comparison(x.p,x.path,b.request_id)


def test_no_pending_transaction_has_no_recovery_write_or_fake_plan(setup):
    x=setup;before=set(x.root.rglob('*'));plan=x.s.recovery(x.p,x.path)
    assert not plan['required'] and not plan['can_recover'] and plan['reason']=='NOT_NEEDED' and 'recovery_etag' not in plan
    assert before==set(x.root.rglob('*'))
