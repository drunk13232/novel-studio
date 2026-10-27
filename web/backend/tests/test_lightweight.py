from pathlib import Path
import json,time
import pytest
from app.projects.service import NovelWorkspace,committed_chapters
from app.studio import manuscript_summary
from app.errors import ConsoleError

def test_ledger_cache_observes_bytes_and_protected_final(tmp_path):
    (tmp_path/'state').mkdir();(tmp_path/'chapters/chapter-1').mkdir(parents=True)
    ledger=tmp_path/'state/chapter-ledger.yaml';ledger.write_text('entries: []\n','utf8')
    draft=tmp_path/'chapters/chapter-1/draft.txt';draft.write_text('第一章 测试\n原文','utf8')
    ws=NovelWorkspace(tmp_path);assert ws.content('chapters/chapter-1/draft.txt')['editable']
    ledger.write_text('entries:\n- chapter: 1\n','utf8')
    assert not ws.content('chapters/chapter-1/draft.txt')['editable']
    with pytest.raises(ConsoleError):ws.save('chapters/chapter-1/draft.txt','覆盖',ws.content('chapters/chapter-1/draft.txt')['etag'])
    assert draft.read_text('utf8').endswith('原文')
    ledger.write_text('entries: []\n','utf8');assert ws.content('chapters/chapter-1/draft.txt')['editable']

def test_display_cache_external_revision_and_project_scope(tmp_path):
    for n in ['a','b']:
        f=tmp_path/n/'chapters/chapter-1/draft.txt';f.parent.mkdir(parents=True);f.write_text('第一章 标题\n'+('甲' if n=='a' else '乙乙'),'utf8')
    def read(n):
        root=tmp_path/n;f=root/'chapters/chapter-1/draft.txt';s=f.stat()
        return manuscript_summary(str(root),'chapters/chapter-1/draft.txt',s.st_mtime_ns,s.st_ctime_ns,s.st_size)
    assert read('a')['han']!=read('b')['han'];first=read('a')['han']
    (tmp_path/'a/chapters/chapter-1/draft.txt').write_text('第一章 标题\n更多文字','utf8')
    assert read('a')['han']>first

def test_ledger_parser_rejects_unsafe_alias():
    with pytest.raises(ConsoleError):committed_chapters('entries: &a []\ncopy: *a\n')


def test_continuation_uses_valid_saved_prose_not_other_project_or_unread_path():
    from app.studio import continuation
    rows=[{'number':1,'path':'chapters/chapter-1/final.md','modified_at':'2026-10-17','versions':[{'path':'chapters/chapter-1/final.md'}]},
          {'number':2,'path':'chapters/chapter-2/draft.md','modified_at':'2026-10-16','versions':[{'path':'chapters/chapter-2/draft.md'}]}]
    # Last writing wins even when an older Final has a newer filesystem timestamp.
    prefs={'last_edited_files':{'p':'chapters/chapter-2/draft.md'},'last_files':{'p':'chapters/chapter-1/final.md'}}
    assert continuation(rows,prefs,'p')['number']==2
    assert continuation(rows,prefs,'other')['number']==1
    prefs['last_edited_files']['p']='../other/private.md'
    assert continuation(rows,prefs,'p')['number']==1
    prefs['last_files']['p']='deleted.md'
    assert continuation(rows,prefs,'p')['number']==1
    assert continuation([],prefs,'p') is None
    assert rows[0]['path']=='chapters/chapter-1/final.md'
