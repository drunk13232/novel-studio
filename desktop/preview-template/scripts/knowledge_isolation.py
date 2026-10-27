"""V0.6 role boundary. Author text never doubles as a Writer instruction.

Matching secrets is a backstop, not a Chinese semantic classifier. Free-form
Writer views need an explicit, hash-bound safety review before execution.
"""
import hashlib
import json
import re


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def hidden_texts(state, plan, allowed):
    hidden = []
    for fid, fact in state['knowledge-state.yaml']['facts'].items():
        if fid not in allowed:
            hidden.append(fact.get('canonical_truth'))
    for name, row in state.items():
        if name.startswith('characters/'):
            hidden.extend(strings(row.get('secrets', {})))
    for row in state['foreshadowing.yaml']['foreshadowing'].values():
        hidden.extend(strings(row.get('intended_payoff')))
    hidden.extend(strings(plan.get('must_not_include', [])))
    # Authorized facts are released once, deliberately, even if also stored as secrets.
    authorized = {state['knowledge-state.yaml']['facts'][fid]['canonical_truth'] for fid in allowed}
    return [s for s in hidden if s and s not in authorized]


def assert_no_hidden(value, hidden):
    for text in strings(value):
        if any(secret in text for secret in hidden):
            raise ValueError('Writer 输入含未授权内容；请由 Planner 重建安全视图（详情仅在 Author View 核查）')


def writer_packet(packet, root, state, plan, scene_id):
    allowed = {f['fact_id'] for f in packet['pov_knowledge']['known'] + packet['pov_knowledge']['scene_disclosures']}
    hidden = hidden_texts(state, plan, allowed)
    assert_no_hidden(packet, hidden)
    # Do not pass prohibitions containing a secret as "safe" chapter directions.
    # Reject the whole source row, never redact a name and preserve the hint.
    for section in ['chapter_plan', 'foreshadowing', 'active_characters', 'pov_character', 'canon_contract']:
        if any(re.search(r'不要.{0,24}(?:暗示|透露|揭露)|不得.{0,24}(?:暗示|透露|揭露)|不能让.{0,24}知道', t)
               for t in strings(packet[section])):
            raise ValueError('Writer view 含禁止性披露描述；请改为正向可用信息')
    packet.update(context_version='0.6', audience='WRITER', project_id=root.name,
                  state_sha256=sha(state), plan_sha256=sha(plan))
    packet['boundary'] = '仅使用本包；新增知识先写本场获得事件。缺项返回 NEEDS_CONTEXT。'
    packet['disclosure_scope'] = {'character': plan['pov']['character'], 'scene': scene_id,
                                 'chapter': plan['chapter']['number']}
    packet['packet_sha256'] = sha(packet)
    return packet


def require_safe_review(packet, review):
    """Semantic authorization is specific to bytes/project/POV/state, not a sticky flag."""
    expected = {k: packet[k] for k in ['project_id', 'packet_sha256', 'state_sha256', 'plan_sha256']}
    if (review.get('audience') != 'WRITER' or review.get('result') != 'PASS'
            or review.get('coverage') != 'WRITER_SAFETY_REVIEW'
            or not review.get('reviewer') or any(review.get(k) != v for k, v in expected.items())):
        raise ValueError('需要绑定当前包哈希的 Writer Safety Review；旧 Context 或普通审稿不能代替')


SAFE_FIXES = {
    'UNSUPPORTED_POV': '删除该段未经当前 POV 支持的推断；仅使用 Writer View 中的信息。',
    'KNOWLEDGE_LEAK': '重写该段；仅使用 Writer View 的已知事实与本场获准信息。',
    'CONTINUITY': '按 Writer View 的当前状态修正该段动作与时间衔接。',
    'EXPOSITION': '压缩该段重复解释，让行动、阻力或后果承担信息。',
    'DIALOGUE': '减少该段说明性对白，保留人物诉求、反应和分歧。',
    'STYLE': '保留原有声音，仅调整明确影响阅读的表达。',
}


def revision_feedback(report, body):
    """Never return checker prose, quotations, truth, IDs, rationale or suggestions."""
    paragraphs = body.splitlines()
    fixes = []
    for row in report.get('issues', []):
        level = row.get('priority', 'SUGGESTION')
        if level not in ['MUST FIX', 'SHOULD FIX']:
            continue
        if level == 'SHOULD FIX' and row.get('confidence') != 'HIGH':
            continue
        code, paragraph = row.get('code'), row.get('paragraph')
        if code not in SAFE_FIXES or type(paragraph) is not int or not 1 <= paragraph <= len(paragraphs):
            if level == 'MUST FIX':
                raise ValueError('MUST FIX 缺少可安全转交的 code / paragraph，请 Checker 补充结构化定位')
            continue
        fixes.append({'priority': level, 'paragraph': paragraph, 'instruction': SAFE_FIXES[code]})
        if code in ['KNOWLEDGE_LEAK', 'UNSUPPORTED_POV']:
            paragraphs[paragraph-1] = '[本段待按 Writer View 重写]'
    return {'audience': 'WRITER', 'fixes': fixes, 'body': '\n'.join(paragraphs)}


def author_packet(root, state, plan, canon, characters, reader_knowledge=None):
    return {'context_version': '0.6', 'audience': 'AUTHOR', 'project_id': root.name,
            'state': state, 'plan': plan, 'canon': canon, 'characters': characters,
            'reader_knowledge': reader_knowledge or {},
            'disclosure_permissions': plan.get('approved_disclosures', [])}


def checker_packet(author, body):
    return {**author, 'audience': 'CHECKER', 'writer_output': body,
            'review_policy': 'MUST FIX blocks; SHOULD FIX only high confidence; SUGGESTION and STYLE ONLY optional',
            'feedback_contract': {'code': list(SAFE_FIXES), 'paragraph': '1-based line',
                                  'priority': ['MUST FIX', 'SHOULD FIX', 'SUGGESTION', 'STYLE ONLY']}}


def actor_knowledge_at(state, character_id, chapter, committed, strict_receipts=False):
    """Evidence-backed actor projection. Missing history never becomes known truth.

    Separate from the Author inspector: suspicion text never falls back to
    canonical_truth. This pure projection does not mutate either authority.
    """
    if type(chapter) is not int or chapter not in committed:
        raise ValueError('角色视图只能使用已提交章节或初始化背景')
    result={'audience':'ACTOR','character_id':character_id,'as_of_chapter':chapter,
            'known':[],'suspected':[],'false_beliefs':[],'unknown_suspicion_count':0}
    facts=state.get('knowledge-state.yaml',{}).get('facts',{})
    events=state.get('timeline.yaml',{}).get('events',{})
    def receipt_valid(fact,e,acquired):
        if not strict_receipts:return True
        introduced=fact.get('introduced_chapter');event=events.get(e.get('source_event'))
        if type(introduced) is not int or introduced>acquired or not isinstance(event,dict):return False
        if event.get('chapter') not in committed or event.get('chapter',acquired+1)>acquired:return False
        try:
            from datetime import datetime
            a=datetime.fromisoformat(e['story_time']);b=datetime.fromisoformat(event['story_time'])
            if a.tzinfo is None or b.tzinfo is None or b>a:return False
            current=state.get('current-story-state.yaml',{}).get('project',{}).get('story_date')
            if current:
                end=datetime.fromisoformat(current)
                if end.tzinfo is None or a>end:return False
        except (KeyError,TypeError,ValueError):return False
        return True
    for fid,fact in facts.items():
        if not isinstance(fact,dict):continue
        for key,out in [('known_by','known'),('suspected_by','suspected')]:
            for e in fact.get(key,[]):
                if not isinstance(e,dict) or e.get('character_id')!=character_id:continue
                acquired=e.get('acquired_chapter',e.get('since_chapter'))
                if type(acquired) is not int or acquired not in committed or acquired>chapter or not receipt_valid(fact,e,acquired):continue
                text=(fact.get('canonical_truth') if out=='known' else e.get('belief') or e.get('text'))
                if out=='suspected' and (not isinstance(text,str) or not text.strip()):result['unknown_suspicion_count']+=1
                if isinstance(text,str) and text.strip():result[out].append({'fact_id':fid,'text':text,
                    'acquired_chapter':acquired,'source_event':e.get('source_event'),'basis':'COMMITTED'})
        belief=fact.get('false_beliefs',{}).get(character_id)
        if isinstance(belief,dict):
            acquired=belief.get('acquired_chapter',belief.get('since_chapter'))
            if type(acquired) is int and acquired in committed and acquired<=chapter and isinstance(belief.get('belief'),str) and receipt_valid(fact,belief,acquired):
                result['false_beliefs'].append({'fact_id':fid,'text':belief['belief'],
                    'acquired_chapter':acquired,'source_event':belief.get('source_event'),'basis':'COMMITTED_BELIEF_NOT_TRUTH'})
    return result
