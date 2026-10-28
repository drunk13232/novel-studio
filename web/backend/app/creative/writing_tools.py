"""Small author workflow adapters. Reuse project preferences, candidates and indexes.
No new story store, AI planner, permission system or automatic manuscript writer.
"""
import re
from typing import Literal
from pydantic import Field,field_validator
from app.errors import ConsoleError
from app.library.storage import read,uid,now,digest
from app.studio_tools import normalized,text_hash,utf16_slice
from .writing import Strict,ContextChoice

class ScopeSave(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    choice:ContextChoice
class WritingAction(Strict):
    id:str=Field(default='',max_length=50)
    name:str=Field(min_length=1,max_length=80)
    action:Literal['polish','dialogue','condense','expand','logic','voice','custom']='custom'
    instruction:str=Field(default='',max_length=2000)
    candidate_count:int=Field(default=1,ge=1,le=3)
    directions:list[str]=Field(default_factory=list,max_length=3)
    @field_validator('directions')
    @classmethod
    def lengths(cls,rows):
        if any(len(x)>500 for x in rows):raise ValueError('每个候选方向最多 500 字符')
        return rows
class ActionSave(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    template:WritingAction
class Etag(Strict):etag:str=Field(pattern=r'^[0-9a-f]{64}$')
class Lookup(Strict):
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    start:int=Field(ge=0)
    end:int=Field(gt=0)
    quote:str=Field(min_length=1,max_length=120)
    source_mode:Literal['saved','buffer']='saved'

def saved_scope(s,p,path):
    s.tools.doc(p,path);cid,_,_=s.tools.chapter(p,path)
    pref=s.tools.preference(p,'writing/scopes');row=pref['value'].get(text_hash(path))
    if row and (row.get('path')!=path or row.get('chapter_id')!=cid):row=None
    return {'etag':pref['etag'],'scope':row,'approval_restored':False,'project_id':p}

def save_scope(s,p,b):
    s.tools.writable(p);path=b.choice.path;cid,_,_=s.tools.chapter(p,path)
    with s.tools.lock:
        pref=s.tools.preference(p,'writing/scopes')
        if pref['etag']!=b.etag:raise ConsoleError('参考偏好已在另一窗口修改，请刷新后保存',409)
        key=text_hash(path)
        if key not in pref['value'] and len(pref['value'])>=3000:raise ConsoleError('参考偏好已达上限，请先整理',422)
        value=b.choice.model_dump(exclude={'path','revision','task'})
        pref['value'][key]={'path':path,'chapter_id':cid,'choice':value,'updated_at':now(),'writer_review_required':True}
        s.tools.put_pref(p,'writing/scopes',pref['value'],b.etag)
        return saved_scope(s,p,path)

def actions(s,p):
    s.registry.get(p);pref=s.tools.preference(p,'writing/actions')
    return {'etag':pref['etag'],'templates':pref['value'].get('templates',[]),'project_id':p,'contains_model_or_permissions':False}

def save_action(s,p,b):
    s.tools.writable(p)
    with s.tools.lock:
        pref=actions(s,p)
        if pref['etag']!=b.etag:raise ConsoleError('写作操作已变化，请刷新后重试',409)
        row=b.template.model_dump();rows=pref['templates']
        if row['id']:
            if not re.fullmatch(r'action_[0-9a-f]{32}',row['id']) or not any(x['id']==row['id'] for x in rows):raise ConsoleError('写作操作不属于当前作品',404)
        else:
            if len(rows)>=60:raise ConsoleError('最多保留 60 个写作操作，请先整理',422)
            row['id']=uid('action')
        row.update(updated_at=now());rows=[x for x in rows if x['id']!=row['id']]+[row]
        s.tools.put_pref(p,'writing/actions',{'templates':rows},b.etag)
        return {**actions(s,p),'saved_id':row['id']}

def delete_action(s,p,id,b):
    s.tools.writable(p)
    with s.tools.lock:
        pref=actions(s,p)
        if pref['etag']!=b.etag:raise ConsoleError('写作操作已变化，请刷新后重试',409)
        if not any(x['id']==id for x in pref['templates']):raise ConsoleError('写作操作不属于当前作品',404)
        s.tools.put_pref(p,'writing/actions',{'templates':[x for x in pref['templates'] if x['id']!=id]},b.etag)
        return actions(s,p)

def describe_candidate(s,p,id):
    row=s.tools.candidate(p,id)
    if row.get('project_id')!=p:raise ConsoleError('候选不属于当前作品',404)
    try:
        doc=s.tools.doc(p,row['path']);text=normalized(doc)
        current=doc['etag']==row['document_revision'] and text_hash(text)==row['originalHash'] and utf16_slice(text,row['start'],row['end'])==row['selected_text']
    except (ConsoleError,KeyError):current=False
    return {**row,'source_current':current,'can_accept':current and row['status']=='PROPOSED','read_only_history':row['status']!='PROPOSED' or not current}

def candidate_history(s,p,path,offset=0,limit=30):
    doc=s.tools.doc(p,path);text=normalized(doc)
    rows=s.workbench.revision_list(p,path)['candidates']
    rows.sort(key=lambda r:r.get('created_at',''),reverse=True)
    result=[];current_hash=text_hash(text)
    for r in rows[offset:offset+limit]:
        current=doc['etag']==r.get('document_revision') and current_hash==r.get('originalHash')
        result.append({**{k:r.get(k) for k in ['id','action','status','created_at','completed_at','ai_metadata','saved_path','task_id']},'instruction_summary':str(r.get('instruction',''))[:100],'source_current':current,'variant_count':len(r.get('variants') or [r]),'has_candidate':'candidate' in r,'draft_saved_at':max((v.get('updated_at','') for v in (r.get('author_draft') or {}).get('variants',{}).values()),default='')})
    return {'candidates':result,'total':len(rows),'offset':offset,'limit':limit,'project_id':p,'source_path':path,'source_revision':doc['etag']}

def lookup(s,p,b):
    doc=s.tools.doc(p,b.path);text=normalized(doc)
    if doc['etag']!=b.revision or b.start>=b.end:raise ConsoleError('选区或正文已变化，请重新选择资料名称',409)
    source_bound=utf16_slice(text,b.start,b.end)==b.quote if b.end<=len(text.encode('utf-16-le'))//2 else False
    if b.source_mode=='saved' and not source_bound:raise ConsoleError('选区与已保存原文不匹配，请重新选择',409)
    query=b.quote.strip()
    if not query:raise ConsoleError('请选择人物或设定名称',422)
    nodes=s.workbench.knowledge.view(p)['entities'];aliases={r['canonical']['id']:r['canonical'].get('aliases',[]) for r in s.tools.characters.list(p)}
    anchors={(a['target_type'],a['target_id']) for a in s.workbench.knowledge.anchors(p,b.path) if a.get('located') and a['start']>=b.start and a['end']<=b.end} if source_bound and b.source_mode=='saved' else set()
    result=[]
    for n in nodes:
        if n['type'] not in {'character','entity','location','faction','item','term','event'}:continue
        reason='CONFIRMED_ANCHOR' if (n['type'],n['id']) in anchors else 'EXACT_NAME' if query.casefold()==n['name'].casefold() else 'ALIAS' if n['type']=='character' and any(query.casefold()==x.casefold() for x in aliases.get(n['id'],[])) else None
        if reason:result.append({k:n.get(k) for k in ['id','type','name','path','status','summary']}|{'reason':reason})
    hits=s.tools.search(p,query,locked=True);chapters=[];seen=set();_,current,_=s.tools.chapter(p,b.path)
    for hit in sorted(hits,key=lambda h:(abs(int(h['number'])-current),h['path'],h['start'])):
        if hit['path']==b.path or hit['path'] in seen:continue
        seen.add(hit['path']);chapters.append(hit)
        if len(chapters)>=12:break
    if s.tools.doc(p,b.path)['etag']!=b.revision:raise ConsoleError('查询期间正文发生变化，请重新选择',409)
    return {'project_id':p,'audience':'AUTHOR','writer_context':False,'query':query,'matches':result[:30],'ambiguous':len(result)>1,'chapters':chapters,'mentions_are_not_presence_or_knowledge':True,'canonical_data_changed':False,'selection_bound_to_disk':source_bound and b.source_mode=='saved','source_revision':doc['etag']}
