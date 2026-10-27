"""Real local save/history tests in isolated projects; no model or private data."""
import threading
from types import SimpleNamespace

import pytest

from app.errors import ConsoleError
from app.global_replace import GlobalReplace,ReplaceQuery,ReplaceApply,ReplaceUndo
from app.library.storage import safe,read,write,write_bytes
from app.projects.service import NovelWorkspace
from app.studio_tools import StudioTools


@pytest.fixture
def service(tmp_path):
    root=tmp_path/'projects'/'isolated';root.mkdir(parents=True)
    write_bytes(safe(root,'state/chapter-ledger.yaml'),b'entries: []\n')
    workspace=NovelWorkspace(root)
    cards=[{'id':f'c{i}','number':i,'title':f'Chapter {i}','volume':'v1' if i<3 else 'v2'} for i in range(1,4)]
    volumes=[{'id':'v1','title':'Volume one'},{'id':'v2','title':'Volume two'}]
    def catalog(project,**options):
        rows=[]
        for c in cards:
            folder=safe(root,f'chapters/chapter-{c["number"]}')
            final=next((f'{folder.relative_to(root).as_posix()}/{file}' for file in ['final.txt','final.md'] if (folder/file).is_file()),None)
            draft=next((f'{folder.relative_to(root).as_posix()}/{file}' for file in ['draft.txt','draft.md'] if (folder/file).is_file()),None)
            rows.append({**c,'final':final,'draft':draft})
        return {'chapters':rows,'volumes':volumes}
    registry=SimpleNamespace(workspace=lambda p:workspace,get=lambda p:{'title':'Isolated'},book_center=SimpleNamespace(catalog=catalog))
    characters=SimpleNamespace(list=lambda p:[{'canonical':{'id':'char_one','name':'洛岑','aliases':['Luo Cen']}}],writable=lambda p:workspace)
    bible=SimpleNamespace(list=lambda p:[{'id':'place_one','name':'镜城','aliases':[]}])
    planning=SimpleNamespace(rows=lambda p,kind:cards if kind=='chapter' else volumes)
    tools=StudioTools(registry,planning,characters,bible,None,None)
    service=GlobalReplace(SimpleNamespace(registry=registry,tools=tools,lock=threading.RLock()))
    return service,workspace,root


def put(ws,number,text,version='draft.txt',bom=False):
    path=f'chapters/chapter-{number}/{version}';write_bytes(ws.resolve(path),text.encode('utf-8-sig' if bom else 'utf8'));return path


def preview(service,query='cat',replacement='dog',**kwargs):return service.search('p',ReplaceQuery(query=query,replacement=replacement,**kwargs))
def apply(service,value,**kwargs):
    count=kwargs.pop('expected_count',value['pending_regular_hits']+(value['pending_name_hits'] if kwargs.get('include_protected_names') else 0))
    return service.apply('p',ReplaceApply(preview_id=value['id'],all_remaining=True,expected_count=count,confirm=True,**kwargs))


@pytest.mark.parametrize('settings,expected',[
    ({},2),({'case_sensitive':False},3),({'whole_word':True},1),
    ({'whole_word':True,'case_sensitive':False},2),({'mode':'regex','query':'c.t'},2),
])
def test_four_modes(service,settings,expected):
    s,ws,_=service;put(ws,1,'cat Cat cats')
    assert preview(s,**settings)['total_hits']==expected


def test_regex_groups_and_unicode_utf16_after_sequential_apply(service):
    s,ws,_=service;path=put(ws,1,'😀 cat1 cat2\r\nend',bom=True)
    value=preview(s,query=r'cat(\d)',replacement=r'dog\1\nX',mode='regex')
    assert value['hits'][0]['start']==3
    first=s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[value['hits'][0]['id']],expected_count=1,confirm=True))
    remaining=next(h for h in first['preview']['hits'] if h['status']=='PENDING')
    assert remaining['start']==10 and ws.content(path)['bom']
    s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[remaining['id']],expected_count=1,confirm=True))
    assert ws.content(path)['content']=='😀 dog1\r\nX dog2\r\nX\r\nend'


def test_scope_is_stable_id_and_unselected_bytes_never_change(service):
    s,ws,_=service;paths=[put(ws,i,'cat') for i in range(1,4)];untouched=ws.resolve(paths[2]).read_bytes()
    value=preview(s,scope='volume',volume='v1');result=apply(s,value)
    assert result['replaced']==2 and ws.resolve(paths[2]).read_bytes()==untouched
    value=preview(s,query='cat',scope='chapters',chapter_ids=['c3']);assert value['total_hits']==1
    with pytest.raises(ConsoleError):preview(s,scope='chapters',chapter_ids=['different-project'])
    with pytest.raises(ConsoleError):preview(s,scope='paths',paths=['state/chapter-ledger.yaml'])


def test_names_default_protection_and_explicit_accept(service):
    s,ws,_=service;path=put(ws,1,'洛岑在镜城。洛岑望向城市。')
    value=preview(s,query='洛岑',replacement='新名')
    assert value['protected_name_hits']==2 and not any(h['default_selected'] for h in value['hits'])
    with pytest.raises(ConsoleError):apply(s,value,expected_count=2)
    result=apply(s,value,include_protected_names=True);assert result['replaced']==2 and '新名' in ws.content(path)['content']
    assert s.tools.characters.list('p')[0]['canonical']['name']=='洛岑'


def test_only_names_skip_other_matches(service):
    s,ws,_=service;put(ws,1,'洛岑 岑岑 镜城 城市')
    value=preview(s,query='岑|城',mode='regex',names_mode='only')
    assert value['total_hits']==2 and all(h['protected_names'] for h in value['hits'])


def test_skip_and_count_confirmation_and_duplicates(service):
    s,ws,_=service;path=put(ws,1,'cat cat')
    value=preview(s)
    skipped=s.apply('p',ReplaceApply(preview_id=value['id'],skip_ids=[value['hits'][0]['id']],expected_count=0,confirm=True))
    assert skipped['replaced']==0 and ws.content(path)['content']=='cat cat'
    result=apply(s,skipped['preview']);assert result['replaced']==1 and ws.content(path)['content']=='cat dog'
    with pytest.raises(ConsoleError):s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[value['hits'][1]['id']],expected_count=1,confirm=True))


def test_whole_batch_undo_and_stale_preview_guard(service):
    s,ws,_=service;paths=[put(ws,i,'cat') for i in range(1,4)];value=preview(s);result=apply(s,value)
    restored=s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    assert restored['status']=='UNDONE' and all(ws.content(p)['content']=='cat' for p in paths)
    with pytest.raises(ConsoleError):s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    with pytest.raises(ConsoleError):apply(s,value)


def test_final_is_separate_copy_and_undo_removes_only_copy(service):
    s,ws,_=service;original=put(ws,1,'cat','final.txt');baseline=ws.resolve(original).read_bytes()
    result=apply(s,preview(s));target=result['paths'][0]
    assert target!=original and '/manual-' in target and ws.content(target)['content']=='dog'
    assert ws.resolve(original).read_bytes()==baseline
    s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    assert not ws.resolve(target).exists() and ws.resolve(original).read_bytes()==baseline


def test_final_copy_undo_reverses_only_real_save_delta(service,monkeypatch):
    from app import writing_metrics as wm
    s,ws,root=service;put(ws,1,'天地','final.txt')
    s.registry.root=root.parent
    metrics=wm.Metrics(SimpleNamespace(registry=s.registry))
    monkeypatch.setattr(wm,'observer',metrics.saved)
    result=apply(s,preview(s,query='天地',replacement='天地玄黄'))
    assert [e['han'] for e in metrics.state('p')['events']]==[2]
    s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    events=metrics.state('p')['events']
    assert [e['han'] for e in events]==[2,-2] and events[-1]['source']=='RESTORE'


def test_all_etags_checked_before_any_write_or_undo(service):
    s,ws,_=service;p1=put(ws,1,'cat');p2=put(ws,2,'cat');value=preview(s)
    ws.save(p2,'external',ws.content(p2)['etag'])
    with pytest.raises(ConsoleError):apply(s,value)
    assert ws.content(p1)['content']=='cat'
    ws.save(p2,'cat',ws.content(p2)['etag']);result=apply(s,preview(s))
    ws.save(p2,'external',ws.content(p2)['etag'])
    with pytest.raises(ConsoleError):s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    assert ws.content(p1)['content']=='dog'


def test_apply_failure_compensates_earlier_files(service,monkeypatch):
    s,ws,_=service;p1=put(ws,1,'cat');p2=put(ws,2,'cat');value=preview(s);save=ws.save
    def fail(path,text,etag):
        if path==p2 and text=='dog':raise OSError('isolated simulated disk full')
        return save(path,text,etag)
    monkeypatch.setattr(ws,'save',fail)
    with pytest.raises(OSError):apply(s,value)
    assert ws.content(p1)['content']==ws.content(p2)['content']=='cat'
    assert s.batches('p')['batches'][0]['status']=='ROLLED_BACK'


def test_copy_save_failure_cleans_new_final_revision(service,monkeypatch):
    s,ws,root=service;path=put(ws,1,'cat','final.txt');value=preview(s)
    monkeypatch.setattr(ws,'save',lambda *args:(_ for _ in ()).throw(OSError('isolated failure')))
    with pytest.raises(OSError):apply(s,value)
    assert list((root/'chapters/chapter-1').glob('manual-*'))==[] and ws.content(path)['content']=='cat'


def test_mid_undo_failure_compensates_undone_files(service,monkeypatch):
    s,ws,_=service;p1=put(ws,1,'cat');p2=put(ws,2,'cat');result=apply(s,preview(s));save=ws.save
    def fail(path,text,etag):
        if path==p2 and text=='cat':raise OSError('isolated undo failure')
        return save(path,text,etag)
    monkeypatch.setattr(ws,'save',fail)
    with pytest.raises(OSError):s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    assert ws.content(p1)['content']==ws.content(p2)['content']=='dog'
    assert s.batches('p')['batches'][0]['status']=='APPLIED'


@pytest.mark.parametrize('query',['[','a*','(?=cat)'])
def test_invalid_and_zero_width_regex_never_write(service,query):
    s,ws,_=service;path=put(ws,1,'cat')
    with pytest.raises(ConsoleError):preview(s,query=query,mode='regex')
    assert ws.content(path)['content']=='cat'


def test_catastrophic_regex_times_out_and_large_chapter_is_bounded(service):
    s,ws,_=service;path=put(ws,1,'a'*50000+'!')
    with pytest.raises(ConsoleError,match='超时'):preview(s,query='(a+)+$',mode='regex')
    put(ws,1,'cat '+'x'*(2*1024*1024-8))
    assert preview(s)['total_hits']==1
    put(ws,2,'x'*(2*1024*1024+1));value=preview(s)
    assert not value['coverage']['complete'] and len(value['errors'])==1 and value['total_hits']==1


def test_empty_and_no_match_are_honest(service):
    s,ws,_=service;value=preview(s)
    assert value['total_hits']==0 and value['coverage']['complete']
    put(ws,1,'');assert preview(s)['total_hits']==0


def test_imported_revision_only_chapter_remains_searchable(service):
    s,ws,_=service;path=put(ws,1,'cat','manual-import-one.txt')
    value=preview(s);assert value['total_hits']==1 and value['hits'][0]['path']==path


def test_actual_book_catalog_can_list_oversized_text_without_reading_it(service):
    from app.book_center import BookCenter
    from app.projects.writing_config import defaults
    s,ws,root=service;put(ws,1,'x'*(ws.max_bytes+1))
    manifest={'title':'Isolated','writing':defaults()}
    s.registry.get=lambda p:manifest
    rows={'chapter':[{'id':'c1','number':1,'title':'Oversized','volume':'','status':'DRAFT','order':1}],'volume':[]}
    planning=SimpleNamespace(rows=lambda p,kind:rows[kind])
    books=BookCenter(s.registry,planning,None,root/'config')
    s.registry.book_center=books
    result=books.catalog('p',include_auxiliary=False,include_text_counts=False)
    assert len(result['chapters'])==1
    value=preview(s);assert value['total_hits']==0 and not value['coverage']['complete'] and len(value['errors'])==1


def test_anthology_does_not_recurse_into_other_private_projects(service):
    from app.projects.writing_config import defaults
    s,ws,_=service;s.registry.get=lambda p:{'title':'Collection','writing':defaults('anthology')}
    s.registry.book_center.catalog=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('Must not read linked stories'))
    assert s.catalog('p')['chapters']==[]


def test_unknown_confirmation_and_changed_names_block(service):
    s,ws,_=service;path=put(ws,1,'cat');value=preview(s)
    with pytest.raises(ConsoleError):s.apply('p',ReplaceApply(preview_id=value['id'],all_remaining=True,expected_count=1))
    s.tools.bible.list=lambda p:[{'name':'new name'}]
    with pytest.raises(ConsoleError):apply(s,value)
    assert ws.content(path)['content']=='cat'


def test_legacy_adapter_uses_frozen_preview_and_rejects_forged_offsets(service):
    s,ws,_=service;path=put(ws,1,'cat cat')
    body=SimpleNamespace(query='cat',replacement='dog',paths=[],chapter='',volume='',hits=[],confirm=True)
    body.hits=s.legacy_replacements('p',body)['hits'];body.hits[0]['start']=99
    with pytest.raises(ConsoleError):s.legacy_replacements('p',body,True)
    assert ws.content(path)['content']=='cat cat'
    body.hits=s.legacy_replacements('p',body)['hits'];s.legacy_replacements('p',body,True)
    assert ws.content(path)['content']=='dog dog'


def test_identical_replacement_is_not_reported_as_a_write(service):
    s,ws,root=service;path=put(ws,1,'cat dog');value=preview(s,query='cat|dog',replacement='dog',mode='regex')
    assert value['total_hits']==2 and value['unchanged_hits']==1 and value['remaining']==1
    same=next(h for h in value['hits'] if h['status']=='UNCHANGED')
    assert not same['default_selected']
    result=apply(s,value)
    assert result['replaced']==1 and result['preview']['applied_hits']==1 and result['preview']['unchanged_hits']==1
    assert ws.content(path)['content']=='dog dog'
    value=preview(s,query='dog',replacement='dog')
    assert value['remaining']==0 and value['unchanged_hits']==2
    with pytest.raises(ConsoleError):apply(s,value)
    assert len(s.batches('p')['batches'])==1


def test_skip_metadata_has_no_empty_batch_and_protected_defer_is_not_a_skip(service):
    s,ws,_=service;path=put(ws,1,'cat 洛岑');value=preview(s,query='cat|洛岑',replacement='new',mode='regex')
    result=apply(s,value)
    assert result['replaced']==1 and result['skipped']==0 and result['protected_remaining']==1
    assert result['preview']['skipped_hits']==0
    name=next(h for h in result['preview']['hits'] if h['protected_names'])
    skipped=s.apply('p',ReplaceApply(preview_id=value['id'],skip_ids=[name['id']],expected_count=0,confirm=True))
    assert skipped['status']=='SKIPPED' and skipped['skipped']==1 and skipped['preview']['skipped_hits']==1
    assert len(s.batches('p')['batches'])==1
    restored=s.apply('p',ReplaceApply(preview_id=value['id'],restore_skip_ids=[name['id']],expected_count=0,confirm=True))
    assert restored['status']=='RESTORED' and restored['restored']==1 and restored['preview']['pending_name_hits']==1
    assert len(s.batches('p')['batches'])==1 and ws.content(path)['content']=='new 洛岑'


def test_consecutive_replacement_recalculates_new_canonical_name_boundaries(service):
    s,ws,_=service;path=put(ws,1,'x岑 岑');value=preview(s,query='x|岑',replacement='洛',mode='regex')
    assert value['pending_name_hits']==0
    first=s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[value['hits'][0]['id']],expected_count=1,confirm=True))
    assert ws.content(path)['content']=='洛岑 岑'
    assert first['preview']['pending_name_hits']==1 and first['preview']['pending_regular_hits']==1
    newly_protected=next(h for h in first['preview']['hits'] if h['status']=='PENDING' and h['protected_names'])
    assert newly_protected['protected_names']==['洛岑'] and not newly_protected['default_selected']
    second=apply(s,first['preview'])
    assert second['replaced']==1 and ws.content(path)['content']=='洛岑 洛'


def test_partial_rename_never_silently_removes_original_name_protection(service):
    s,ws,_=service;path=put(ws,1,'洛岑');value=preview(s,query='洛|岑',replacement='x',mode='regex',names_mode='only')
    first=s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[value['hits'][0]['id']],include_protected_names=True,expected_count=1,confirm=True))
    remaining=next(h for h in first['preview']['hits'] if h['status']=='PENDING')
    assert ws.content(path)['content']=='x岑' and remaining['protected_names']==['洛岑']
    assert first['preview']['pending_regular_hits']==0 and first['preview']['pending_name_hits']==1
    with pytest.raises(ConsoleError):apply(s,first['preview'],expected_count=1)


def test_locations_follow_saved_revision_and_applied_ranges(service):
    s,ws,_=service;path=put(ws,1,'😀 cat\ncat');value=preview(s,replacement='天地玄黄')
    assert (value['hits'][0]['line'],value['hits'][0]['column'])==(1,4)
    first=s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[value['hits'][0]['id']],expected_count=1,confirm=True))
    original=next(h for h in first['preview']['hits'] if h['status']=='APPLIED')
    assert (original['start'],original['end'],original['location_text'])==(3,7,'天地玄黄')
    remaining=next(h for h in first['preview']['hits'] if h['status']=='PENDING')
    assert remaining['line']==2 and remaining['column']==1
    second=apply(s,first['preview'])
    assert all(h['revision']==ws.content(path)['etag'] and h['location_text']=='天地玄黄' for h in second['preview']['hits'])


def test_skipped_location_tracks_other_edits_and_restores_safely(service):
    s,ws,_=service;path=put(ws,1,'cat cat');value=preview(s,replacement='long dog')
    s.apply('p',ReplaceApply(preview_id=value['id'],skip_ids=[value['hits'][1]['id']],expected_count=0,confirm=True))
    first=s.apply('p',ReplaceApply(preview_id=value['id'],hit_ids=[value['hits'][0]['id']],expected_count=1,confirm=True))
    skipped=next(h for h in first['preview']['hits'] if h['status']=='SKIPPED')
    assert skipped['start']==9 and skipped['location_text']=='cat'
    restored=s.apply('p',ReplaceApply(preview_id=value['id'],restore_skip_ids=[skipped['id']],expected_count=0,confirm=True))
    assert restored['preview']['remaining']==1
    apply(s,restored['preview']);assert ws.content(path)['content']=='long dog long dog'


def test_restoring_skipped_hit_rejects_external_revision_change(service):
    s,ws,_=service;path=put(ws,1,'cat');value=preview(s)
    s.apply('p',ReplaceApply(preview_id=value['id'],skip_ids=[value['hits'][0]['id']],expected_count=0,confirm=True))
    ws.save(path,'external',ws.content(path)['etag'])
    with pytest.raises(ConsoleError) as error:s.apply('p',ReplaceApply(preview_id=value['id'],restore_skip_ids=[value['hits'][0]['id']],expected_count=0,confirm=True))
    assert error.value.code=='REPLACE_REVISION_CHANGED' and ws.content(path)['content']=='external'


@pytest.mark.parametrize('replacement',[r'\2',r'\g<missing>',r'\q'])
def test_invalid_replacement_is_checked_even_without_matches(service,replacement):
    s,ws,_=service;path=put(ws,1,'nothing matches')
    with pytest.raises(ConsoleError) as error:preview(s,query='(cat)',replacement=replacement,mode='regex')
    assert error.value.code=='REPLACE_REPLACEMENT_INVALID' and ws.content(path)['content']=='nothing matches'


def test_paged_counts_are_consistent_after_skip_and_apply(service):
    s,ws,_=service;put(ws,1,'cat '*250);value=preview(s)
    assert len(value['hits'])==100 and value['total_hits']==250 and value['more_pages']
    page=s.page('p',value['id'],200,100);assert len(page['hits'])==50 and not page['more_pages']
    skipped=s.apply('p',ReplaceApply(preview_id=value['id'],skip_ids=[value['hits'][0]['id']],expected_count=0,confirm=True))
    result=apply(s,skipped['preview'])
    assert result['replaced']==249 and result['skipped']==0
    final=s.page('p',value['id'],200,100)
    assert (final['total_hits'],final['applied_hits'],final['skipped_hits'],final['remaining'])==(250,249,1,0)
    file=result['batch']['files'][0]
    assert file['count']==249 and file['title']=='Chapter 1' and result['batch']['query']['query']=='cat'


@pytest.mark.parametrize('source',['cat\nend','cat\r\nend'])
def test_regex_newline_preserves_document_format_and_undo(service,source):
    s,ws,_=service;path=put(ws,1,source);before=ws.resolve(path).read_bytes()
    result=apply(s,preview(s,query='cat',replacement=r'new\r\nline',mode='regex'))
    assert ws.content(path)['line_ending']!='MIXED' and '\r\r' not in ws.content(path)['content']
    s.undo('p',result['batch']['id'],ReplaceUndo(confirm=True))
    assert ws.resolve(path).read_bytes()==before


def test_bare_carriage_return_replacement_is_rejected_before_write(service):
    s,ws,_=service;path=put(ws,1,'cat\nend')
    with pytest.raises(ConsoleError) as error:preview(s,query='cat',replacement=r'new\rline',mode='regex')
    assert error.value.code=='REPLACE_REPLACEMENT_INVALID' and ws.content(path)['content']=='cat\nend'


def test_one_search_per_project_and_exception_release_do_not_block_saves(service,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    s,ws,_=service;path=put(ws,1,'cat');original=s._search;started=threading.Event();release=threading.Event()
    def blocked(p,b):
        started.set();assert release.wait(3)
        raise ConsoleError('isolated search failure',422)
    monkeypatch.setattr(s,'_search',blocked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running=pool.submit(s.search,'p',ReplaceQuery(query='cat'))
        assert started.wait(3)
        try:
            with pytest.raises(ConsoleError) as error:s.search('p',ReplaceQuery(query='cat'))
            assert error.value.code=='REPLACE_SEARCH_BUSY'
            # The running read-only scan owns no manuscript save lock.
            ws.save(path,'cat cat',ws.content(path)['etag'])
        finally:release.set()
        with pytest.raises(ConsoleError):running.result(timeout=3)
    monkeypatch.setattr(s,'_search',original)
    assert preview(s)['total_hits']==2


def test_preview_return_revalidates_read_only_without_replaying_search(service,monkeypatch):
    s,ws,root=service;put(ws,1,'cat');value=preview(s)
    baseline={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    monkeypatch.setattr(s,'search',lambda *args:(_ for _ in ()).throw(AssertionError('Restore must not search')))
    result=s.page('p',value['id'],revalidate=True)
    assert result['can_apply'] and result['validation']['status']=='VALID' and result['validation']['checked_files']==1
    assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}==baseline


def test_preview_return_detects_text_scope_and_name_changes(service):
    s,ws,_=service;path=put(ws,1,'cat');value=preview(s)
    ws.save(path,'changed',ws.content(path)['etag'])
    result=s.page('p',value['id'],revalidate=True)
    assert not result['can_apply'] and result['validation']['reason']=='DOCUMENT_CHANGED'
    value=preview(s,query='changed');put(ws,2,'cat')
    result=s.page('p',value['id'],revalidate=True)
    assert not result['can_apply'] and result['validation']['reason']=='SCOPE_CHANGED'
    value=preview(s);s.tools.bible.list=lambda p:[{'name':'a new canonical name'}]
    result=s.page('p',value['id'],revalidate=True)
    assert not result['can_apply'] and result['validation']['reason']=='NAMES_CHANGED'


def test_expired_preview_return_does_not_restore_executable_state(service):
    s,ws,_=service;put(ws,1,'cat');value=preview(s)
    path=s._path('p','previews',value['id']);stored=read(path);stored['expires_at']='2000-01-01T00:00:00+00:00';write(path,stored)
    result=s.page('p',value['id'],revalidate=True)
    assert not result['can_apply'] and result['validation']['status']=='EXPIRED'
    with pytest.raises(ConsoleError):apply(s,value)


def test_preview_return_revalidation_respects_aggregate_size_limit(service,monkeypatch):
    import app.global_replace as module
    s,ws,_=service;put(ws,1,'cat');value=preview(s);monkeypatch.setattr(module,'MAX_BYTES',1)
    result=s.page('p',value['id'],revalidate=True)
    assert not result['can_apply'] and result['validation']['status']=='UNVERIFIED' and result['validation']['reason']=='REVALIDATION_LIMIT'


def test_regular_pagination_does_not_revalidate_manuscript_text(service,monkeypatch):
    s,ws,_=service;put(ws,1,'cat');value=preview(s)
    monkeypatch.setattr(s.tools,'doc',lambda *args:(_ for _ in ()).throw(AssertionError('Ordinary paging must not rescan text')))
    assert s.page('p',value['id'])['total_hits']==1


def test_preview_return_after_protected_copy_revalidates_both_sources(service):
    s,ws,_=service;put(ws,1,'cat','final.txt');result=apply(s,preview(s))
    value=s.page('p',result['preview']['id'],revalidate=True)
    assert value['can_apply'] and value['validation']['checked_files']==2
