"""Candidate-only operator controls; local model doubles never claim real inference."""
import asyncio,json
import pytest
from fastapi import FastAPI
import httpx
from app.creative.director import Review,routes
from app.creative.director_feedback import FeedbackRejection,FeedbackApproval
from app.errors import ConsoleError
from test_director_collaboration import lab,install,start,ready,request,TEXT,Fake
from test_creative_director import body,done

def test_reject_approved_feedback_retains_candidate_and_cannot_execute(lab,monkeypatch):
 async def run():
  row,calls=await ready(lab,monkeypatch);s,p,root,path,*_=lab;original=(root/path).read_bytes()
  row=await done(s,p,s.feedback(p,row['id'],request(row,direction='保留角色的当前决定。')));proposal=row['feedback_proposal'];assert proposal['author_direction']=='保留角色的当前决定。'
  row=s.approve_feedback(p,row['id'],FeedbackApproval(etag=row['etag'],proposal_id=proposal['id'],confirm=True,confirm_important=True));count=len(calls)
  rejected=s.reject_feedback(p,row['id'],FeedbackRejection(etag=row['etag'],proposal_id=proposal['id']))
  assert rejected['draft']==TEXT and rejected['feedback_state']['status']=='REJECTED' and not rejected['feedback_state']['valid']
  assert not rejected['rewrite'] and not rejected.get('rewrite_source') and len(calls)==count
  with pytest.raises(ConsoleError):s.approve_feedback(p,row['id'],FeedbackApproval(etag=rejected['etag'],proposal_id=proposal['id'],confirm=True,confirm_important=True))
  assert (root/path).read_bytes()==original
 asyncio.run(run())

def test_review_failure_retries_only_reviewer_with_compact_methods_and_real_receipt(lab,monkeypatch):
 calls=install(lab,monkeypatch);s,p,root,path,*_=lab;attempts=[];prepared=[];prepare=s.reviews.prepare
 def prepare_record(project,request,**kw):prepared.append(kw);return prepare(project,request,**kw)
 monkeypatch.setattr(s.reviews,'prepare',prepare_record)
 class Flaky(Fake):
  bound_ai_selection=True
  def __init__(self,prompt):
   from app.ai.controls import RequestControls
   super().__init__(prompt);self.request_controls=RequestControls();self.selected_ai={'backend':'MOCK','provider_name':'Reviewer fixture','model':'review-fixture'}
  selected_ai={'backend':'MOCK','provider_name':'Reviewer fixture','model':'review-fixture'}
  def start_task(self,prompt,emit,**kw):
   attempts.append(prompt)
   if len(attempts)==1:raise RuntimeError('Controlled review failure')
   return {'status':'completed','output':json.dumps({'verdict':'PASS','summary':'MOCK review, not a quality claim','issues':[]})}
 monkeypatch.setattr('app.creative.reviews.adapter',lambda *a,**kw:Flaky(''))
 async def run():
  original=(root/path).read_bytes();row=start(lab,mode='quick');row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
  assert row['status']=='FAILED' and row['review_failed'] and row['failure']['phase']=='REVIEW' and row['draft']==TEXT
  writes=sum(k=='WRITE' for k,_ in calls)
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as c:
   response=await c.post('/api/projects/'+p+'/creative-director/'+row['id']+'/review',json=Review(etag=row['etag']).model_dump())
  assert response.status_code==200;row=await done(s,p,response.json())
  assert row['status']=='REVIEW_READY' and not row['review_failed'] and row['draft']==TEXT
  assert sum(k=='WRITE' for k,_ in calls)==writes and len(attempts)==2 and row['calls']==3
  assert all(v['method_keys']==['review','character','continuity'] for v in prepared)
  assert row['usage'][-1]['phase']=='REVIEW' and row['usage'][-1]['model']=='review-fixture'
  assert row['usage'][-1]['receipt']['backend']=='MOCK' and (root/path).read_bytes()==original
 app=FastAPI();app.include_router(routes(s));asyncio.run(run())

def test_reject_http_is_project_scoped_and_does_not_call_models(lab,monkeypatch):
 async def run():
  row,calls=await ready(lab,monkeypatch);s,p,*_=lab;row=await done(s,p,s.feedback(p,row['id'],request(row)));count=len(calls);app=FastAPI();app.include_router(routes(s))
  async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://test') as c:
   response=await c.post('/api/projects/'+p+'/creative-director/'+row['id']+'/feedback/reject',json={'etag':row['etag'],'proposal_id':row['feedback_proposal']['id']})
  assert response.status_code==200 and response.json()['feedback_state']['status']=='REJECTED' and len(calls)==count
  with pytest.raises(ConsoleError):s.reject_feedback('different-project',row['id'],FeedbackRejection(etag=response.json()['etag'],proposal_id=row['feedback_proposal']['id']))
 asyncio.run(run())


def test_review_retry_does_not_spend_when_previous_time_is_unknown(lab,monkeypatch):
 async def run():
  row,calls=await ready(lab,monkeypatch);s,p,*_=lab;count=len(calls);row['timing_unknown']=True;s.put(p,row);row=s.get(p,row['id'])
  with pytest.raises(ConsoleError):s.review(p,row['id'],Review(etag=row['etag']))
  assert len(calls)==count and s.get(p,row['id'])['calls']==row['calls']
 asyncio.run(run())
