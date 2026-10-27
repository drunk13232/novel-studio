"""Dated author plans over the existing notebook. Plans never schedule model calls
or commit narrative facts. Impact is explicit association, not inferred causality.
"""
from datetime import date
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.errors import ConsoleError
from app.library.storage import database
import json

class Step(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text:str=Field(min_length=1,max_length=500)
    done:bool=False

class Schedule(BaseModel):
    model_config=ConfigDict(extra='forbid')
    start_date:str=''
    due_date:str=''
    progress:int=Field(default=0,ge=0,le=100,strict=True)
    steps:list[Step]=Field(default_factory=list,max_length=30)
    @field_validator('start_date','due_date')
    @classmethod
    def calendar_date(cls,v):
        if not v:return ''
        if len(v)!=10 or date.fromisoformat(v).isoformat()!=v:raise ValueError('Use a valid YYYY-MM-DD date')
        return v
    @model_validator(mode='after')
    def ordered(self):
        if self.start_date and self.due_date and self.start_date>self.due_date:raise ValueError('Due date must not precede start date')
        return self

def plan_overview(service,project):
    # No duplicate store or whole-book read. The same etag protects every editor.
    row=dict(service.entries(project))
    for key in ['todos','notes','revision_tasks']:row.setdefault(key,[])
    chapters=service.registry.book_center.catalog(project)['chapters']
    return {**row,'chapters':[{'id':c['id'],'number':c['number'],'title':c['title'],'path':c.get('final') or c.get('draft') or ''} for c in chapters],
            'planning_only':True,'automatic_execution':False}

def impact_preview(service,project,type='',id='',q=''):
    knowledge=service.knowledge
    if not id:
        return {'entities':[{k:n.get(k) for k in ['id','type','name','path','status']} for n in knowledge.lookup(project,q[:120],60)],'relations':[],'planning_only':True}
    if type not in {'character','entity','location','faction','item','term','event','chapter','clue','reference','asset'} or len(id)>160:raise ConsoleError('Invalid project object',422)
    knowledge.refresh(project)
    with database(knowledge.root(project)) as db:
        found=db.execute('SELECT payload FROM knowledge_entities WHERE type=? AND id=?',(type,id)).fetchone()
        if not found:raise ConsoleError('对象不属于当前小说或已经移除',404)
        node=json.loads(found[0])
        raw=db.execute('SELECT payload FROM knowledge_links WHERE (source_type=? AND source_id=?) OR (target_type=? AND target_id=?) LIMIT 201',(type,id,type,id)).fetchall()
        links=[json.loads(v[0]) for v in raw[:200]]
        keys={(e['target_type'],e['target_id']) if (e['source_type'],e['source_id'])==(type,id) else (e['source_type'],e['source_id']) for e in links}
        nodes=[]
        for kind,key in sorted(keys):
            value=db.execute('SELECT payload FROM knowledge_entities WHERE type=? AND id=?',(kind,key)).fetchone()
            if value:nodes.append(json.loads(value[0]))
    def public(n):return {k:n.get(k) for k in ['id','type','name','path','status','number']}
    return {'entity':public(node),'entities':[public(n) for n in nodes],'relations':links,'truncated':len(raw)>200,
            'planning_only':True,'causal_prediction':False,'writer_context':False,
            'notice':'Only existing recorded links are shown. A relationship is not causal proof; unlinked chapters are not covered.'}
