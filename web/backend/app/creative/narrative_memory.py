"""Read-only, disposable temporal views over existing Ledger/Proposed evidence.

No second state authority or migration. Historical end-state reconstruction uses
the original inverse patches, never guesses a value from today's character file.
Chapter disclosure and explicit story time are independent query boundaries.
"""
import copy,json,re,threading
from functools import lru_cache
from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.studio_tools import normalized,text_hash
from app.tasks.router import core_workflow
from .state_view import read_state,writing_scope

RUNTIME={'items.yaml','relationships.yaml','locations.yaml','factions.yaml','plot-threads.yaml','foreshadowing.yaml','knowledge-state.yaml','timeline.yaml'}

def moment(value):
    try:
        v=datetime.fromisoformat(value.replace('Z','+00:00'))
        return v if v.tzinfo else None
    except (ValueError,TypeError,AttributeError):return None

@lru_cache(maxsize=512)
def cached_yaml(path,mtime,size,engine):
    from pathlib import Path
    return core_workflow(Path(engine)).y.read(Path(path))

@lru_cache(maxsize=1024)
def cached_revision(path,mtime,size):
    from pathlib import Path
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inverse(state,op):
    file=op['file'];pointer=op['pointer']
    if file not in RUNTIME and not file.startswith('characters/'):return
    if pointer=='/':
        if state.get(file)!=op['after']:raise ValueError('whole-record lineage mismatch')
        if op.get('before') is None:state.pop(file,None)
        else:state[file]=copy.deepcopy(op['before'])
        return
    if not pointer.startswith('/') or '~' in pointer:raise ValueError('unsupported state pointer')
    keys=pointer[1:].split('/');cursor=state[file]
    for key in keys[:-1]:cursor=cursor[int(key)] if isinstance(cursor,list) else cursor[key]
    key=int(keys[-1]) if isinstance(cursor,list) else keys[-1]
    if cursor[key]!=op['after']:raise ValueError('patch lineage mismatch')
    # Existing extractor cannot delete fields; None before an appended list is
    # the only append encoding. Dict None is conservatively restored as None.
    if isinstance(cursor,list) and op.get('before') is None and key==len(cursor)-1:cursor.pop()
    elif isinstance(cursor,dict) and op.get('before') is None and len(keys)==2 and keys[0] in {'facts','events','items','relationships','locations','factions','threads','foreshadowing'}:cursor.pop(key,None)
    else:cursor[key]=copy.deepcopy(op.get('before'))

def temporal_state(ws,engine,state,cutoff,story_time=''):
    """Project committed END states, not exact unrecorded intra-scene instants."""
    w=core_workflow(engine);entries=state.get('chapter-ledger.yaml',{}).get('entries',[])
    at=moment(story_time);current_at=moment(state.get('current-story-state.yaml',{}).get('project',{}).get('story_date'))
    if story_time and at is None:raise ConsoleError('故事时间需要明确时区；不确定日期请留空',422)
    result=copy.deepcopy(state);records=[];warnings=[];receipts=[];unresolved=False
    # Old committed operations address timeline list indexes. Undo them in the
    # original representation, then normalize only the returned projection.
    raw_timeline=ws.yaml_file('state/timeline.yaml')
    if isinstance(raw_timeline.get('events'),list):result['timeline.yaml']=copy.deepcopy(raw_timeline)
    for e in entries:
        if e.get('chapter')==0:continue
        id=e.get('proposal_id','');record={'chapter':e.get('chapter'),'proposal_id':id,'status':'MISSING_HISTORY','time':'','operations':[],'source_path':''}
        outside=e.get('chapter',0)>cutoff
        try:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',id):raise ValueError('missing receipt')
            file=ws.resolve('state/proposed/'+id+'.yaml');s=file.stat()
            v=cached_yaml(str(file),s.st_mtime_ns,s.st_size,str(engine));sha=w.digest(v);receipts.append([id,sha])
            final=v['final']
            if sha!=e.get('proposal_sha256') or final['chapter']!=e['chapter'] or final['body_sha256']!=e.get('body_sha256'):raise ValueError('receipt mismatch')
            path=final['body_path'];body_file=ws.resolve(path);stat=body_file.stat()
            source_revision=cached_revision(str(body_file),stat.st_mtime_ns,stat.st_size)
            if source_revision!=e['body_sha256']:
                record['status']='STALE_SOURCE';raise ValueError('source changed')
            time=v.get('author_state_time',{}).get('value') or next((o['after'] for o in v['extraction']['operations'] if o['file']=='current-story-state.yaml' and o['pointer']=='/project/story_date'),'')
            record.update(status='VERIFIED',time=time,operations=v['extraction']['operations'],source_path=path,source_revision=source_revision)
            record['outside']=outside or bool(at and moment(time) and moment(time)>at)
            if at and not moment(time):
                # A source without an end anchor cannot establish a precise
                # historical state. Latest/no-time navigation remains possible.
                if current_at and at<current_at:record['outside']=True;record['status']='UNKNOWN_TIME'
        except (ConsoleError,OSError,ValueError,KeyError,TypeError):
            receipts.append([id,record['status']]);record['outside']=outside or bool(at and current_at and at<current_at)
        if record['status']!='VERIFIED':warnings.append(record['status'])
        records.append(record)
    # Verify that current runtime still descends from these recorded patches.
    # A hand-edited current field cannot acquire authority merely by leaving
    # the Ledger untouched. This check reads no additional manuscript text.
    lineage=copy.deepcopy(result)
    for r in reversed(records):
        if r['status']!='VERIFIED':continue
        try:
            for op in reversed(r['operations']):inverse(lineage,op)
        except (ValueError,KeyError,TypeError,IndexError):unresolved=True;warnings.append('INCOMPLETE_PATCH_LINEAGE');break
    for r in reversed(records):
        if not r.get('outside'):continue
        if r['status']!='VERIFIED':unresolved=True;continue
        try:
            for op in reversed(r['operations']):inverse(result,op)
        except (ValueError,KeyError,TypeError,IndexError):unresolved=True;warnings.append('INCOMPLETE_PATCH_LINEAGE')
    stale=any(r['status']=='STALE_SOURCE' for r in records)
    if unresolved or stale:
        # Do not substitute current runtime for missing or stale history. Static
        # character Canon stays separate; authoritative originals are untouched.
        for key in list(result):
            if key in RUNTIME or key.startswith('characters/'):result[key]={'facts':{}} if key=='knowledge-state.yaml' else {'events':{}} if key=='timeline.yaml' else {'foreshadowing':{}} if key=='foreshadowing.yaml' else {}
        warnings.append('HISTORICAL_STATE_UNKNOWN' if unresolved else 'STATE_SOURCE_STALE')
    elif isinstance(result.get('timeline.yaml',{}).get('events'),list):
        result['timeline.yaml']['events']={e['id']:e for e in result['timeline.yaml']['events'] if isinstance(e,dict) and e.get('id')}
    return result,{'authority':'DERIVED_COMMITTED_END_STATE_NOT_CANON','cutoff':cutoff,'story_time':story_time or 'UNKNOWN','history_status':'UNKNOWN' if unresolved or stale else 'VERIFIED_PROJECTION' if not warnings else 'LEGACY_VIEWS_ONLY','boundary':'AUTHOR_END_STATE_ANCHORS_NOT_EXACT_INTRA_CHAPTER_TIMES','warnings':sorted(set(warnings)),'receipts_sha256':text_hash(json.dumps(receipts,ensure_ascii=False)),'records':records}

class Query(BaseModel):
    model_config=ConfigDict(extra='forbid')
    through_chapter:int|None=Field(default=None,ge=0,le=99999)
    story_time:str=Field(default='',max_length=80)
    character_id:str=Field(default='',max_length=100)
    queries:list[str]=Field(default_factory=list,max_length=4)
    include_structure:bool=False

def inspect(writing,p,b,*,locked=False):
    ws=writing.registry.workspace(p);state=read_state(ws,writing.registry.engine)
    committed={0}|{e['chapter'] for e in state.get('chapter-ledger.yaml',{}).get('entries',[]) if type(e.get('chapter')) is int}
    cutoff=min(b.through_chapter if b.through_chapter is not None else max(committed),max(committed))
    chars={r['canonical']['id']:r['canonical']['name'] for r in writing.tools.characters.list(p)}
    if b.character_id and b.character_id not in chars:raise ConsoleError('人物不属于当前作品',422)
    projected,audit=temporal_state(ws,writing.registry.engine,state,cutoff,b.story_time)
    # Inspector is AUTHOR-only. Never copy this response directly into Writer.
    scope=writing_scope(projected,b.character_id,cutoff+1,b.story_time or None)
    hits=[]
    for q in b.queries:
        if not q.strip() or len(q)>100:raise ConsoleError('检索词需为 1–100 字',422)
        for hit in writing.tools.search(p,q,before_chapter=cutoff+1,locked=locked):
            if len(hits)>=32:break
            # Revalidate the body without reparsing every ChapterCard per hit.
            # This retains the exact manuscript-only scope of StudioTools.doc.
            if not re.fullmatch(r'chapters/chapter-\d+/(?:draft|final|manual-[a-z0-9-]+)\.(?:txt|md)',hit['path']):continue
            doc=ws.content(hit['path'])
            if doc['etag']==hit['revision'] and hit['exact'] in normalized(doc):hits.append({**hit,'basis':'TEXT_NOT_OBJECTIVE_FACT','version_current':True})
    def values(file,key):
        rows=projected.get(file,{}).get(key,{})
        if isinstance(rows,list):return rows
        return [{'id':id,**v} for id,v in rows.items() if isinstance(v,dict)] if isinstance(rows,dict) else []
    events=values('timeline.yaml','events');events=[e for e in events if e.get('chapter') in committed and e.get('chapter',999999)<=cutoff and (not b.story_time or moment(e.get('story_time')) and moment(e['story_time'])<=moment(b.story_time))]
    history=[{k:r.get(k) for k in ('chapter','proposal_id','status','time','source_path','source_revision')} for r in audit.pop('records')]
    for r in history:r['disclosed']=r.get('chapter',999999)<=cutoff
    structure={}
    if b.include_structure:
        core=writing.literary_core;index=core.index(p);records=[]
        for c in index['records']:
            d=c['literary'];positions=[v for v in d['positions'] if not b.character_id or v['character']==b.character_id]
            evidence=[e for e in c['evidence_status'] if e.get('chapter',999999)<=cutoff]
            if not evidence and d['phase']!='PLANNED':continue
            if b.character_id and not positions and not any(l['id']==b.character_id for l in d['links']):continue
            visible_paths={e.get('path') for e in evidence}
            records.append({'id':c['id'],'kind':d['kind'],'title':d['title'],'phase':d['phase'],'positions':positions,'evidence':evidence,'current':bool(evidence) and all(e.get('current') for e in evidence),'basis':'AUTHOR_INTERPRETATION_NOT_STATE','dependencies':d['dependencies'],'events':[{'phase':e['literary']['phase'],'text':e['text'],'evidence':[v for v in e['literary']['evidence'] if v['path'] in visible_paths]} for e in c['events'] if e['literary']['phase']=='PLANNED' or any(v['path'] in visible_paths for v in e['literary']['evidence'])]})
        for r in records:
            observed=[e for e in r['events'] if e['phase']!='PLANNED' and e['evidence']]
            if observed:r['phase']=observed[-1]['phase']
        # Reuse the existing formal dependency validator; associations do not
        # become causal edges and literary interpretations are not proof.
        import networkx as nx
        edges=[(d['before'],d['after']) for c in records for d in c['dependencies'] if d['kind']=='strict_order']
        graph=nx.DiGraph(edges);structure={'records':records,'strict_dependency_edges':edges,'strict_order_is_dag':nx.is_directed_acyclic_graph(graph),'cycle':list(nx.find_cycle(graph)) if graph and not nx.is_directed_acyclic_graph(graph) else [],'authority':'AUTHOR_DECLARED_DEPENDENCIES_NOT_PROVEN_SOCIAL_CAUSALITY'}
    return {'project_id':p,'audience':'AUTHOR','writer_context':False,'cutoff':cutoff,'characters':chars,'knowledge':scope['knowledge'],'items':values('items.yaml','items'),'relationships':values('relationships.yaml','relationships'),'character_states':[v for k,v in projected.items() if k.startswith('characters/') and isinstance(v,dict) and (not b.character_id or v.get('id')==b.character_id)],'events':events[:500],'evidence':hits,'history':[r for r in history if r['disclosed']],'audit':audit,'structure':structure,'warning':'已提交结束状态不等于精确场景时刻；正文中的说谎、回忆与不可靠叙述不自动成为客观事实。'}
