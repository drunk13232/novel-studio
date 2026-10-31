"""Recovery cleanup concurrency: real isolated API/files, no model or desktop run."""
from pathlib import Path
import hashlib,json,shutil
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app

ENGINE=Path(__file__).resolve().parents[3]

@pytest.fixture
def local(tmp_path,monkeypatch):
    workspace=tmp_path/'workspace';shutil.copytree(ENGINE/'desktop/preview-template',workspace)
    data=tmp_path/'app-data';monkeypatch.setenv('NOVEL_STUDIO_DATA',str(data));monkeypatch.setenv('NOVEL_STUDIO_HOME',str(tmp_path/'home'));monkeypatch.setenv('CODEX_HOME',str(tmp_path/'empty-codex'));monkeypatch.setenv('NOVEL_DEMO','1')
    before={p.relative_to(workspace).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
    app=create_app(Settings(workspace=workspace));client=TestClient(app,base_url='http://127.0.0.1');client.headers['X-Novel-Request']=client.get('/api/session').json()['request_token'];project=next((workspace/'projects').glob('novel_*')).name;path='chapters/chapter-2/draft.md';base='/api/projects/'+project;doc=client.get(base+'/files/content',params={'path':path}).json()
    namespace=hashlib.sha256(str(workspace.resolve()).casefold().encode()).hexdigest()[:20];record=data/namespace/'recovery'/project/(hashlib.sha256(path.encode()).hexdigest()+'.json')
    yield client,base,path,doc,record
    after={p.relative_to(workspace).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
    assert all(after.get(name)==digest for name,digest in before.items())
    assert set(after)-set(before)<= {'web/.runtime/studio-data.lock'}
    if 'web/.runtime/studio-data.lock' in after:assert (workspace/'web/.runtime/studio-data.lock').read_bytes()==b'0'
    client.close()

def put(local,text):
    c,b,p,d,_=local;r=c.put(b+'/studio/recovery',json={'path':p,'etag':d['etag'],'content':text});assert r.status_code==200,r.text;return r.json()
def delete(local,revision):
    c,b,p,_,_=local;return c.delete(b+'/studio/recovery',params={'path':p},headers={'If-Match':'"'+revision+'"'})
def get(local):
    c,b,p,_,_=local;return c.get(b+'/studio/recovery',params={'path':p})

def test_receipt_matches_actual_bytes_without_changing_recovery_format(local):
    r=put(local,'Public isolated recovery A');record=local[-1];raw=record.read_bytes();assert set(json.loads(raw))=={'path','etag','content','saved_at'};assert r['saved'] is True;assert r['recovery_revision']==hashlib.sha256(raw).hexdigest();copy=get(local).json();assert copy['recovery_revision']==r['recovery_revision'];assert record.read_bytes()==raw

def test_stale_cleanup_keeps_newer_copy(local):
    a=put(local,'Public isolated A');b=put(local,'Public isolated B');raw=local[-1].read_bytes();r=delete(local,a['recovery_revision']);assert r.status_code==412;assert r.json()['code']=='RECOVERY_CHANGED';assert get(local).json()['recovery_revision']==b['recovery_revision'];assert local[-1].read_bytes()==raw

def test_missing_precondition_cannot_delete_a_new_copy(local):
    assert get(local).json() is None;put(local,'Public isolated newer recovery');assert delete(local,'missing').status_code==412;assert get(local).json()['content']=='Public isolated newer recovery'

def test_conditional_cleanup_is_idempotent_after_actual_deletion(local):
    a=put(local,'Public isolated A');assert delete(local,a['recovery_revision']).json()=={'deleted':True,'recovery_revision':'missing'};assert delete(local,a['recovery_revision']).status_code==200;assert delete(local,'missing').status_code==200;assert get(local).json() is None

@pytest.mark.parametrize('header',['*','W/"'+'a'*64+'"','a'*64,'"short"','"'+('a'*64)+'", "'+('b'*64)+'"','""'])
def test_invalid_or_weak_precondition_never_deletes(local,header):
    put(local,'Public isolated A');raw=local[-1].read_bytes();c,b,p,_,_=local;r=c.delete(b+'/studio/recovery',params={'path':p},headers={'If-Match':header});assert r.status_code==422;assert local[-1].read_bytes()==raw

def test_legacy_copy_and_explicit_legacy_delete_remain_compatible(local):
    c,b,p,d,record=local;record.parent.mkdir(parents=True,exist_ok=True);legacy={'path':p,'etag':d['etag'],'content':'Legacy public fixture','saved_at':'2020-01-01T00:00:00+00:00'};raw=json.dumps(legacy).encode();record.write_bytes(raw);assert get(local).json()['content']==legacy['content'];assert record.read_bytes()==raw;assert c.delete(b+'/studio/recovery',params={'path':p}).status_code==200;assert not record.exists()

def test_corrupt_copy_is_reported_and_retained(local):
    put(local,'Public isolated A');record=local[-1];record.write_bytes(b'{broken recovery');r=get(local);assert r.status_code==422;assert r.json()['code']=='RECOVERY_INVALID';assert record.read_bytes()==b'{broken recovery'

def test_cleanup_keeps_project_scope_and_session_protection(local):
    a=put(local,'Public isolated A');c,b,_,_,record=local;raw=record.read_bytes();assert c.delete(b+'/studio/recovery',params={'path':'../private.json'},headers={'If-Match':'"'+a['recovery_revision']+'"'}).status_code==403;assert c.delete('/api/projects/novel_'+'0'*32+'/studio/recovery',params={'path':local[2]},headers={'If-Match':'"'+a['recovery_revision']+'"'}).status_code==404;c.headers.pop('X-Novel-Request');assert delete(local,a['recovery_revision']).status_code==403;assert record.read_bytes()==raw

def test_cleanup_never_creates_writing_events(local):
    c,b,*_=local;before=c.get(b+'/experience/focus-boundary').json()['cursor'];a=put(local,'Public isolated A');assert delete(local,a['recovery_revision']).status_code==200;assert c.get(b+'/experience/focus-boundary').json()['cursor']==before

def test_concurrent_new_copy_always_survives_old_cleanup(local):
    c,b,p,d,_=local
    for _ in range(3):
        a=put(local,'Public isolated A')
        with ThreadPoolExecutor(max_workers=2) as pool:
            clean=pool.submit(delete,local,a['recovery_revision'])
            new=pool.submit(c.put,b+'/studio/recovery',json={'path':p,'etag':d['etag'],'content':'Public isolated B'})
            cleaned,written=clean.result(),new.result()
        for response in [cleaned,written]:
            if response.status_code==409:assert response.json()['code']=='WORKSPACE_BUSY'
        assert cleaned.status_code in {200,412,409}
        assert written.status_code in {200,409}
        # The shared workspace lease can reject simultaneous requests. An explicit
        # latest-copy retry is safe; never retry the stale destructive cleanup.
        if written.status_code==409:put(local,'Public isolated B')
        assert get(local).json()['content']=='Public isolated B'
