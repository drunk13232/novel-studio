"""Version-bound handoffs from existing candidate review to a Writer-safe task.

Only data/schema helpers. No model calls, file edits or independent task runner.
"""
import json
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.studio_tools import text_hash,utf16_slice,utf16_index
from .director_delivery import review_validity
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class FeedbackRequest(Strict):
    etag:str
    report_id:str=Field(pattern=r'^review_[0-9a-f]{32}$')
    issue:int=Field(ge=0,le=99)
    quote:int=Field(ge=0,le=19)
    location:int=Field(default=0,ge=0,le=1000)
    target:Literal['quote','paragraph']='paragraph'
    direction:str=Field(default='',max_length=1500)
class ReworkBrief(Strict):
    title:str=Field(min_length=1,max_length=120)
    instruction:str=Field(min_length=1,max_length=2000)
    checks:list[str]=Field(default_factory=list,max_length=6)
    needs_author:bool=True
    uncertainty:str=Field(default='',max_length=1500)
class FeedbackApproval(Strict):
    etag:str
    proposal_id:str=Field(pattern=r'^feedback_[0-9a-f]{32}$')
    confirm:Literal[True]
    confirm_important:bool=False
    instruction:str|None=Field(default=None,min_length=1,max_length=2000)

class FeedbackRejection(Strict):
    etag:str
    proposal_id:str=Field(pattern=r'^feedback_[0-9a-f]{32}$')

def basis(row,report_digest):
    value={k:row.get(k) for k in ['id','project_id','path','revision','context_id','context_hash','goal','plan','interventions','review_id']}
    value.update(draft_sha256=text_hash(row['draft']),report_digest=report_digest)
    return text_hash(json.dumps(value,sort_keys=True,ensure_ascii=False))

def target(row,report,b):
    if b.report_id!=row.get('review_id') or review_validity(row,report)['status']!='MATCHES_CANDIDATE':raise ConsoleError('复核报告与当前候选或要求不匹配，请重新复核',409)
    issues=report.get('report',{}).get('issues',[])
    anchor=next((a for a in report.get('anchors',[]) if a.get('issue')==b.issue),{})
    quotes=anchor.get('evidence',[])
    if b.issue>=len(issues) or b.quote>=len(quotes):raise ConsoleError('复核证据不存在，请刷新',409)
    q=quotes[b.quote];locations=q.get('locations',[])
    if not q.get('verified') or b.location>=len(locations):raise ConsoleError('没有可定位原文，不能生成定向返工',409)
    hit=locations[b.location];draft=row['draft'];start=hit['start'];end=hit['end']
    if utf16_slice(draft,start,end)!=q['quote']:raise ConsoleError('证据位置已经变化，请重新复核',409)
    if b.target=='paragraph':
        a=len(utf16_slice(draft,0,start));z=len(utf16_slice(draft,0,end));a=draft.rfind('\n',0,a)+1;tail=draft.find('\n',z);z=len(draft) if tail<0 else tail
        start=utf16_index(draft,a);end=utf16_index(draft,z)
    quote=utf16_slice(draft,start,end)
    if not quote.strip() or len(quote)>16000:raise ConsoleError('返工范围为空或过长，请使用原文引用范围',422)
    return {'start':start,'end':end,'quote':quote,'issue':b.issue,'evidence_quote':q['quote'],'finding':issues[b.issue],'direction':b.direction,'scope':b.target}

def state(row,report_digest):
    proposal=row.get('feedback_proposal')
    if not proposal:return {'status':'NOT_RUN','valid':False}
    if proposal.get('status') in {'APPLIED','REJECTED'}:return {'status':proposal['status'],'valid':False}
    valid=proposal.get('basis')==basis(row,report_digest) and not row.get('review_stale')
    return {'status':proposal.get('status','PROPOSED') if valid else 'HISTORICAL','valid':valid}
