"""Local V0.1 mechanics. Literary interpretation belongs to the project Skills.

Checkers audit evidence-bound claims, not unrestricted natural language. Final
requires separate semantic reviews of the exact final bytes.
"""
import argparse
import copy
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml_io as y
from model import SCHEMAS, FILE_SCHEMAS, MEMORY_KEYS, validate

ROOT = Path(__file__).resolve().parents[1]
REVIEW_KINDS = ['contract', 'continuity', 'character', 'scene_plot', 'style']


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def safe_path(root, relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError('Use root-relative portable paths')
    parts = relative.split('/')
    if any(p in ('', '.', '..') for p in parts):
        raise ValueError('Unsafe path')
    root = Path(root).resolve()
    candidate = root.joinpath(*parts)
    for parent in [candidate, *candidate.parents]:
        if parent == root:
            break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Symlink/junction not allowed')
    if not candidate.resolve().is_relative_to(root):
        raise ValueError('Path outside project')
    return candidate


def state_paths(root):
    paths = list(FILE_SCHEMAS)
    paths += ['characters/' + p.name for p in (root / 'state/characters').glob('*.yaml')]
    return sorted(paths)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('A story timestamp is required')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Story timestamps require an explicit UTC offset')
    return parsed


def validate_state(state):
    for relative, data in state.items():
        schema_name = 'character' if relative.startswith('characters/') else FILE_SCHEMAS.get(relative)
        if not schema_name:
            raise ValueError('Unsupported state target: ' + relative)
        validate(data, SCHEMAS['$defs'][schema_name], relative)
    current = state['current-story-state.yaml']
    chars = {v['id']: v for k, v in state.items() if k.startswith('characters/')}
    if len(chars) != sum(k.startswith('characters/') for k in state):
        raise ValueError('Duplicate character IDs')
    for relative, char in state.items():
        if relative.startswith('characters/') and relative != f"characters/{char['id']}.yaml":
            raise ValueError('Character filename and ID mismatch')
    def refs(values, table, field):
        if any(v not in table for v in values if v is not None):
            raise ValueError('Unknown reference in ' + field)
    locations = state['locations.yaml']['locations']
    items = state['items.yaml']['items']
    facts = state['knowledge-state.yaml']['facts']
    events = {e['id']: e for e in state['timeline.yaml']['events']}
    if len(events) != len(state['timeline.yaml']['events']):
        raise ValueError('Duplicate event IDs')
    refs(current['active_characters'] + [current['pov']['current_character']], chars, 'current characters')
    refs([current['location']['current']], locations, 'current location')
    refs(current['active_threads'], state['plot-threads.yaml']['threads'], 'active threads')
    refs(current['open_foreshadowing'], state['foreshadowing.yaml']['foreshadowing'], 'foreshadowing')
    refs(current['recent_events'], events, 'recent events')
    if current['project']['story_date'] is not None:
        timestamp(current['project']['story_date'])
    committed_time = timestamp(current['project']['story_date']) if current['project']['story_date'] else None
    chapter = current['project']['current_chapter']
    for event in events.values():
        if not event['id'] or event['chapter'] is None or event['chapter'] > chapter:
            raise ValueError('Timeline contains incomplete/future event')
        timestamp(event['story_time'])
        if committed_time and timestamp(event['story_time']) > committed_time:
            raise ValueError('Timeline event occurs after committed state time')
        refs(event['characters'], chars, 'event characters')
        refs([event['location']], locations, 'event location')
    for fact in facts.values():
        if fact['introduced_chapter'] is None or fact['introduced_chapter'] > chapter:
            raise ValueError('Fact introduced after committed chapter')
        reader_since=fact.get('reader_known_since_chapter')
        if reader_since is not None and reader_since>chapter:
            raise ValueError('Reader knowledge must already exist in committed chapters')
        if fact['public'] and (fact['public_since_chapter'] is None or fact['public_since_chapter'] > chapter
                               or not fact['public_story_time'] or committed_time and timestamp(fact['public_story_time']) > committed_time):
            raise ValueError('Public knowledge must already exist in committed state')
        for kind in ['known_by', 'suspected_by']:
            seen = set()
            for receipt in fact[kind]:
                actor = receipt['character_id']
                refs([actor], chars, kind)
                if actor in seen or receipt['acquired_chapter'] is None or receipt['acquired_chapter'] > chapter:
                    raise ValueError('Duplicate/future knowledge receipt')
                seen.add(actor)
                if receipt['acquired_chapter'] < fact['introduced_chapter']:
                    raise ValueError('Knowledge predates fact introduction')
                timestamp(receipt['story_time'])
                if current['project']['story_date'] and timestamp(receipt['story_time']) > timestamp(current['project']['story_date']):
                    raise ValueError('Knowledge acquisition is later than current state')
                refs([receipt['source_event']], events, 'knowledge source')
                if not receipt['source_event']:
                    raise ValueError('Knowledge source event required')
                event = events[receipt['source_event']]
                if event['chapter'] > receipt['acquired_chapter'] or timestamp(event['story_time']) > timestamp(receipt['story_time']):
                    raise ValueError('Knowledge source occurs after acquisition')
        refs(fact['false_beliefs'], chars, 'belief holder')
        for belief in fact['false_beliefs'].values():
            if belief['acquired_chapter'] > chapter:
                raise ValueError('Future belief receipt')
            timestamp(belief['story_time'])
            if committed_time and timestamp(belief['story_time']) > committed_time:
                raise ValueError('Belief occurs after committed state time')
            refs([belief['source_event']], events, 'belief source')
            if not belief['source_event']:
                raise ValueError('Belief source required')
            source = events[belief['source_event']]
            if source['chapter'] > belief['acquired_chapter'] or timestamp(source['story_time']) > timestamp(belief['story_time']):
                raise ValueError('Belief source occurs after acquisition')
    for actor, char in chars.items():
        refs([char['status']['location']], locations, 'character location')
        refs(char['inventory'], items, 'inventory')
        refs(char['relationships'], chars, 'character relationships')
        for kind, central in [('knows', 'known_by'), ('suspects', 'suspected_by')]:
            actual = {fid for fid, fact in facts.items() if any(r['character_id'] == actor for r in fact[central])}
            if set(char['knowledge'][kind]) != actual:
                raise ValueError('Knowledge projection mismatch: ' + actor + '/' + kind)
        refs(char['knowledge']['does_not_know'], facts, 'unknown facts')
        if set(char['knowledge']['knows']) & set(char['knowledge']['does_not_know']):
            raise ValueError('Contradictory knowledge projection')
    for relationship in state['relationships.yaml']['relationships'].values():
        refs(relationship['characters'], chars, 'relationship actors')
    for item in items.values():
        refs([item['holder']], chars, 'item holder')
        refs([item['location']], locations, 'item location')
    for faction in state['factions.yaml']['factions'].values():
        refs(faction['members'], chars, 'faction members')
    for row in state['foreshadowing.yaml']['foreshadowing'].values():
        refs(row['known_by'], chars, 'foreshadow knowers')
        window = [v for v in row['planned_window'].values() if v is not None]
        if window != sorted(window):
            raise ValueError('Foreshadow window reversed')
        if row['status'] == 'RESOLVED' and row['resolved_chapter'] is None:
            raise ValueError('Resolved foreshadow lacks chapter')
    for row in state['plot-threads.yaml']['threads'].values():
        refs(row['characters'], chars, 'thread actors')
    entries = state['chapter-ledger.yaml']['entries']
    if entries and [e['chapter'] for e in entries] != list(range(1, len(entries) + 1)):
        raise ValueError('Ledger chapter sequence invalid')


def load_state(root, locked=False):
    root = Path(root)
    if not locked and ((root / 'state/.commit.lock').exists() or (root / 'state/proposed/transaction.json').exists()):
        raise ValueError('State transaction pending; recover before reading')
    result = {name: y.read(safe_path(root, 'state/' + name)) for name in state_paths(root)}
    validate_state(result)
    if not locked and ((root / 'state/.commit.lock').exists() or (root / 'state/proposed/transaction.json').exists()):
        raise ValueError('Concurrent commit detected; retry after completion/recovery')
    return result


def eligible(view, actor, chapter, time):
    return (view['visibility'] == 'PUBLIC' or
            view['visibility'] == 'CHARACTER' and actor in view['known_by']) and (
                view['since_chapter'] is not None and view['since_chapter'] <= chapter) and (
                view['story_time'] is not None and timestamp(view['story_time']) <= time)


def context(root, plan, scene_id=None, materials=None):
    state = load_state(root)
    validate(plan, SCHEMAS['$defs']['plan'])
    current = state['current-story-state.yaml']
    actor = plan['pov']['character']
    if scene_id is not None and scene_id not in {s['id'] for s in plan['scenes']}:
        raise ValueError('Unknown disclosure scene')
    chars = {v['id']: v for k, v in state.items() if k.startswith('characters/')}
    if actor not in chars or plan['chapter']['number'] != current['project']['current_chapter'] + 1:
        raise ValueError('Missing POV or chapter is not the next chapter')
    cutoff = current['project']['current_chapter']
    time = timestamp(current['project']['story_date'])
    if timestamp(plan['setting']['story_time']) < time:
        raise ValueError('Plan time precedes committed state; explicit flashback needs a separate scoped plan')
    def views(rows):
        return [v['text'] for v in rows if eligible(v, actor, cutoff, time)]
    known, suspicion, beliefs, disclosures = [], [], [], []
    for fid, fact in state['knowledge-state.yaml']['facts'].items():
        def acquired(kind):
            return any(r['character_id'] == actor and r['acquired_chapter'] <= cutoff and timestamp(r['story_time']) <= time
                       for r in fact[kind])
        unrestricted = fact['restricted_until'] is None or plan['chapter']['number'] >= fact['restricted_until']
        public = (fact['public'] and fact['public_since_chapter'] is not None and fact['public_since_chapter'] <= cutoff
                  and fact['public_story_time'] is not None and timestamp(fact['public_story_time']) <= time)
        if unrestricted and (acquired('known_by') or public):
            reader_since = fact.get('reader_known_since_chapter')
            known.append({'fact_id': fid, 'text': fact['canonical_truth'], 'character_knows':True,
                          'reader_knows':None if reader_since is None else reader_since <= cutoff})
        # Suspecting truth does not authorize sending the author's answer.
        if acquired('suspected_by'):
            suspicion.append({'instruction': '存在怀疑；只采用明确获准的角色假设文本，不推定真相'})
        belief = fact['false_beliefs'].get(actor)
        if belief and belief['acquired_chapter'] <= cutoff and timestamp(belief['story_time']) <= time:
            beliefs.append({'text': belief['belief']})
        for disclosure in plan['approved_disclosures']:
            if (unrestricted and disclosure['fact_id'] == fid and disclosure['character_id'] == actor
                    and disclosure['scene_id'] == scene_id and disclosure['author_approved']):
                target=disclosure.get('audience','CHARACTER')
                disclosures.append({'text': fact['canonical_truth'], 'fact_id': fid, 'scene_id': scene_id,
                                    'audience':target,'character_knows_before_scene':acquired('known_by') or public,
                                    'source_event': disclosure['source_event'],
                                    'instruction': '本场允许向读者披露；这不授予 POV 角色内心知识。' if target=='READER' else '先写本场信息获得事件，再使用此知识'})
    active = set(current['active_characters']) | {actor}
    scene_rows = [s for s in plan['scenes'] if scene_id is None or s['id'] == scene_id]
    for scene in scene_rows:
        if any(c not in chars for c in scene['characters']):
            raise ValueError('Unknown scene character')
        active.update(scene['characters'])
    location = plan['setting']['location']
    if location not in state['locations.yaml']['locations']:
        raise ValueError('Unknown plan location')
    contract = y.read(root / 'settings/canon-contract.yaml')
    validate(contract, SCHEMAS['$defs']['contract'])
    style = y.read(root / 'settings/style-profile.yaml')
    validate(style, SCHEMAS['$defs']['style'])
    char = chars[actor]
    materials = materials or {'global_rules': [], 'recent_summaries': [], 'previous_scene': []}
    for key, rows in materials.items():
        if key not in ['global_rules', 'recent_summaries', 'previous_scene']:
            raise ValueError('Unknown context material kind')
        validate(rows, {'type': 'array', 'items': SCHEMAS['$defs']['view']})
    packet = {
        'global_rules': ['Canon 优先；禁止补写未知事实；只能使用本包的角色信息；检查不改稿。'] + views(materials.get('global_rules', [])),
        'canon_contract': {level: [text for r in contract[level] for text in views(r['writer_view'])]
                           for level in ['hard', 'strong', 'soft', 'preferences']},
        'current_story_state': {'chapter': plan['chapter']['number'], 'volume': plan['chapter']['volume'],
                                'scene': scene_id, 'story_time': plan['setting']['story_time'], 'location': location},
        'pov_character': {'id': actor, 'condition': char['status']['physical_condition'],
                          'limitations': char['status']['limitations'], 'view': views(char['writer_view'])},
        'pov_knowledge': {'known': known, 'suspicions': suspicion, 'beliefs': beliefs, 'scene_disclosures': disclosures},
        'active_characters': [{'id': cid, 'view': views(chars[cid]['writer_view'])} for cid in sorted(active) if cid != actor],
        'active_location': views(state['locations.yaml']['locations'][location]['writer_view']),
        'relationships': [text for r in state['relationships.yaml']['relationships'].values()
                          if actor in r['characters'] and set(r['characters']) & active for text in views(r['writer_view'])],
        'timeline': [text for e in state['timeline.yaml']['events'] if e['chapter'] <= cutoff
                     and timestamp(e['story_time']) <= time and (actor in e['characters'] or e['id'] in current['recent_events'])
                     for text in views(e['writer_view'])],
        'plot_threads': [text for tid, row in state['plot-threads.yaml']['threads'].items()
                         if tid in current['active_threads'] for text in views(row['writer_view'])],
        'foreshadowing': [text for fid, row in state['foreshadowing.yaml']['foreshadowing'].items()
                          if fid in current['open_foreshadowing'] for text in views(row['writer_view'])],
        'recent_summaries': views(materials.get('recent_summaries', [])),
        'previous_scene': views(materials.get('previous_scene', [])),
        'chapter_plan': {'view': views(plan['writer_view']), 'scenes': [
            {'id': s['id'], 'location': s['location'], 'characters': s['characters'], 'view': views(s['writer_view'])} for s in scene_rows]},
        'style_rules': style,
        'boundary': '被排除的事实不能自行读取或推断成已知；本包仅是信息输入边界，不是进程访问控制。'}
    from knowledge_isolation import writer_packet
    return writer_packet(packet, root, state, plan, scene_id)


def issue(category, claim, reason, severity='HARD'):
    return {'category': category, 'character': claim.get('character'), 'severity': severity,
            'rule': category, 'location': claim['location'], 'evidence': claim['evidence'],
            'explanation': reason, 'reason': reason, 'suggested_fix': '在 REVISE 修复或补齐已授权且有证据的剧情过渡；重新检查。',
            'fix_direction': '保持已有事实和 POV，补行动/获得信息的过程。'}


def role_context(root, plan, audience='WRITER', scene_id=None, materials=None, body=''):
    if audience=='WRITER': return context(root,plan,scene_id,materials)
    if audience not in ['AUTHOR','CHECKER']: raise ValueError('Unknown context audience')
    from knowledge_isolation import author_packet, checker_packet
    state=load_state(root)
    characters={p.stem:y.read(p) for p in (root/'characters').glob('*.yaml')}
    author=author_packet(root,state,plan,y.read(root/'settings/canon-contract.yaml'),characters,
                        {fid:fact.get('reader_known_since_chapter') for fid,fact in state['knowledge-state.yaml']['facts'].items()})
    return author if audience=='AUTHOR' else checker_packet(author,body)


def check(root, body_path, claims, kind, plan=None):
    state = load_state(root)
    body = Path(body_path).read_bytes()
    text = body.decode('utf-8-sig')
    if claims.get('body_sha256') != digest(body):
        raise ValueError('Claims do not match body bytes')
    current = state['current-story-state.yaml']
    chars = {v['id']: v for k, v in state.items() if k.startswith('characters/')}
    problems = []
    chapter_number = (plan or {}).get('chapter', {}).get('number', current['project']['current_chapter'] + 1)
    knowledge_time = timestamp(current['project']['story_date'])
    known = {cid: set() for cid in chars}
    for fid, fact in state['knowledge-state.yaml']['facts'].items():
        public = (fact['public'] and fact['public_since_chapter'] is not None
                  and fact['public_since_chapter'] <= current['project']['current_chapter']
                  and fact['public_story_time'] is not None and timestamp(fact['public_story_time']) <= knowledge_time)
        for cid in chars:
            if public or any(r['character_id'] == cid and timestamp(r['story_time']) <= knowledge_time for r in fact['known_by']):
                known[cid].add(fid)
    last_time = timestamp(current['project']['story_date']) if current['project']['story_date'] else None
    recognized = ['action', 'knowledge', 'acquire', 'appearance', 'time', 'location', 'age', 'item', 'ability',
                  'relationship', 'event', 'decision', 'dialogue', 'emotion', 'world', 'sequence']
    for claim in claims.get('claims', []):
        if not isinstance(claim.get('location'), str) or not claim.get('evidence'):
            raise ValueError('Every claim needs location and verbatim evidence')
        # Paragraph anchors are one-based non-empty paragraphs; same quote elsewhere is insufficient.
        match = re.fullmatch(r'p([1-9][0-9]*)', claim['location'])
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text.strip())]
        if not match or int(match[1]) > len(paragraphs) or claim['evidence'] not in paragraphs[int(match[1])-1]:
            raise ValueError('Claim evidence not present at location')
        category = claim.get('type')
        if category not in recognized:
            raise ValueError('Unknown claim type')
        cid = claim.get('character')
        char = chars.get(cid)
        if cid and char is None:
            raise ValueError('Unknown character in claims')
        for field in ['supporting_evidence', 'travel_evidence', 'transfer_evidence', 'acquisition_evidence']:
            if claim.get(field) and claim[field] not in text:
                raise ValueError('Supporting evidence absent from chapter')
        if category == 'action' and char:
            blocked = set(claim.get('required_capabilities', [])) & set(char['status']['limitations'])
            if blocked:
                problems.append(issue('injury', claim, '伤势限制与动作冲突：' + ','.join(sorted(blocked))))
        if category == 'appearance' and char and not char['status']['alive'] and not claim.get('representation') in ['memory', 'recording', 'ghost_authorized']:
            problems.append(issue('alive', claim, '已死亡人物正常出现'))
        if category == 'acquire':
            approved = any(d['author_approved'] and d['character_id'] == cid and d['fact_id'] == claim.get('fact_id')
                           and d.get('audience','CHARACTER') in ['CHARACTER','BOTH']
                           and d['scene_id'] == claim.get('scene_id') and d['source_event'] == claim.get('source_event')
                           for d in (plan or {}).get('approved_disclosures', []))
            if not approved:
                problems.append(issue('knowledge', claim, '未批准的信息获得事件'))
            else:
                known[cid].add(claim['fact_id'])
        if category == 'knowledge':
            fid = claim.get('fact_id')
            fact = state['knowledge-state.yaml']['facts'].get(fid)
            if fact is None:
                raise ValueError('Unknown fact')
            stance = claim.get('stance', 'knows')
            if stance not in ['knows', 'suspects', 'believes']:
                raise ValueError('Unknown knowledge stance')
            allowed = (fid in known.get(cid, set()) if stance == 'knows' else
                       fid in chars[cid]['knowledge']['suspects'] if stance == 'suspects' else
                       cid in fact['false_beliefs'] or fid in known.get(cid, set()))
            if not allowed:
                problems.append(issue('knowledge', claim, '角色没有此知识/怀疑/信念的获得记录'))
            if stance == 'knows' and fact['restricted_until'] is not None and chapter_number < fact['restricted_until']:
                problems.append(issue('knowledge', claim, '该真相尚未到允许揭示的章节'))
        if category == 'time':
            now = timestamp(claim['story_time'])
            if last_time and 'elapsed_minutes' in claim and now != last_time + timedelta(minutes=claim['elapsed_minutes']):
                problems.append(issue('time', claim, '经过时长与明确时间不一致'))
            place = claim.get('location_id') or current['location']['current']
            hours = state['locations.yaml']['locations'].get(place, {}).get('daylight_hours', [])
            if claim.get('daylight') is True and hours and now.hour not in hours:
                problems.append(issue('time', claim, '此地已定昼夜条件不支持该时刻的日光'))
            if last_time and now < last_time and not claim.get('flashback'):
                problems.append(issue('time', claim, '无回忆标识的时间倒退'))
            last_time = now
        if category == 'location' and char and claim.get('location_id') != char['status']['location'] and not claim.get('travel_evidence'):
            problems.append(issue('location', claim, '地点改变缺少移动依据', 'STRONG'))
        if category == 'age' and char and claim.get('age') != char['status']['age']:
            problems.append(issue('age', claim, '年龄与正式状态冲突'))
        if category == 'item' and char and claim.get('item_id') not in char['inventory'] and not claim.get('transfer_evidence'):
            problems.append(issue('item', claim, '使用不在持有记录中的道具', 'STRONG'))
        if category == 'ability' and char and claim.get('ability_id') not in char['abilities'] and not claim.get('acquisition_evidence'):
            problems.append(issue('ability', claim, '能力缺少已建立的来源', 'STRONG'))
        if category == 'sequence' and claim.get('chapter') != current['project']['current_chapter'] + 1:
            problems.append(issue('sequence', claim, '章节顺序错误'))
        if category in ['decision', 'dialogue', 'emotion', 'relationship'] and claim.get('deviation') and not claim.get('supporting_evidence'):
            problems.append(issue(category, claim, '改变缺少剧情支撑；需要人物判断，不能直接认定 OOC', 'SOFT'))
        if category in ['event', 'world'] and claim.get('contradiction'):
            problems.append(issue(category, claim, claim['contradiction']))
    if kind == 'continuity':
        selected = [i for i in problems if i['category'] not in ['decision', 'dialogue', 'emotion']]
    elif kind == 'character':
        selected = [i for i in problems if i['category'] in ['knowledge', 'decision', 'dialogue', 'emotion', 'relationship']]
    elif kind == 'contract':
        contract = y.read(root / 'settings/canon-contract.yaml')
        validate(contract, SCHEMAS['$defs']['contract'])
        selected = []
        # Inviolable baseline always applies, even if author leaves contract empty.
        selected.extend(i for i in problems if i['category'] in ['knowledge', 'alive', 'injury', 'time', 'sequence'])
        for level in ['hard', 'strong', 'soft', 'preferences']:
            for rule in contract[level]:
                matching = [i for i in problems if i['category'] == rule['check']]
                for found in matching:
                    found = copy.deepcopy(found)
                    found.update(rule=rule['id'], severity=level.upper().rstrip('S') if level == 'preferences' else level.upper())
                    selected.append(found)
                if rule['check'] in [None, 'manual']:
                    selected.append({'category': 'manual_rule', 'severity': 'SOFT', 'rule': rule['id'], 'location': 'whole_chapter',
                                     'evidence': None, 'explanation': '该规则必须由 Skill 逐条语义审查；机器未宣告通过',
                                     'suggested_fix': '补充语义审查证据'})
    else:
        raise ValueError('Checker kind unsupported')
    result = 'FAIL' if any(i['severity'] in ['HARD', 'STRONG'] for i in selected) else 'WARN' if selected else 'PASS'
    return {'result': result, 'body_sha256': digest(body), 'coverage': 'STRUCTURED_CLAIMS_ONLY',
            'semantic_review_required': True, 'violations' if kind == 'contract' else 'issues': selected}


def authority_digest(root):
    files = {}
    for folder in ['settings', 'outlines']:
        for path in (root / folder).rglob('*'):
            if path.is_file() and path.name != '.gitkeep':
                relative = path.relative_to(root).as_posix()
                files[relative] = digest(safe_path(root, relative).read_bytes())
    return digest(files)


def final_witness(root, body_relative, chapter, reviews, locked=False):
    body_hash = digest(safe_path(root, body_relative).read_bytes())
    if set(reviews) != set(REVIEW_KINDS):
        raise ValueError('All five final semantic reviews required')
    evidence = {}
    for kind, relative in reviews.items():
        path = safe_path(root, relative)
        report = y.read(path)
        if (report.get('body_sha256') != body_hash or report.get('result') != 'PASS'
                or report.get('coverage') != 'SEMANTIC_REVIEW' or not report.get('reviewer')
                or not report.get('reviewed_rules') or not report.get('findings_resolved')):
            raise ValueError('Final review missing, stale, failed or only mechanical: ' + kind)
        evidence[kind] = {'path': relative, 'sha256': digest(path.read_bytes())}
    return {'result': 'PASS', 'chapter': chapter, 'body_path': body_relative, 'body_sha256': body_hash, 'reviews': evidence,
            'state_sha256': digest(load_state(root, locked=locked)), 'authority_sha256': authority_digest(root)}


def verify_final(root, witness, locked=False, check_state=True):
    actual = final_witness(root, witness['body_path'], witness['chapter'],
                           {k: v['path'] for k, v in witness['reviews'].items()}, locked=locked)
    if not check_state:
        actual['state_sha256'] = witness['state_sha256']
    if actual != witness:
        raise ValueError('Final witness no longer matches body/reviews')


def extract(root, witness, observations, locked=False):
    verify_final(root, witness, locked=locked)
    if set(observations) != set(MEMORY_KEYS + ['operations']):
        raise ValueError('Memory categories/operations incomplete')
    body = safe_path(root, witness['body_path']).read_text(encoding='utf-8-sig')
    for rows in observations.values():
        if not isinstance(rows, list):
            raise ValueError('Memory records must be lists')
        for row in rows:
            if not isinstance(row, dict) or not row.get('evidence') or row['evidence'] not in body:
                raise ValueError('Memory change lacks body evidence')
    return {'chapter': witness['chapter'], 'body_sha256': witness['body_sha256'], **copy.deepcopy(observations)}


def allowed_target(relative):
    if relative in FILE_SCHEMAS and relative != 'chapter-ledger.yaml':
        return True
    return bool(re.fullmatch(r'characters/[A-Za-z0-9_-]+\.yaml', relative))


def apply_operations(state, operations):
    state = copy.deepcopy(state)
    paths = set()
    for operation in operations:
        relative, pointer = operation['file'], operation['pointer']
        if not allowed_target(relative) or not pointer.startswith('/') or '~' in pointer:
            raise ValueError('State-only targets and simple JSON pointers required')
        if relative == 'current-story-state.yaml' and pointer.startswith(('/hard_constraints', '/project/title', '/project/genre')):
            raise ValueError('Author canon/configuration cannot be changed by memory extraction')
        if relative == 'knowledge-state.yaml' and (pointer == '/facts' or pointer.endswith('/canonical_truth') or len(pointer.split('/')) == 3 and pointer.split('/')[-1] in state[relative]['facts']):
            raise ValueError('Established canonical truth cannot be rewritten by memory extraction')
        identity = relative + pointer
        if identity in paths:
            raise ValueError('Duplicate patch target')
        paths.add(identity)
        if relative not in state:
            if pointer != '/' or operation.get('before') is not None:
                raise ValueError('New file requires whole-document creation')
            state[relative] = copy.deepcopy(operation['after'])
            continue
        if pointer == '/':
            raise ValueError('Existing whole-file replacement forbidden')
        keys = pointer[1:].split('/')
        cursor = state[relative]
        for key in keys[:-1]:
            cursor = cursor[int(key)] if isinstance(cursor, list) else cursor[key]
        key = int(keys[-1]) if isinstance(cursor, list) else keys[-1]
        if isinstance(cursor,list) and (key < 0 or key > len(cursor)):
            raise ValueError('List patch index out of bounds')
        present = key in cursor if isinstance(cursor, dict) else 0 <= key < len(cursor)
        if (cursor[key] if present else None) != operation.get('before'):
            raise ValueError('Patch before-value mismatch')
        if isinstance(cursor,list) and key == len(cursor):cursor.append(copy.deepcopy(operation['after']))
        else:cursor[key] = copy.deepcopy(operation['after'])
    return state


def propose(root, witness, extraction, proposal_id):
    verify_final(root, witness)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', proposal_id):
        raise ValueError('Invalid proposal ID')
    state = load_state(root)
    if extraction['chapter'] != witness['chapter'] or extraction['body_sha256'] != witness['body_sha256']:
        raise ValueError('Extraction is not from this final chapter')
    validated_extraction = extract(root, witness, {k: extraction[k] for k in MEMORY_KEYS + ['operations']})
    if extraction != validated_extraction:
        raise ValueError('Unexpected extraction fields')
    proposal = {'proposal_id': proposal_id, 'base_sha256': digest(state), 'final': witness, 'extraction': extraction}
    path = safe_path(root, 'state/proposed/' + proposal_id + '.yaml')
    if path.exists():
        raise ValueError('Proposal ID already exists')
    y.write(path, proposal)
    return proposal


def candidate(root, proposal, locked=False):
    verify_final(root, proposal['final'], locked=locked)
    state = load_state(root, locked=locked)
    if digest(state) != proposal['base_sha256']:
        raise ValueError('Stale proposal: committed state changed')
    chapter = proposal['final']['chapter']
    if chapter != state['current-story-state.yaml']['project']['current_chapter'] + 1:
        raise ValueError('State commit must be next chapter')
    extraction = proposal['extraction']
    extract(root, proposal['final'], {k: extraction[k] for k in MEMORY_KEYS + ['operations']}, locked=locked)
    if extraction['body_sha256'] != proposal['final']['body_sha256'] or extraction['chapter'] != chapter:
        raise ValueError('Wrong extraction provenance')
    updated = apply_operations(state, extraction['operations'])
    old_current = state['current-story-state.yaml']
    current = updated['current-story-state.yaml']
    if (current['project']['title'] != old_current['project']['title']
            or current['project']['genre'] != old_current['project']['genre']
            or current['hard_constraints'] != old_current['hard_constraints']):
        raise ValueError('Memory extraction cannot replace author canon through a parent pointer')
    if current['revision'] != old_current['revision'] or current['project']['current_chapter'] != old_current['project']['current_chapter']:
        raise ValueError('Revision/chapter progression is owned by commit, not extraction')
    current['revision'] += 1
    current['project']['current_chapter'] = chapter
    validate_state(updated)
    return updated


def verify_diff_review(root, proposal):
    relative = 'state/proposed/' + proposal['proposal_id'] + '.review.yaml'
    path = safe_path(root, relative)
    review = y.read(path)
    targets = [o['file'] + o['pointer'] for o in proposal['extraction']['operations']]
    if (review.get('result') != 'PASS' or review.get('coverage') != 'SEMANTIC_DIFF_REVIEW'
            or not review.get('reviewer') or review.get('proposal_sha256') != digest(proposal)
            or review.get('verified_operations') != targets or not review.get('extraction_complete')):
        raise ValueError('Proposed Diff semantic review missing/stale/incomplete')
    return {'path': relative, 'sha256': digest(path.read_bytes())}


def validate_proposal(root, proposal):
    updated = candidate(root, proposal)
    review = verify_diff_review(root, proposal)
    receipt = {'result': 'PASS', 'proposal_sha256': digest(proposal), 'base_sha256': proposal['base_sha256'],
               'candidate_sha256': digest(updated), 'final_sha256': digest(proposal['final']), 'diff_review': review}
    y.write(root / 'state/proposed' / (proposal['proposal_id'] + '.validation.yaml'), receipt)
    return receipt


def commit(root, proposal, receipt, fail_after=None):
    root = Path(root)
    ledger = load_state(root)['chapter-ledger.yaml']
    existing = [e for e in ledger['entries'] if e['proposal_id'] == proposal['proposal_id']]
    if existing:
        if (existing[0]['body_sha256'] == proposal['final']['body_sha256']
                and existing[0]['chapter'] == proposal['final']['chapter']
                and existing[0]['proposal_sha256'] == digest(proposal)
                and receipt.get('proposal_sha256') == digest(proposal)):
            verify_final(root, proposal['final'], check_state=False)
            if receipt.get('diff_review') != verify_diff_review(root, proposal):
                raise ValueError('Repeated commit review changed')
            return {'result': 'PASS', 'action': 'ALREADY_COMMITTED'}
        raise ValueError('Proposal ID reused with different chapter')
    lock = root / 'state/.commit.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(descriptor)
    journal = root / 'state/proposed/transaction.json'
    try:
        updated = candidate(root, proposal, locked=True)
        expected = {'result': 'PASS', 'proposal_sha256': digest(proposal), 'base_sha256': proposal['base_sha256'],
                    'candidate_sha256': digest(updated), 'final_sha256': digest(proposal['final']),
                    'diff_review': verify_diff_review(root, proposal)}
        if expected != receipt:
            raise ValueError('Validation receipt missing/tampered/stale')
        now = datetime.now(timezone.utc).isoformat()
        updated['chapter-ledger.yaml']['last_commit'] = now
        updated['chapter-ledger.yaml']['entries'].append({'chapter': proposal['final']['chapter'],
            'body_sha256': proposal['final']['body_sha256'], 'proposal_id': proposal['proposal_id'],
            'proposal_sha256': digest(proposal),
            'committed_at': now, 'revision': updated['current-story-state.yaml']['revision']})
        validate_state(updated)
        # Prepare a write-ahead rollback journal. Ledger is installed last.
        originals = {relative: (safe_path(root, 'state/' + relative).read_text(encoding='utf-8')
                               if safe_path(root, 'state/' + relative).exists() else None) for relative in updated}
        journal.write_text(json.dumps({'originals': originals}, ensure_ascii=False, indent=2), encoding='utf-8')
        order = sorted(k for k in updated if k != 'chapter-ledger.yaml') + ['chapter-ledger.yaml']
        for index, relative in enumerate(order, 1):
            path = safe_path(root, 'state/' + relative)
            temporary = path.with_suffix('.yaml.next')
            y.write(temporary, updated[relative])
            os.replace(temporary, path)
            if fail_after == index:
                raise OSError('Injected interrupted commit')
        journal.unlink()
        return {'result': 'PASS', 'action': 'COMMITTED', 'chapter': proposal['final']['chapter']}
    except BaseException:
        if journal.exists():
            rollback(root)
        raise
    finally:
        if lock.exists():
            lock.unlink()


def rollback(root):
    root = Path(root)
    journal = root / 'state/proposed/transaction.json'
    if not journal.exists():
        raise ValueError('No journal; inspect stale lock manually before removal')
    originals = json.loads(journal.read_text(encoding='utf-8'))['originals']
    for relative, contents in originals.items():
        if relative not in FILE_SCHEMAS and not allowed_target(relative):
            raise ValueError('Invalid rollback target')
        path = safe_path(root, 'state/' + relative)
        if contents is None:
            if path.exists():
                path.unlink()
        else:
            temporary = path.with_suffix('.yaml.rollback')
            temporary.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(contents, encoding='utf-8')
            os.replace(temporary, path)
        leftover = path.with_suffix('.yaml.next')
        if leftover.exists():
            leftover.unlink()
    journal.unlink()
    lock = root / 'state/.commit.lock'
    if lock.exists():
        lock.unlink()


def status(root):
    state = load_state(root)
    current = state['current-story-state.yaml']
    threads = state['plot-threads.yaml']['threads']
    foreshadow = state['foreshadowing.yaml']['foreshadowing']
    return {'Project': current['project']['title'], 'Volume': current['project']['current_volume'],
            'Chapter': current['project']['current_chapter'], 'Current POV': current['pov']['current_character'],
            'Current Location': current['location']['current'], 'Story Time': current['project']['story_date'],
            'Active Characters': current['active_characters'],
            'Open Plot Threads': [k for k, v in threads.items() if v['status'] not in ['RESOLVED', 'DROPPED']],
            'Open Foreshadowing': [k for k, v in foreshadow.items() if v['status'] not in ['RESOLVED', 'ABANDONED']],
            'Canon Warnings': current['warnings'], 'Last State Commit': state['chapter-ledger.yaml']['last_commit'],
            'Pending State Diff': [p.name for p in (root / 'state/proposed').glob('*.yaml')
                                   if not p.name.endswith(('.validation.yaml', '.review.yaml')) and p.stem not in
                                   {e['proposal_id'] for e in state['chapter-ledger.yaml']['entries']}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['status', 'validate-state', 'recover']:
        sub.add_parser(name)
    command = sub.add_parser('context')
    command.add_argument('--plan', required=True); command.add_argument('--scene'); command.add_argument('--materials')
    command.add_argument('--audience',choices=['WRITER','AUTHOR','CHECKER'],default='WRITER')
    command.add_argument('--body')
    command = sub.add_parser('check')
    command.add_argument('--kind', choices=['contract', 'continuity', 'character'], required=True)
    command.add_argument('--body', required=True); command.add_argument('--claims', required=True); command.add_argument('--plan')
    command = sub.add_parser('final')
    command.add_argument('--body', required=True); command.add_argument('--chapter', type=int, required=True); command.add_argument('--reviews', required=True)
    command = sub.add_parser('extract')
    command.add_argument('--final', required=True); command.add_argument('--observations', required=True)
    command = sub.add_parser('propose')
    command.add_argument('--final', required=True); command.add_argument('--extraction', required=True); command.add_argument('--id', required=True)
    for name in ['validate-proposal', 'commit']:
        command = sub.add_parser(name); command.add_argument('--proposal', required=True)
        if name == 'commit': command.add_argument('--receipt', required=True)
    parser.add_argument('--output', help='Root-relative output artifact, never a formal state target')
    args = parser.parse_args()
    root = args.root.resolve()
    read = lambda relative: y.read(safe_path(root, relative))
    if args.command == 'status':
        result = status(root)
        if args.output:
            raise ValueError('Status uses text output')
        for key, value in result.items(): print(f'{key}: {value}')
        return
    elif args.command == 'validate-state': load_state(root); result = {'result': 'PASS'}
    elif args.command == 'recover': rollback(root); result = {'result': 'PASS', 'action': 'ROLLED_BACK'}
    elif args.command == 'context': result = role_context(root, read(args.plan), args.audience,args.scene,
        read(args.materials) if args.materials else None,safe_path(root,args.body).read_text(encoding='utf-8-sig') if args.body else '')
    elif args.command == 'check': result = check(root, safe_path(root, args.body), read(args.claims), args.kind, read(args.plan) if args.plan else None)
    elif args.command == 'final': result = final_witness(root, args.body, args.chapter, read(args.reviews))
    elif args.command == 'extract': result = extract(root, read(args.final), read(args.observations))
    elif args.command == 'propose': result = propose(root, read(args.final), read(args.extraction), args.id)
    elif args.command == 'validate-proposal': result = validate_proposal(root, read(args.proposal))
    elif args.command == 'commit': result = commit(root, read(args.proposal), read(args.receipt))
    if args.output:
        if not args.output.startswith(('reviews/', 'state/proposed/')):
            raise ValueError('Output artifacts belong in reviews/ or state/proposed/')
        y.write(safe_path(root, args.output), result)
    else:
        print(y.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as error:
        print('FAIL: ' + str(error))
        raise SystemExit(1)
