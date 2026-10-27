"""Author clue board projection over existing state, plans and entity anchors.

Only metadata/studio/clue-board.json is writable here. Author tracking never
becomes story State, Canon or proof that an event happened in the manuscript.
"""
from collections import Counter
import copy
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.errors import ConsoleError
from app.library.storage import checkpoint, digest, now, safe, write

BOARD_PATH = 'metadata/studio/clue-board.json'
TRACKING = {'planned', 'planted', 'partial', 'recovered'}


class ClueBoardUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    threshold: int | None = Field(default=None, ge=1, le=1000)
    clue_id: str | None = Field(default=None, min_length=1, max_length=200)
    tracking_status: Literal['planned', 'planted', 'partial', 'recovered'] | None = None
    recovery_chapter_id: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=8000)
    reset_tracking: bool = False


class ClueBoardChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    clue_id: str = Field(min_length=1, max_length=200)
    tracking_status: Literal['planned', 'planted', 'partial', 'recovered'] | None = None
    recovery_chapter_id: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=8000)
    reset_tracking: bool = False


class ClueBoardBatchUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    confirm: Literal[True]
    updates: list[ClueBoardChange] = Field(min_length=1, max_length=200)


class ClueBoardService:
    def __init__(self, workbench):
        self.workbench = workbench

    def _local(self, p):
        path = safe(self.workbench.ws(p).root, BOARD_PATH)
        try:
            present = path.exists()
            raw = path.read_bytes() if present else b''
            stored = json.loads(raw.decode('utf-8-sig')) if present else {}
        except (ValueError, UnicodeError, OSError):
            raise ConsoleError('伏笔看板记录无法读取，请从历史版本恢复', 422, code='CLUE_BOARD_INVALID_RECORD') from None
        if not isinstance(stored, dict) or not isinstance(stored.get('items', {}), dict):
            raise ConsoleError('伏笔看板记录损坏，请从历史版本恢复', 422, code='CLUE_BOARD_INVALID_RECORD')
        return path, stored, digest(raw)

    def _chapters(self, p):
        """Reuse stable plans/catalog order; numeric legacy references must be unique."""
        wb = self.workbench
        plans = wb.tools.planning.rows(p, 'chapter')
        try:
            catalog = wb.registry.book_center.catalog(p, include_auxiliary=False, include_text_counts=False)
            chapters = catalog['chapters']
        except ConsoleError as exc:
            # Existing catalog rejects duplicate display numbers. Keep stable plan
            # rows available but never attach a numeric manuscript to either twin.
            if exc.status != 409:
                raise
            volumes = wb.tools.planning.rows(p, 'volume')
            ranks = {v['id']: i for i, v in enumerate(sorted(volumes, key=lambda v: v['number']))}
            chapters = sorted(plans, key=lambda c: (ranks.get(c.get('volume'), 999), c.get('order', c['number'])))
        rows = []
        for i, chapter in enumerate(chapters):
            if chapter.get('kind') == 'anthology':
                continue  # Never traverse another novel through anthology membership.
            path = chapter.get('final') or chapter.get('draft') or chapter.get('path') or ''
            rows.append({'id': chapter['id'], 'number': chapter.get('number'),
                         'title': chapter.get('title') or '', 'volume': chapter.get('volume', ''),
                         'path': path, 'position': i,
                         'has_prose': bool(path and (chapter.get('characters', 0) > 0 or chapter.get('han', 0) > 0)),
                         'progress_unknown': False})
        # Find just the last nonblank manuscript rather than counting every book
        # body. Bounded reads keep an unusually large/invalid chapter from taking
        # the entire board down. The existing prose helper strips headings.
        from app.book_center import prose
        for chapter in reversed(rows):
            if chapter['has_prose']:
                break
            if not chapter['path']:
                continue
            target = safe(wb.ws(p).root, chapter['path'])
            if not target.is_file():
                chapter['progress_unknown'] = True
                continue
            try:
                with target.open('r', encoding='utf-8-sig', newline=None) as stream:
                    text = stream.read(65536)
                chapter['has_prose'] = bool(prose(text).strip())
                chapter['progress_unknown'] = not chapter['has_prose'] and target.stat().st_size > len(text.encode('utf8'))
            except (UnicodeError, OSError):
                chapter['progress_unknown'] = True
            if chapter['has_prose']:
                break
        return rows, plans

    @staticmethod
    def _resolve(reference, by_id, by_number):
        if isinstance(reference, str) and reference in by_id:
            return by_id[reference]
        if isinstance(reference, int) and not isinstance(reference, bool):
            matches = by_number.get(reference, [])
            return matches[0] if len(matches) == 1 else None
        return None


    def _literary(self, p, source, by_id):
        """Reuse LiteraryCore's actual lifecycle and evidence validator in place."""
        core = getattr(getattr(self.workbench.tools, 'writing_assist', None), 'literary_core', None)
        if core is None:
            return {}
        from app.creative.literary_core import authored
        rows = self.workbench.entries(p)
        projections = {}
        for note in authored(rows):
            details = note['literary']
            if details.get('kind') != 'clue':
                continue
            target = details.get('original_clue') or note['id']
            source.setdefault(target, {'title': details.get('title') or target, '_source': 'metadata/studio/reading.json'})
            card = core.card(p, note['id'], rows)
            projected = projections.setdefault(target, {'evidence': [], 'phases': [], 'introduced': [], 'resolved': [], 'record_ids': []})
            projected['record_ids'].append(note['id'])
            current = {(e.get('path'), e.get('revision'), e.get('start'), e.get('end'), e.get('quote')): e
                       for e in card['evidence_status']}
            for event in [note, *card['events']]:
                phase = event['literary'].get('phase', 'PLANNED')
                phase_chapters = []
                for index, raw in enumerate(event['literary'].get('evidence', [])):
                    checked = current.get((raw.get('path'), raw.get('revision'), raw.get('start'), raw.get('end'), raw.get('quote')), {})
                    chapter = by_id.get(checked.get('chapter_id'))
                    if chapter is None:
                        # Stale evidence still has an honest source chapter when
                        # the existing path->stable-ID service can resolve it.
                        try:
                            cid, _, _ = self.workbench.tools.chapter(p, raw['path'])
                            chapter = by_id.get(cid)
                        except ConsoleError:
                            continue
                    if chapter is None:
                        continue
                    located = bool(checked.get('current'))
                    projected['evidence'].append({'id': event['id'] + ':' + str(index), 'kind': 'literary',
                        'chapter': {**chapter, 'path': raw['path']}, 'exact': raw['quote'], 'located': located,
                        'source': 'metadata/studio/reading.json#' + event['id'],
                        'location': {'start': raw['start'], 'end': raw['end'], 'text': raw['quote'],
                                     'exact': raw['quote'], 'document_revision': raw['revision'], 'prefix': '', 'suffix': ''} if located else None})
                    if located:
                        phase_chapters.append(chapter)
                if phase_chapters and phase in {'PLACED', 'REINFORCED', 'MISDIRECTED', 'PARTIAL', 'RESOLVED'}:
                    projected['phases'].append(phase)
                    if phase == 'PLACED':
                        projected['introduced'].extend(phase_chapters)
                    elif phase == 'RESOLVED':
                        projected['resolved'].extend(phase_chapters)
            if not projected['phases'] and details.get('phase') in {'ABANDONED', 'INTENTIONALLY_OPEN'}:
                projected['plan_phase'] = details['phase']
        return projections

    def get(self, p):
        wb = self.workbench
        ws = wb.ws(p)
        _, local, etag = self._local(p)
        chapters, plans = self._chapters(p)
        by_id = {c['id']: c for c in chapters}
        by_number = {}
        for chapter in chapters:
            by_number.setdefault(chapter['number'], []).append(chapter)
        resolve = lambda value: self._resolve(value, by_id, by_number)
        ledger = ws.yaml_file('state/chapter-ledger.yaml').get('entries', [])
        committed = set()
        for entry in ledger:
            if not isinstance(entry, dict):
                continue
            chapter = resolve(entry.get('chapter_id') or entry.get('chapter'))
            if chapter:
                committed.add(chapter['id'])
        anchors = wb.knowledge.anchors(p)
        latest = max((c for c in chapters if c['has_prose'] or c['id'] in committed),
                     key=lambda c: c['position'], default=None)
        raw = ws.yaml_file('state/foreshadowing.yaml')
        values = raw.get('foreshadowing', raw.get('clues', raw.get('threads', {})))
        if isinstance(values, dict):
            source = {str(key): dict(value) for key, value in values.items() if isinstance(value, dict)}
        elif isinstance(values, list):
            source = {str(value['id']): dict(value) for value in values if isinstance(value, dict) and value.get('id')}
        else:
            source = {}
        # Chapter-card requests remain plans, including when the chapter has prose.
        planned = {}
        for card in plans:
            for kind, ids in card.get('foreshadowing', {}).items():
                for clue_id in ids:
                    planned.setdefault(clue_id, {}).setdefault(kind, []).append(card['id'])
                    source.setdefault(clue_id, {})
        literary = self._literary(p, source, by_id)
        threshold = local.get('threshold', 20)
        if not isinstance(threshold, int) or isinstance(threshold, bool) or not 1 <= threshold <= 1000:
            threshold = 20
        items = []
        for clue_id, value in source.items():
            annotations = local.get('items', {}).get(clue_id, {})
            if not isinstance(annotations, dict):
                annotations = {}
            literary_record = literary.get(clue_id, {})
            linked_anchors = [a for a in anchors if a.get('target_id') == clue_id and a.get('target_type') == 'clue']
            intro_ref = value.get('introduced_chapter_id') or value.get('introduced_chapter')
            introduced = resolve(intro_ref)
            background = intro_ref == 0 and any(isinstance(x, dict) and x.get('chapter') == 0 for x in ledger)
            intro_verified = bool(introduced and introduced['id'] in committed)
            valid_anchors = [a for a in linked_anchors if a.get('located') and a.get('chapter_id') in by_id]
            if not intro_verified and valid_anchors:
                introduced = min((by_id[a['chapter_id']] for a in valid_anchors), key=lambda c: c['position'])
                intro_verified = True
            if literary_record.get('introduced'):
                literary_intro = min(literary_record['introduced'], key=lambda c: c['position'])
                if not intro_verified or introduced['position'] > literary_intro['position']:
                    introduced = literary_intro
                intro_verified = True
            resolved = resolve(value.get('resolved_chapter_id') or value.get('resolved_chapter'))
            source_status = str(value.get('status', 'UNKNOWN')).upper()
            resolved_verified = bool(source_status in {'RESOLVED', 'PAID_OFF'} and resolved and resolved['id'] in committed)
            if literary_record.get('resolved') and intro_verified and literary_record.get('phases', [])[-1:] == ['RESOLVED']:
                resolved = max(literary_record['resolved'], key=lambda c: c['position'])
                resolved_verified = True
            actual_status = ('recovered' if resolved_verified else 'partial' if intro_verified and (source_status in {'PARTIAL', 'PARTIALLY_RESOLVED', 'PARTIALLY_PAID_OFF'} or literary_record.get('phases', [])[-1:] == ['PARTIAL'])
                             else 'planted' if intro_verified or background else 'planned')
            tracking = annotations.get('tracking_status')
            if tracking not in TRACKING:
                tracking = actual_status
            recovery = by_id.get(annotations.get('recovery_chapter_id', ''))
            plan_recoveries = [by_id[cid] for cid in planned.get(clue_id, {}).get('resolve', []) if cid in by_id]
            window = value.get('planned_window') or {}
            window_chapters = {key: resolve(window.get(key)) for key in ('earliest', 'preferred', 'latest')}
            window_invalid = bool(window_chapters['earliest'] and window_chapters['latest'] and window_chapters['earliest']['position'] > window_chapters['latest']['position'])
            preferred = resolve(value.get('planned_recovery_chapter_id') or window.get('preferred') or window.get('latest'))
            if preferred and not any(c['id'] == preferred['id'] for c in plan_recoveries):
                plan_recoveries.append(preferred)
            elapsed = (max(0, latest['position'] - introduced['position']) if latest and intro_verified and introduced
                       else latest['position'] + 1 if latest and background else None)
            archived = source_status in {'ABANDONED', 'DROPPED'} or literary_record.get('plan_phase') == 'ABANDONED'
            overdue = bool(elapsed is not None and elapsed > threshold and tracking != 'recovered' and not resolved_verified and not archived)
            evidence = list(literary_record.get('evidence', []))
            for anchor in linked_anchors:
                chapter = by_id.get(anchor.get('chapter_id'))
                if not chapter:
                    continue
                evidence.append({'id': anchor['id'], 'kind': 'anchor', 'chapter': {**chapter, 'path': anchor.get('path', chapter['path'])},
                                 'exact': anchor.get('anchor', {}).get('exact', ''), 'located': bool(anchor.get('located')),
                                 'source': 'metadata/studio/entity-anchors/' + anchor['id'] + '.json',
                                 'location': {'start': anchor.get('start'), 'end': anchor.get('end'),
                                              'text': anchor.get('anchor', {}).get('exact', ''),
                                              'exact': anchor.get('anchor', {}).get('exact', ''),
                                              'prefix': anchor.get('anchor', {}).get('prefix', ''),
                                              'suffix': anchor.get('anchor', {}).get('suffix', ''),
                                              'document_revision': anchor.get('document_revision', '')} if anchor.get('located') else None})
            for label, chapter in [('introduced', introduced if introduced and introduced['id'] in committed else None), ('recovered', resolved if resolved_verified and resolved['id'] in committed and source_status in {'RESOLVED', 'PAID_OFF'} else None)]:
                if chapter:
                    evidence.append({'id': label + ':' + chapter['id'], 'kind': 'committed', 'chapter': chapter,
                                     'located': False, 'location': None, 'exact': '', 'source': 'state/foreshadowing.yaml'})
            history = []
            for entry in value.get('writer_view', []):
                if isinstance(entry, dict):
                    chapter = resolve(entry.get('chapter_id') or entry.get('since_chapter'))
                    if chapter and chapter['id'] in committed:
                        history.append({'chapter': chapter, 'text': entry.get('text', ''), 'source': 'state/foreshadowing.yaml'})
            items.append({'id': clue_id, 'name': value.get('title') or value.get('name') or clue_id,
                          'source': value.get('_source') or ('state/foreshadowing.yaml' if value else 'outlines/chapters'),
                          'source_status': source_status, 'archived': archived,
                          'evidenced_status': actual_status, 'tracking_status': tracking,
                          'tracking_is_manual': bool(annotations.get('tracking_status')),
                          'introduced': introduced if intro_verified else None, 'background': background,
                          'unverified_introduction': resolve(intro_ref) if not intro_verified else None,
                          'actual_recovery': resolved if resolved_verified else None,
                          'recovery_chapter': recovery, 'planned_recovery': plan_recoveries,
                          'planned_introduction': [by_id[cid] for cid in planned.get(clue_id, {}).get('introduce', []) if cid in by_id],
                          'planned_window': window, 'planned_window_chapters': window_chapters,
                          'planned_window_invalid': window_invalid,
                          'planned_window_passed': bool(not window_invalid and latest and window_chapters['latest'] and latest['position'] > window_chapters['latest']['position'] and tracking != 'recovered' and not resolved_verified and not archived),
                          'elapsed_chapters': elapsed,
                          'overdue': overdue, 'overdue_by': max(0, elapsed - threshold) if overdue else 0,
                          'note': annotations.get('note', ''), 'updated_at': annotations.get('updated_at'),
                          'evidence': evidence, 'history': history,
                          'characters': value.get('known_by', []), 'literary_record_ids': literary_record.get('record_ids', [])})
        items.sort(key=lambda c: (not c['overdue'], -c['overdue_by'], -(c['elapsed_chapters'] or 0), c['name'], c['id']))
        counts = Counter(item['tracking_status'] for item in items if not item['archived'])
        return {'etag': etag, 'threshold': threshold, 'latest_chapter': latest,
                'chapters': chapters, 'clues': items,
                'volumes': [{key: row.get(key) for key in ('id', 'number', 'title')} for row in sorted(wb.tools.planning.rows(p, 'volume'), key=lambda v: v['number'])],
                'progress_incomplete': any(c['progress_unknown'] for c in chapters),
                'summary': {**{status: counts[status] for status in sorted(TRACKING)},
                            'overdue': sum(c['overdue'] for c in items), 'total': len(items)},
                'author_metadata_only': True, 'canon_modified': False}

    @staticmethod
    def _validate_changes(board, changes):
        ids = [change.clue_id for change in changes]
        if len(ids) != len(set(ids)):
            raise ConsoleError('同一次修改中不能重复选择同一伏笔', 422, code='CLUE_BOARD_INVALID_CHANGE')
        allowed = {row['id'] for row in board['clues']}
        chapters = {row['id'] for row in board['chapters']}
        for change in changes:
            if change.clue_id not in allowed:
                raise ConsoleError('伏笔不属于当前作品或已移除；未保存任何批量修改', 404, code='CLUE_BOARD_INVALID_TARGET')
            fields = change.model_fields_set - {'clue_id'}
            if not fields or fields == {'reset_tracking'} and not change.reset_tracking:
                raise ConsoleError('没有要保存的伏笔修改', 422, code='CLUE_BOARD_INVALID_CHANGE')
            if change.reset_tracking and 'tracking_status' in fields:
                raise ConsoleError('恢复来源状态不能同时提交人工状态', 422, code='CLUE_BOARD_INVALID_CHANGE')
            for name in ('tracking_status', 'recovery_chapter_id', 'note'):
                if name in fields and getattr(change, name) is None:
                    raise ConsoleError('不能将追踪字段保存为空值；清除章节请使用空字符串', 422, code='CLUE_BOARD_INVALID_CHANGE')
            if change.recovery_chapter_id and change.recovery_chapter_id not in chapters:
                raise ConsoleError('回收章节不属于当前作品；未保存任何批量修改', 422, code='CLUE_BOARD_INVALID_TARGET')

    @staticmethod
    def _apply_changes(value, changes):
        result = copy.deepcopy(value)
        updated_at = now()
        for change in changes:
            item = result.setdefault('items', {}).setdefault(change.clue_id, {})
            for name in ('tracking_status', 'recovery_chapter_id', 'note'):
                if name in change.model_fields_set:
                    item[name] = getattr(change, name)
            if change.reset_tracking:
                item.pop('tracking_status', None)
            item['updated_at'] = updated_at
        return result

    def update(self, p, body):
        wb = self.workbench
        ws = wb.tools.writable(p)
        with wb.lock, ws._save_lock:
            path, value, etag = self._local(p)
            if etag != body.etag:
                raise ConsoleError('伏笔看板已变化，请刷新后重试；没有覆盖其他修改', 409, code='CLUE_BOARD_CHANGED')
            fields = body.model_fields_set - {'etag'}
            if not fields:
                raise ConsoleError('没有要保存的伏笔看板修改', 422, code='CLUE_BOARD_INVALID_CHANGE')
            if body.clue_id is None and fields - {'threshold'}:
                raise ConsoleError('请选择当前作品中的伏笔', 422, code='CLUE_BOARD_INVALID_TARGET')
            if body.clue_id is not None:
                change = ClueBoardChange.model_validate(body.model_dump(exclude={'etag', 'threshold'}, exclude_unset=True))
                self._validate_changes(self.get(p), [change])
                value = self._apply_changes(value, [change])
            if 'threshold' in fields:
                if body.threshold is None:
                    raise ConsoleError('请选择逾期提醒章节数', 422, code='CLUE_BOARD_INVALID_CHANGE')
                value['threshold'] = body.threshold
            checkpoint(ws.root, BOARD_PATH, 'PRE_CLUE_BOARD_TRACKING')
            write(path, value)
            return self.get(p)

    def batch(self, p, body):
        """One explicit author confirmation, one snapshot and one atomic write.

        Validate every target before touching the overlay or revision history.
        Canon, source notes, State and manuscripts are never batch-write targets.
        """
        if body.confirm is not True:
            raise ConsoleError('请明确确认本次批量追踪修改', 409, code='CLUE_BOARD_CONFIRM_REQUIRED')
        wb = self.workbench
        ws = wb.tools.writable(p)
        with wb.lock, ws._save_lock:
            path, value, etag = self._local(p)
            if etag != body.etag:
                raise ConsoleError('伏笔看板已变化，请刷新后重试；未保存任何批量修改', 409, code='CLUE_BOARD_CHANGED')
            board = self.get(p)
            self._validate_changes(board, body.updates)
            updated = self._apply_changes(value, body.updates)
            checkpoint(ws.root, BOARD_PATH, 'PRE_CLUE_BOARD_BATCH')
            write(path, updated)
            return {**self.get(p), 'batch_summary': {'updated': len(body.updates), 'clue_ids': [change.clue_id for change in body.updates]}}
