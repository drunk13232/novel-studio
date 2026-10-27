"""Focused local clue-board checks. Only temporary project files are written."""
import copy
import json
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.clue_board import BOARD_PATH, ClueBoardService, ClueBoardUpdate, ClueBoardBatchUpdate
from app.errors import ConsoleError
from app.library.storage import digest


def fixture_board(tmp_path, n=24, written=22):
    chapters = [{'id': 'chapter_' + str(i), 'number': i, 'title': '章' + str(i),
                 'volume': 'v1' if i <= 12 else 'v2', 'order': i,
                 'draft': f'chapters/chapter-{i}/draft.txt', 'characters': 5 if i <= written else 0,
                 'foreshadowing': {'introduce': [], 'advance': [], 'resolve': []}}
                for i in range(1, n + 1)]
    values = {'clue_a': {'title': '钥匙', 'status': 'OPEN', 'introduced_chapter': 1,
                         'planned_window': {'earliest': None, 'preferred': None, 'latest': None}},
              'clue_b': {'title': '计划秘密', 'status': 'RESOLVED', 'introduced_chapter': 23, 'resolved_chapter': 24}}
    docs = {'state/foreshadowing.yaml': {'foreshadowing': values},
            'state/chapter-ledger.yaml': {'entries': [{'chapter': 1}]}}
    for path, data in docs.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(data, allow_unicode=True), encoding='utf8')
    ws = SimpleNamespace(root=tmp_path, _save_lock=threading.RLock(),
                         yaml_file=lambda path: yaml.safe_load((tmp_path/path).read_text(encoding='utf8')))
    anchors = []
    planning = SimpleNamespace(rows=lambda p, kind: copy.deepcopy(chapters if kind == 'chapter' else [{'id': 'v1', 'number': 1}, {'id': 'v2', 'number': 2}]))
    registry = SimpleNamespace(book_center=SimpleNamespace(catalog=lambda p, **kwargs: {'chapters': copy.deepcopy(chapters)}))
    tools = SimpleNamespace(planning=planning, writable=lambda p: ws)
    wb = SimpleNamespace(ws=lambda p: ws, registry=registry, tools=tools, lock=threading.RLock(),
                         knowledge=SimpleNamespace(anchors=lambda p: copy.deepcopy(anchors)))
    return ClueBoardService(wb), chapters, docs, anchors


def clue(board, id='clue_a'):
    return next(item for item in board['clues'] if item['id'] == id)


def update(service, **values):
    return service.update('p', ClueBoardUpdate(etag=service.get('p')['etag'], **values))


def rewrite_docs(root, docs):
    for path, value in docs.items():
        (root/path).write_text(yaml.safe_dump(value, allow_unicode=True), encoding='utf8')


def test_overdue_exact_boundary_cross_volume_and_future_plans(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path, written=21)
    board = service.get('p')
    assert clue(board)['elapsed_chapters'] == 20 and not clue(board)['overdue']
    assert board['latest_chapter']['number'] == 21
    assert not clue(board, 'clue_b')['introduced'] and clue(board, 'clue_b')['tracking_status'] == 'planned'
    assert not clue(board, 'clue_b')['overdue']  # A future plan isn't a confirmed planting/payoff.
    chapters[21]['characters'] = 5
    board = service.get('p')
    assert clue(board)['elapsed_chapters'] == 21 and clue(board)['overdue_by'] == 1
    assert clue(board)['overdue'] and clue(board)['planned_recovery'] == []
    assert clue(board)['introduced']['volume'] != board['latest_chapter']['volume']
    assert board['clues'][0]['id'] == 'clue_a'
    update(service, threshold=21)
    assert not clue(service.get('p'))['overdue']


def test_status_flow_metadata_only_etag_history_and_restart(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path)
    before = {path: (tmp_path/path).read_bytes() for path in docs}
    assert not (tmp_path/BOARD_PATH).exists()
    original = service.get('p')
    assert not (tmp_path/BOARD_PATH).exists()  # Opening is read-only.
    for state in ['planned', 'planted', 'partial', 'recovered']:
        board = update(service, clue_id='clue_a', tracking_status=state, recovery_chapter_id=chapters[-1]['id'], note='作者备注')
        assert clue(board)['tracking_status'] == state
        assert clue(board)['evidenced_status'] == 'planted'
        assert clue(board)['tracking_is_manual'] and clue(board)['note'] == '作者备注'
        assert clue(board)['recovery_chapter']['id'] == chapters[-1]['id']
    assert not clue(board)['overdue']
    assert {path: (tmp_path/path).read_bytes() for path in docs} == before
    assert len(list((tmp_path/'history/revisions').glob('*/revision.json'))) == 3
    restarted = ClueBoardService(service.workbench)
    assert clue(restarted.get('p'))['tracking_status'] == 'recovered'
    update(restarted, clue_id='clue_a', recovery_chapter_id='')
    assert clue(restarted.get('p'))['recovery_chapter'] is None
    with pytest.raises(ConsoleError) as error:
        restarted.update('p', ClueBoardUpdate(etag=original['etag'], clue_id='clue_a', note='不能覆盖'))
    assert error.value.status == 409


def test_plan_cards_and_ambiguous_legacy_numbers_are_not_facts(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path)
    chapters[7]['foreshadowing'] = {'introduce': ['clue_only_plan'], 'resolve': []}
    chapters[11]['foreshadowing'] = {'resolve': ['clue_only_plan']}
    board = service.get('p')
    assert clue(board, 'clue_only_plan')['planned_introduction'][0]['number'] == 8
    assert clue(board, 'clue_only_plan')['planned_recovery'][0]['number'] == 12
    assert clue(board, 'clue_only_plan')['evidenced_status'] == 'planned'
    assert clue(board, 'clue_only_plan')['elapsed_chapters'] is None
    # A repeated display number must never silently bind a legacy numeric fact.
    chapters[1]['number'] = 1
    board = service.get('p')
    assert clue(board)['introduced'] is None and clue(board)['evidence'] == []
    assert not clue(board)['overdue']


def test_located_evidence_and_stale_anchor_navigation(tmp_path):
    service, chapters, _, anchors = fixture_board(tmp_path)
    # Full-text UTF-16 coordinates are carried through without changing or trimming.
    anchors.append({'id': 'anchor_a', 'target_type': 'clue', 'target_id': 'clue_a',
                    'chapter_id': chapters[2]['id'], 'path': 'chapters/chapter-3/draft.txt',
                    'located': True, 'start': 13, 'end': 18, 'document_revision': 'f'*64,
                    'anchor': {'exact': '😀钥匙。', 'prefix': '之前', 'suffix': '之后'}})
    entry = clue(service.get('p'))['evidence'][0]
    assert entry['location']['start'] == 13 and entry['location']['end'] == 18
    assert entry['location']['document_revision'] == 'f'*64
    assert entry['chapter']['path'] == anchors[0]['path'] and entry['exact'] == '😀钥匙。'
    anchors[0]['located'] = False
    entry = clue(service.get('p'))['evidence'][0]
    assert entry['location'] is None and not entry['located']


def test_committed_resolution_and_unknown_or_empty_sources(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path)
    value = docs['state/foreshadowing.yaml']['foreshadowing']['clue_a']
    value.update(status='RESOLVED', resolved_chapter=3)
    rewrite_docs(tmp_path, docs)
    assert clue(service.get('p'))['tracking_status'] != 'recovered'
    docs['state/chapter-ledger.yaml']['entries'].append({'chapter': 3})
    rewrite_docs(tmp_path, docs)
    assert clue(service.get('p'))['actual_recovery']['number'] == 3
    assert not clue(service.get('p'))['overdue']
    docs['state/foreshadowing.yaml']['foreshadowing'] = {}
    chapters.clear()
    rewrite_docs(tmp_path, docs)
    board = service.get('p')
    assert board['clues'] == [] and board['chapters'] == [] and board['latest_chapter'] is None
    assert board['summary']['total'] == 0 and board['summary']['overdue'] == 0


def test_no_cross_project_target_and_strict_updates(tmp_path):
    service, _, _, _ = fixture_board(tmp_path)
    with pytest.raises(ConsoleError):
        update(service, clue_id='foreign', tracking_status='recovered')
    with pytest.raises(ConsoleError):
        update(service, clue_id='clue_a', recovery_chapter_id='foreign')
    with pytest.raises(ConsoleError):
        update(service, note='未指定目标')
    with pytest.raises(ValidationError):
        ClueBoardUpdate(etag=digest(b''), threshold=0)
    assert not (tmp_path/BOARD_PATH).exists()


def test_real_registry_planning_and_anchor_reopen(tmp_path, monkeypatch):
    from app.config import Settings
    from app.main import create_app
    from app.domain.planning import Volume, ChapterCard, dump
    from app.studio_tools import utf16_index, normalized
    engine = Path(__file__).resolve().parents[3]
    shutil.copytree(engine/'engine', tmp_path/'engine')
    shutil.copytree(engine/'templates', tmp_path/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA', str(tmp_path/'app-data'))
    app = create_app(Settings(workspace=tmp_path))
    app.state.testing = True
    with TestClient(app) as client:
        client.headers['X-Novel-Request'] = client.get('/api/session').json()['request_token']
        draft = client.post('/api/drafts', json={'input': {'title': '伏笔隔离检查', 'premise': '只验证数据。'}}).json()
        created = client.post('/api/projects', json={'draft_id': draft['id'], 'version': draft['version'], 'confirm': True})
        assert created.status_code == 201, created.text
        p = created.json()['id']
        ws = app.state.registry.workspace(p)
        volume = Volume(id='volume_'+'1'*32, number=1, title='测试卷')
        card = ChapterCard(id='chapter_'+'1'*32, number=1, order=1, title='钥匙', volume=volume.id,
                           foreshadowing={'introduce': ['safe_clue']})
        for relative, value in [('outlines/volumes/'+volume.id+'.yaml', volume), ('outlines/chapters/'+card.id+'.yaml', card)]:
            file = ws.root/relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(dump(value.model_dump()), encoding='utf8')
        manuscript = 'chapters/chapter-1/draft.txt'
        file = ws.root/manuscript
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('# 第一章\n\n😀一把钥匙放在门边。', encoding='utf8')
        (ws.root/'state/foreshadowing.yaml').write_text(yaml.safe_dump({'foreshadowing': {'safe_clue': {'title': '安全线索', 'status': 'OPEN', 'introduced_chapter': None}}}, allow_unicode=True), encoding='utf8')
        service = ClueBoardService(app.state.workbench)
        first = service.get(p)
        assert first['clues'][0]['evidenced_status'] == 'planned'
        # Reuse the real anchor service through its validated API request model.
        from app.library.knowledge import AnchorRequest
        knowledge = app.state.workbench.knowledge
        view = knowledge.view(p)
        raw = ws.content(manuscript)
        exact = '一把钥匙'
        text = normalized(raw)
        start = utf16_index(text, text.index(exact))
        knowledge.anchor(p, AnchorRequest(path=manuscript, document_revision=raw['etag'], start=start,
            end=start+len(exact), selected_text=exact, target_type='clue', target_id='safe_clue', etag='', confirm=True))
        before = {str(f.relative_to(ws.root)): f.read_bytes() for d in ['state', 'settings', 'chapters'] for f in (ws.root/d).rglob('*') if f.is_file()}
        board = service.get(p)
        row = clue(board, 'safe_clue')
        assert row['evidenced_status'] == 'planted' and row['evidence'][0]['located']
        assert row['evidence'][0]['location']['start'] == start
        updated = service.update(p, ClueBoardUpdate(etag=board['etag'], clue_id='safe_clue', tracking_status='recovered', recovery_chapter_id=card.id, note='只作作者追踪'))
        assert clue(updated, 'safe_clue')['tracking_status'] == 'recovered'
        assert clue(ClueBoardService(app.state.workbench).get(p), 'safe_clue')['note'] == '只作作者追踪'
        assert before == {str(f.relative_to(ws.root)): f.read_bytes() for d in ['state', 'settings', 'chapters'] for f in (ws.root/d).rglob('*') if f.is_file()}

        # Reuse the already-existing literary clue lifecycle, not a second store.
        from app.creative.literary_models import Save, CoreDetails, Event, Evidence
        core = app.state.literary_core
        saved = core.save(p, Save(etag=app.state.workbench.entries(p)['etag'], text='测试作者线索记录',
            details=CoreDetails(kind='clue', title='未发出的信'), confirm=True))
        record_id = saved['record']['id']
        assert clue(service.get(p), record_id)['evidenced_status'] == 'planned'
        quote = Evidence(path=manuscript, revision=raw['etag'], start=start, end=start+len(exact), quote=exact)
        for phase, expected in [('PLACED','planted'),('PARTIAL','partial'),('RESOLVED','recovered'),('PARTIAL','partial')]:
            core.event(p, record_id, Event(etag=app.state.workbench.entries(p)['etag'], phase=phase,
                       text='引用原文的作者观察', evidence=[quote], confirm=True))
            observed = clue(service.get(p), record_id)
            assert observed['evidenced_status'] == expected and observed['source'] == 'metadata/studio/reading.json'
            assert any(e['kind']=='literary' and e['located'] for e in observed['evidence'])
        # Real project services also use the atomic batch path. The literary
        # source notebook is not rewritten when author tracking is changed.
        notebook = (ws.root/'metadata/studio/reading.json').read_bytes()
        batched = service.batch(p, ClueBoardBatchUpdate(etag=service.get(p)['etag'], confirm=True, updates=[
            {'clue_id': 'safe_clue', 'tracking_status': 'partial', 'note': '只改看板作者追踪'},
            {'clue_id': record_id, 'reset_tracking': True}]))
        assert batched['batch_summary']['updated'] == 2
        assert clue(batched, 'safe_clue')['tracking_status'] == 'partial'
        assert (ws.root/'metadata/studio/reading.json').read_bytes() == notebook
        assert before == {str(f.relative_to(ws.root)): f.read_bytes() for d in ['state', 'settings', 'chapters'] for f in (ws.root/d).rglob('*') if f.is_file()}





def test_large_heading_only_and_invalid_prose_do_not_crash_or_advance(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path, written=20)
    for chapter in chapters[20:]:
        file = tmp_path/chapter['draft']
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'\xffbad encoding')
    board = service.get('p')
    assert board['latest_chapter']['number'] == 20
    assert board['progress_incomplete']
    file = tmp_path/chapters[23]['draft']
    file.write_text('# Planned heading only\n', encoding='utf8')
    board = service.get('p')
    assert board['latest_chapter']['number'] == 20
    # A huge chapter may still prove nonempty from its bounded beginning; no
    # full count or ws.content-sized response is needed just to advance progress.
    file.write_text('# Title\n\nVisible body.\n' + 'x'*3_000_000, encoding='utf8')
    board = service.get('p')
    assert board['latest_chapter']['number'] == 24


def test_developing_or_ready_is_not_partial_payoff(tmp_path):
    service, _, docs, _ = fixture_board(tmp_path)
    for status in ['OPEN', 'DEVELOPING', 'READY']:
        docs['state/foreshadowing.yaml']['foreshadowing']['clue_a']['status'] = status
        rewrite_docs(tmp_path, docs)
        assert clue(service.get('p'))['evidenced_status'] == 'planted'


def test_damaged_overlay_has_specific_error_without_touching_sources(tmp_path):
    service, _, docs, _ = fixture_board(tmp_path)
    before = {path: (tmp_path/path).read_bytes() for path in docs}
    target = tmp_path/BOARD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'{damaged')
    with pytest.raises(ConsoleError) as error:
        service.get('p')
    assert error.value.code == 'CLUE_BOARD_INVALID_RECORD'
    assert before == {path: (tmp_path/path).read_bytes() for path in docs}


def test_clear_manual_status_follows_source_and_preserves_notes_and_links(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path)
    before = {path: (tmp_path/path).read_bytes() for path in docs}
    original = service.get('p')
    changed = update(service, clue_id='clue_a', tracking_status='recovered', recovery_chapter_id=chapters[2]['id'], note='保留备注')
    assert clue(changed)['tracking_is_manual'] and not clue(changed)['overdue']
    restored = update(service, clue_id='clue_a', reset_tracking=True)
    assert clue(restored)['tracking_status'] == clue(restored)['evidenced_status'] == 'planted'
    assert not clue(restored)['tracking_is_manual'] and clue(restored)['overdue']
    assert clue(restored)['note'] == '保留备注' and clue(restored)['recovery_chapter']['id'] == chapters[2]['id']
    stored = json.loads((tmp_path/BOARD_PATH).read_text(encoding='utf8'))
    assert 'tracking_status' not in stored['items']['clue_a']
    assert before == {path: (tmp_path/path).read_bytes() for path in docs}
    with pytest.raises(ConsoleError) as error:
        service.update('p', ClueBoardUpdate(etag=original['etag'], clue_id='clue_a', reset_tracking=True))
    assert error.value.code == 'CLUE_BOARD_CHANGED'
    with pytest.raises(ConsoleError) as error:
        update(service, clue_id='clue_a', reset_tracking=True, tracking_status='partial')
    assert error.value.code == 'CLUE_BOARD_INVALID_CHANGE'


def test_planned_window_explained_separately_from_overdue_threshold(tmp_path):
    service, chapters, docs, _ = fixture_board(tmp_path)
    raw = docs['state/foreshadowing.yaml']['foreshadowing']['clue_a']
    raw['planned_window'] = {'earliest': 2, 'preferred': 3, 'latest': 4}
    rewrite_docs(tmp_path, docs)
    board = update(service, threshold=999)
    item = clue(board)
    assert not item['overdue'] and item['planned_window_passed']
    assert item['planned_window_chapters']['latest']['id'] == chapters[3]['id']
    assert not item['planned_window_invalid']
    assert {volume['id'] for volume in board['volumes']} == {'v1', 'v2'}
    raw['planned_window'] = {'earliest': 10, 'preferred': None, 'latest': 3}
    rewrite_docs(tmp_path, docs)
    item = clue(service.get('p'))
    assert item['planned_window_invalid'] and not item['planned_window_passed']
    raw['planned_window'] = {'earliest': None, 'preferred': None, 'latest': 1}
    chapters[1]['number'] = 1
    rewrite_docs(tmp_path, docs)
    item = clue(service.get('p'))
    assert item['planned_window_chapters']['latest'] is None and not item['planned_window_passed']


def test_batch_all_drafts_one_write_one_checkpoint_and_source_safety(tmp_path, monkeypatch):
    import app.clue_board as module
    service, chapters, docs, _ = fixture_board(tmp_path)
    update(service, clue_id='clue_a', note='原备注')
    before = {path: (tmp_path/path).read_bytes() for path in docs}
    checkpoints, writes = [], []
    original_checkpoint, original_write = module.checkpoint, module.write
    def counted_checkpoint(*args, **kwargs):
        checkpoints.append(args)
        return original_checkpoint(*args, **kwargs)
    def counted_write(*args, **kwargs):
        writes.append(args)
        return original_write(*args, **kwargs)
    monkeypatch.setattr(module, 'checkpoint', counted_checkpoint)
    monkeypatch.setattr(module, 'write', counted_write)
    body = ClueBoardBatchUpdate(etag=service.get('p')['etag'], confirm=True, updates=[
        {'clue_id': 'clue_a', 'tracking_status': 'partial', 'recovery_chapter_id': chapters[3]['id'], 'note': '第一条草稿'},
        {'clue_id': 'clue_b', 'tracking_status': 'planted', 'note': '第二条草稿'}])
    result = service.batch('p', body)
    assert result['batch_summary'] == {'updated': 2, 'clue_ids': ['clue_a', 'clue_b']}
    assert clue(result)['tracking_status'] == 'partial' and clue(result)['note'] == '第一条草稿'
    assert clue(result, 'clue_b')['note'] == '第二条草稿'
    assert clue(result, 'clue_b')['evidenced_status'] == 'planned'
    assert len(writes) == len(checkpoints) == 1
    assert writes[0][0] == tmp_path/BOARD_PATH and checkpoints[0][1:3] == (BOARD_PATH, 'PRE_CLUE_BOARD_BATCH')
    assert before == {path: (tmp_path/path).read_bytes() for path in docs}
    assert clue(ClueBoardService(service.workbench).get('p'), 'clue_b')['note'] == '第二条草稿'
    # A repeated confirm keeps the old etag and cannot write again.
    with pytest.raises(ConsoleError) as error:
        service.batch('p', body)
    assert error.value.code == 'CLUE_BOARD_CHANGED'
    assert len(writes) == len(checkpoints) == 1


@pytest.mark.parametrize('invalid', [
    {'clue_id': 'foreign', 'note': '越界'},
    {'clue_id': 'clue_b', 'recovery_chapter_id': 'foreign_chapter'},
    {'clue_id': 'clue_b', 'note': None},
    {'clue_id': 'clue_a', 'note': '重复ID'},
    {'clue_id': 'clue_b'},
    {'clue_id': 'clue_b', 'tracking_status': 'partial', 'reset_tracking': True},
])
def test_invalid_second_batch_item_rejects_everything_without_history(tmp_path, invalid):
    service, _, _, _ = fixture_board(tmp_path)
    update(service, clue_id='clue_a', note='必须保持')
    before = (tmp_path/BOARD_PATH).read_bytes()
    history = set((tmp_path/'history').rglob('*'))
    with pytest.raises(ConsoleError):
        service.batch('p', ClueBoardBatchUpdate(etag=service.get('p')['etag'], confirm=True, updates=[
            {'clue_id': 'clue_a', 'note': '不能只保存第一条'}, invalid]))
    assert (tmp_path/BOARD_PATH).read_bytes() == before
    assert set((tmp_path/'history').rglob('*')) == history


def test_batch_reset_and_recovery_only_keep_other_notes(tmp_path):
    service, chapters, _, _ = fixture_board(tmp_path)
    update(service, clue_id='clue_a', note='保留A', tracking_status='recovered')
    update(service, clue_id='clue_b', note='保留B', recovery_chapter_id=chapters[2]['id'])
    result = service.batch('p', ClueBoardBatchUpdate(etag=service.get('p')['etag'], confirm=True, updates=[
        {'clue_id': 'clue_a', 'reset_tracking': True, 'recovery_chapter_id': chapters[3]['id']},
        {'clue_id': 'clue_b', 'recovery_chapter_id': ''}]))
    assert clue(result)['tracking_status'] == 'planted' and not clue(result)['tracking_is_manual']
    assert clue(result)['note'] == '保留A' and clue(result)['recovery_chapter']['id'] == chapters[3]['id']
    assert clue(result, 'clue_b')['note'] == '保留B' and clue(result, 'clue_b')['recovery_chapter'] is None


def test_batch_requires_confirmation_and_has_bounded_size(tmp_path):
    service, _, _, _ = fixture_board(tmp_path)
    etag = service.get('p')['etag']
    with pytest.raises(ValidationError):
        ClueBoardBatchUpdate(etag=etag, confirm=False, updates=[{'clue_id':'clue_a','note':'x'}])
    with pytest.raises(ValidationError):
        ClueBoardBatchUpdate(etag=etag, confirm=True, updates=[{'clue_id':str(i),'note':'x'} for i in range(201)])
    with pytest.raises(ConsoleError) as error:
        service.batch('p', ClueBoardBatchUpdate.model_construct(etag=etag, confirm=False, updates=[]))
    assert error.value.code == 'CLUE_BOARD_CONFIRM_REQUIRED'
    assert not (tmp_path/BOARD_PATH).exists()
