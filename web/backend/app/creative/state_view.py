"""Read-only projection over existing state files, including supported list timelines.
Formal State Commit validation remains untouched. Uncommitted events do not grant
actor knowledge. This adapter never writes or migrates the original YAML.
"""
from app.errors import ConsoleError
from app.tasks.router import core_workflow

def read_state(ws,engine):
    if (ws.root/'state/.commit.lock').exists() or (ws.root/'state/proposed/transaction.json').exists():raise ConsoleError('State 正在提交或恢复，请稍后读取角色视图',409)
    w=core_workflow(engine);result={name:ws.yaml_file('state/'+name) for name in w.state_paths(ws.root)}
    timeline=result.get('timeline.yaml',{});events=timeline.get('events',{})
    if isinstance(events,list):
        normalized={}
        for row in events:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row['id'] in normalized:raise ConsoleError('时间线缺少稳定事件 ID 或有重复，无法核对来源',422)
            normalized[row['id']]=row
        result['timeline.yaml']={**timeline,'events':normalized}
    elif not isinstance(events,dict):raise ConsoleError('时间线事件结构无效',422)
    if (ws.root/'state/.commit.lock').exists() or (ws.root/'state/proposed/transaction.json').exists():raise ConsoleError('读取期间 State 开始提交，请重新读取',409)
    return result


def writing_scope(state, actor, chapter, story_time=None):
    """Interactive Context Builder projection; never infer historical runtime.

    Reuses actor receipts and Writer views. The caller still requires a hash-bound
    author safety review of free text before sending this packet to a Writer.
    """
    import re
    from knowledge_isolation import actor_knowledge_at,hidden_texts
    from datetime import datetime
    committed = {0} | {e['chapter'] for e in state.get('chapter-ledger.yaml', {}).get('entries', []) if type(e.get('chapter')) is int}
    cutoff = max((n for n in committed if n < chapter), default=0) if chapter else max(committed)
    def time_of(value):
        if not isinstance(value, str) or not value:return None
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return parsed if parsed.tzinfo else None
        except ValueError:return None
    at = time_of(story_time)
    if story_time and at is None:raise ValueError('故事时间必须带明确时区；架空纪年可留空，按已提交章节筛选')
    def eligible(row):
        n = row.get('since_chapter')
        if type(n) is not int or n not in committed or n > cutoff:return False
        if row.get('visibility') != 'PUBLIC' and not (actor and row.get('visibility') == 'CHARACTER' and actor in row.get('known_by', [])):return False
        return not at or time_of(row.get('story_time')) is not None and time_of(row.get('story_time')) <= at
    knowledge = actor_knowledge_at(state, actor, cutoff, committed, strict_receipts=True) if actor else {'known': [], 'suspected': [], 'false_beliefs': [], 'unknown_suspicion_count': 0}
    facts = state.get('knowledge-state.yaml', {}).get('facts', {})
    for kind, field in [('known', 'known_by'), ('suspected', 'suspected_by'), ('false_beliefs', None)]:
        def fits(entry):
            fact = facts[entry['fact_id']]
            if fact.get('restricted_until') is not None and chapter and chapter < fact['restricted_until']:return False
            rows = [fact.get('false_beliefs', {}).get(actor, {})] if field is None else [x for x in fact.get(field, []) if x.get('character_id') == actor and x.get('acquired_chapter') == entry['acquired_chapter']]
            return not at or any(time_of(x.get('story_time')) is not None and time_of(x.get('story_time')) <= at for x in rows)
        knowledge[kind] = [e for e in knowledge[kind] if fits(e)]
    allowed = {x['fact_id'] for x in knowledge['known']}
    # Public availability is explicitly declared, not inferred from a fact's name.
    for fid, fact in facts.items():
        n = fact.get('public_since_chapter'); t = time_of(fact.get('public_story_time'))
        if fact.get('public') and type(n) is int and n in committed and n <= cutoff and (not at or t is not None and t <= at) and (fact.get('restricted_until') is None or chapter and chapter >= fact['restricted_until']):
            if fid not in allowed:knowledge['known'].append({'fact_id': fid, 'text': fact.get('canonical_truth', ''), 'acquired_chapter': n, 'basis': 'DECLARED_PUBLIC'})
            allowed.add(fid)
    hidden = hidden_texts(state, {}, allowed)
    def safe_text(value):
        return isinstance(value, str) and value.strip() and not any(s in value for s in hidden) and not re.search(r'不要.{0,30}(暗示|透露|揭露)|不得.{0,30}(暗示|透露|揭露)|不能让.{0,30}知道', value)
    def views(rows):return [v['text'] for v in rows if isinstance(v, dict) and eligible(v) and safe_text(v.get('text'))]
    return {'cutoff': cutoff, 'knowledge': knowledge, 'allowed': allowed, 'hidden': hidden, 'views': views, 'safe_text': safe_text, 'committed': committed, 'time_of': time_of, 'at': at}
