"""Actor views over the existing knowledge/state authority and generic safe capsule.
No author truth enters unknown/suspected fields. Lore is filtered before matching.
"""
import copy,json
from app.errors import ConsoleError
from app.tasks.router import core_workflow
from app.creative.state_view import read_state

def contains(value,terms):
    if isinstance(value,str):return any(t and t in value for t in terms)
    if isinstance(value,dict):return any(contains(x,terms) for x in value.values())
    if isinstance(value,list):return any(contains(x,terms) for x in value)
    return False

def prune(value,terms):
    if isinstance(value,str):return None if contains(value,terms) else value
    if isinstance(value,dict):return {k:v for k,x in value.items() if (v:=prune(x,terms)) is not None}
    if isinstance(value,list):return [v for x in value if (v:=prune(x,terms)) is not None]
    return value

def committed_chapters(state):
    return {0}|{x['chapter'] for x in state.get('chapter-ledger.yaml',{}).get('entries',[]) if type(x.get('chapter')) is int}

def character_snapshot(registry,characters,project,source_id,chapter):
    state=read_state(registry.workspace(project),registry.engine)
    from knowledge_isolation import actor_knowledge_at,hidden_texts
    row=characters.get(project,source_id);card=row['canonical'];committed=committed_chapters(state)
    requested=chapter
    at=max(committed) if chapter is None else max((n for n in committed if n<=chapter),default=0)
    try:knowledge=actor_knowledge_at(state,source_id,at,committed,strict_receipts=True)
    except ValueError as error:raise ConsoleError(str(error),409) from None
    known={x['fact_id'] for x in knowledge['known']};hidden=hidden_texts(state,{},known)
    hidden+=card.get('secrets',{}).get('author_only',[])
    # Future story plans, private relationship state and author-only secrets never
    # become role instructions. Public history is filtered by explicit provenance.
    profile={k:card.get(k) for k in ['name','aliases','identity','appearance','personality','psychology','behavior','speech','biography','abilities','goals']}
    profile=prune(profile,hidden)
    relationships=[]
    for rel in state.get('relationships.yaml',{}).get('relationships',{}).values():
        if source_id not in rel.get('characters',[]):continue
        for v in rel.get('writer_view',[]):
            n=v.get('since_chapter')
            if type(n) is int and n in committed and n<=at and (v.get('visibility')=='PUBLIC' or source_id in v.get('known_by',[])):
                text=v.get('text','')
                if text and not contains(text,hidden):relationships.append({'text':text,'chapter':n,'basis':'COMMITTED'})
    shareable=[x['fact_id'] for x in knowledge['known'] if state['knowledge-state.yaml']['facts'][x['fact_id']].get('public') and type(state['knowledge-state.yaml']['facts'][x['fact_id']].get('public_since_chapter')) is int and state['knowledge-state.yaml']['facts'][x['fact_id']]['public_since_chapter']<=at]
    return {'name':card.get('name') or '未命名人物','profile':profile,'knowledge':knowledge,'relationships':relationships,
        'runtime':prune({k:v for k,v in row.get('runtime',{}).items() if k in ['status','alive','age','location','injuries','conditions','inventory','goals','emotional_state']},hidden) if at==max(committed) else {'history':'UNKNOWN'},'public_fact_ids':shareable,'source_revision':row.get('etag'),'as_of_chapter':at,'requested_scene_chapter':requested,'knowledge_notice':'场景尚未提交，仅使用此前已提交的知识；后续变化保持未知。' if requested is not None and requested not in committed else '', 'source_kind':'CHARACTER_CANON_AND_COMMITTED_STATE'}

def secret_terms(registry,characters,project):
    state=read_state(registry.workspace(project),registry.engine)
    from knowledge_isolation import hidden_texts
    terms=hidden_texts(state,{},set())
    for card in characters.list(project):terms+=card['canonical'].get('secrets',{}).get('author_only',[])
    return list({x for x in terms if isinstance(x,str) and x.strip()})

def lore_entries(rows,actor_id,probe,budget=9000):
    selected=[];spent=0;probe=probe.casefold()
    for row in sorted(rows,key=lambda x:-x.get('priority',0)):
        if not row.get('enabled',True) or actor_id not in row.get('audiences',[]):continue
        keys=[x.casefold() for x in row.get('keys',[]) if x]
        secondary=[x.casefold() for x in row.get('secondary_keys',[]) if x]
        matches=[x in probe for x in keys]
        if not row.get('constant') and not (matches and (all(matches) if row.get('match')=='ALL' else any(matches))):continue
        if secondary and not any(x in probe for x in secondary):continue
        if spent+len(row['text'])>budget:continue
        selected.append({'id':row['id'],'name':row['name'],'text':row['text'],'source_type':row.get('source_type'),'source_id':row.get('source_id'),'temporary_not_canon':True})
        spent+=len(row['text'])
        if len(selected)>=12:break
    return selected

def fit(items,budget):
    result=[];spent=0
    for item in reversed(items):
        size=len(json.dumps(item,ensure_ascii=False))
        if spent+size>budget:continue
        result.append(item);spent+=size
    return list(reversed(result))

def view(session,actor_id,messages,scene,lore,memories):
    actor=next((x for x in session['actors'] if x['id']==actor_id),None)
    if not actor:raise ConsoleError('角色不属于此会话',403)
    # Separate actor profiles; other NPCs contribute only visible dialogue and names.
    personal=[x for x in memories if actor_id in x['audiences'] and x.get('status')=='CONFIRMED'
              and set(x.get('source_node_ids',[]))<=set(m['id'] for m in messages)]
    temporary=[x for x in scene.get('temporary_facts',[]) if actor_id in x['audiences']]
    transcript=[{k:m[k] for k in ['id','speaker_name','text','kind'] if k in m} for m in messages[-32:] if not m.get('audiences') or actor_id in m['audiences']]
    probe=scene.get('background','')+'\n'+'\n'.join(x['text'] for x in transcript[-6:])
    snapshot=copy.deepcopy(actor['snapshot'])
    omitted={}
    for group in ['known','suspected','false_beliefs']:
        values=snapshot.get('knowledge',{}).get(group,[])
        kept=fit(values,6000 if group=='known' else 1800);omitted[group]=len(values)-len(kept)
        snapshot.setdefault('knowledge',{})[group]=kept
    personal=fit(personal,5000);transcript=fit(transcript,14000)
    result={'audience':'ACTOR','actor_id':actor_id,'self':snapshot,
        'other_participants':[{'id':x['id'],'name':x['name']} for x in session['actors'] if x['id']!=actor_id],
        'user_persona':session['persona'],'scene':{k:scene.get(k) for k in ['time','location','background','dialogue_language']},
        'temporary_information':temporary,'confirmed_scene_memory':personal,
        'activated_lore':lore_entries(lore,actor_id,probe,budget=5000),'visible_conversation':transcript,
        'canonical_authority':False,'context_omissions':omitted,'stored_turn_count':len(messages),'missing_history':'Use visible turns and confirmed personal memory; do not invent omitted turns.'}
    while len(json.dumps(result,ensure_ascii=False))>48000 and len(result['visible_conversation'])>1:result['visible_conversation'].pop(0)
    while len(json.dumps(result,ensure_ascii=False))>48000 and result['activated_lore']:result['activated_lore'].pop()
    if len(json.dumps(result,ensure_ascii=False))>48000:raise ConsoleError('角色上下文过大，请减少资料或整理场景记忆',413)
    return result
