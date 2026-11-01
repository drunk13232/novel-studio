"""Isolated daily-workflow safety; adapter stubs are not real model acceptance."""
from pathlib import Path
from types import SimpleNamespace
import time
import pytest
from app.errors import ConsoleError
from app.library.data import DataCenter
from app.library.storage import checkpoint,revisions,write
from app.cache_maintenance import CacheMaintenance,Cleanup
from app.studio_tools import SelectionRequest,normalized,text_hash,utf16_index
from app.author_workbench import Entry
from test_creative_maps_audio import local

@pytest.fixture
def storage(tmp_path):
    root=tmp_path/'book';root.mkdir();engine=tmp_path/'engine';(engine/'desktop').mkdir(parents=True)
    registry=SimpleNamespace(engine=engine,workspace=lambda p:SimpleNamespace(root=root if p=='book' else tmp_path/'other'))
    return DataCenter(registry,tmp_path/'settings.json'),root,registry

def cache(root,name='old.jpg'):
    p=root/'assets/thumbnails'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'LOCAL_CACHE');return p

def test_project_cleanup_is_frozen_single_use_and_does_not_sweep_new_files(storage):
    service,root,_=storage;old=cache(root);preview=service.cleanup('book');new=cache(root,'new.jpg')
    with pytest.raises(ConsoleError):service.cleanup('book',True,'清理可重建缓存')
    result=service.cleanup('book',True,'清理可重建缓存',preview['preview_id'])
    assert result['deleted_files']==1 and not old.exists() and new.exists() and result['reclaimed_bytes'] is None
    with pytest.raises(ConsoleError):service.cleanup('book',True,'清理可重建缓存',preview['preview_id'])

def test_changed_foreign_expired_or_malformed_cleanup_deletes_nothing(storage):
    service,root,_=storage;a=cache(root);b=cache(root,'b.jpg');preview=service.cleanup('book');b.write_bytes(b'CHANGED')
    with pytest.raises(ConsoleError):service.cleanup('book',True,'清理可重建缓存',preview['preview_id'])
    assert a.exists() and b.exists()
    with pytest.raises(ConsoleError):service.cleanup('other',True,'清理可重建缓存',preview['preview_id'])
    service.cleanup_previews[preview['preview_id']]['at']-=901
    with pytest.raises(ConsoleError):service.cleanup('book',True,'清理可重建缓存',preview['preview_id'])
    with pytest.raises(ConsoleError):service.cleanup('book',True,'清理可重建缓存',[])
    assert a.exists() and b.exists()

def test_duplicate_history_needs_separate_explicit_confirmation(storage):
    service,root,_=storage;p=root/'chapters/draft.txt';p.parent.mkdir();p.write_text('SYNTHETIC_BODY',encoding='utf8')
    first=checkpoint(root,'chapters/draft.txt');second=checkpoint(root,'chapters/draft.txt');write(service.settings_path,{'revision_retention':'DEDUP_PREVIEW'})
    preview=service.cleanup('book');assert preview['history_files']==1
    with pytest.raises(ConsoleError,match='另行明确确认'):service.cleanup('book',True,'清理可重建缓存',preview['preview_id'])
    assert len(revisions(root))==2 and p.read_text('utf8')=='SYNTHETIC_BODY'
    service.cleanup('book',True,'清理可重建缓存',preview['preview_id'],True)
    assert len(revisions(root))==1 and p.read_text('utf8')=='SYNTHETIC_BODY'

def test_build_cache_whitelist_preserves_audit_evidence_and_old_releases(storage):
    _,root,registry=storage;engine=registry.engine;owned=[];protected=[]
    for name in ['desktop/build/NovelStudio/regenerable.toc','desktop/build/pyinstaller-cache/cache.bin','desktop/build/experience-local/report.json','desktop/build/source-before.json','release/v1/NovelStudio.exe']:
        p=engine/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('LOCAL_FIXTURE');time_before=time.time()-3*86400
        import os
        os.utime(p,(time_before,time_before));(owned if '/NovelStudio/' in name or '/pyinstaller-cache/' in name else protected).append(p)
    service=CacheMaintenance(engine,registry);preview=service.scan('book')
    service.cleanup(Cleanup(preview_id=preview['preview_id'],buckets=['build'],confirm=True),'book')
    assert all(not p.exists() for p in owned) and all(p.exists() for p in protected)

def test_selection_passes_explicit_controls_to_existing_adapter_without_model_call(local,monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3]/'scripts'))
    _,app,p=local;tools=app.state.studio_tools;doc=tools.doc(p,'chapters/story/draft.txt');body=normalized(doc);cid,_,_=tools.chapter(p,doc['path']);seen={}
    def adapter(*args,**kwargs):seen.update(kwargs);return SimpleNamespace(metadata={'backend':'MOCK','model':'codex::isolated'})
    monkeypatch.setattr('app.creative.tasks.adapter',adapter)
    manager=tools.manager(p)
    monkeypatch.setattr(manager,'prepared',lambda *args,**kwargs:SimpleNamespace(id='mock-prepared-no-worker',public=lambda:{'id':'mock-prepared-no-worker','status':'QUEUED'}))
    request=SelectionRequest(project_id=p,chapter_id=cid,path=doc['path'],document_revision=doc['etag'],originalHash=text_hash(body),start=0,end=utf16_index(body,len(body)),selected_text=body,style='none',ai_model='codex::isolated',ai_controls={'model':'codex::isolated','parameters':{'reasoning_effort':'high'},'context':{'budget':16000}})
    result=tools.start(p,request)
    assert result['id']=='mock-prepared-no-worker' and seen['controls'].parameters=={'reasoning_effort':'high'} and seen['controls'].context.budget==16000
    assert tools.doc(p,doc['path'])['etag']==doc['etag']

def test_chapter_work_evidence_is_current(local):
    _,app,p=local;tools=app.state.studio_tools;work=app.state.writing_assist.workbench;doc=tools.doc(p,'chapters/story/draft.txt');body=normalized(doc);entries=work.entries(p)
    work.save_entry(p,Entry(etag=entries['etag'],kind='revision',text='Exact source issue',path=doc['path'],start=0,exact=body[:4],revision=doc['etag']))
    view=work.chapter_work(p,doc['path']);assert view['revisions'][0]['located'] is True
    tools.registry.workspace(p).save(doc['path'],doc['content']+' changed',doc['etag'])
    view=work.chapter_work(p,doc['path']);assert view['revisions'][0]['located'] is False
    assert view['counts']=={'todos':0,'revisions':1}
