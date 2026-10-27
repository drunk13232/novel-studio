"""Fixed cache roots, frozen author consent and no actual user directories."""
from pathlib import Path
from types import SimpleNamespace
import os,time
import pytest
from pydantic import ValidationError
from app.cache_maintenance import CacheMaintenance,Cleanup
from app.errors import ConsoleError

@pytest.fixture
def caches(tmp_path):
    engine=tmp_path/'engine';(engine/'desktop').mkdir(parents=True)
    project=tmp_path/'book';(project/'assets/original').mkdir(parents=True)
    def workspace(id):
        if id!='book':raise ConsoleError('Unknown project',404)
        return SimpleNamespace(root=project)
    return CacheMaintenance(engine,SimpleNamespace(workspace=workspace)),engine,project

def old(path,text='cache'):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);os.utime(path,(time.time()-3*86400,)*2);return path

def test_cleanup_requires_frozen_confirmation_and_keeps_originals_and_new_files(caches):
    s,root,book=caches;a=old(root/'web/.build-cache/npm/a');new=root/'web/.build-cache/npm/new';new.write_text('new')
    original=old(book/'assets/original/picture.jpg','original');thumb=old(book/'assets/thumbnails/test.jpg')
    v=s.scan('book');result=s.cleanup(Cleanup(preview_id=v['preview_id'],buckets=['npm','thumbnails'],confirm=True),'book')
    assert result['deleted_files']==2 and not a.exists() and not thumb.exists() and original.read_text()=='original' and new.exists()
    assert result['reclaimed_bytes'] is None
    with pytest.raises(ConsoleError):s.cleanup(Cleanup(preview_id=v['preview_id'],buckets=['npm'],confirm=True),'book')

def test_stale_changed_or_foreign_previews_delete_nothing(caches):
    s,root,_=caches;a=old(root/'desktop/build/a');b=old(root/'desktop/build/b');v=s.scan('book');b.write_text('changed')
    with pytest.raises(ConsoleError):s.cleanup(Cleanup(preview_id=v['preview_id'],buckets=['build'],confirm=True),'book')
    assert a.exists() and b.exists()
    with pytest.raises(ConsoleError):s.cleanup(Cleanup(preview_id=v['preview_id'],buckets=['build'],confirm=True),'')
    s.previews[v['preview_id']]['at']-=901
    with pytest.raises(ConsoleError):s.cleanup(Cleanup(preview_id=v['preview_id'],buckets=['build'],confirm=True),'book')

def test_build_lock_and_fixed_paths(caches):
    s,root,_=caches;v=s.scan();(root/'desktop/.cache-operation.lock').write_text('owned build')
    with pytest.raises(ConsoleError):s.scan()
    with pytest.raises(ConsoleError):s.cleanup(Cleanup(preview_id=v['preview_id'],buckets=['build'],confirm=True))
    assert (root/'desktop/.cache-operation.lock').read_text()=='owned build'
    for body in [{'preview_id':'a'*32,'buckets':['../../projects'],'confirm':True},{'preview_id':'a'*32,'buckets':['npm'],'confirm':False},{'preview_id':'a'*32,'buckets':['npm'],'confirm':True,'path':'C:/'}]:
        with pytest.raises(ValidationError):Cleanup.model_validate(body)

def test_links_are_never_followed(caches,tmp_path):
    s,root,_=caches;victim=old(tmp_path/'outside/value');cache=root/'web/.build-cache/npm';cache.mkdir(parents=True)
    try:(cache/'link').symlink_to(victim)
    except OSError:pytest.skip('Symlink privilege unavailable')
    v=s.scan();assert not any(row['files'] for row in v['buckets']) and victim.exists()
