"""Real local Director/ReviewCenter tasks; model doubles are explicitly MOCK."""
import asyncio,json,threading,time
import pytest
from app.creative.director import Patch,Plan,Step,Create
from app.creative.director_feedback import FeedbackRequest,FeedbackApproval
from app.ai.models import Provider,Model
from app.errors import ConsoleError
from app.library.storage import read,write
from test_creative_director import lab,new,body,done,Fake
TEXT='前段保留😀。\n需要修改的中段。\n后段保留。'
NEW='更明确的新中段。'

def install(lab,monkeypatch,slow_review=False,slow_writer=False,secret=False):
    s,p,*_=lab;calls=[]
    s.center.put(Provider(provider_id='fixture-writer',display_name='MOCK API writer',base_url='http://127.0.0.1:12345/v1',available_models=[Model(id='writer',protocol='chat',chat_token_parameter='max_tokens')]))
    class Writer(Fake):
        def start_task(self,prompt,emit,**kw):
            calls.append(('WRITE',prompt));text=NEW if 'selected_text_to_replace' in prompt else TEXT
            for i in range(0,len(text),2):
                if self.stop.is_set():return {'status':'interrupted','output':''}
                emit('llm_delta',text[i:i+2],{'delta':text[i:i+2]});time.sleep(.02 if slow_writer else .001)
            return {'status':'completed','output':text}
    class Commander(Fake):
        def start_task(self,prompt,emit,**kw):
            if 'ReworkBrief JSON' in prompt:
                calls.append(('FEEDBACK',prompt));value={'title':'调整中段','instruction':'不要透露幕后真相' if secret else '用一次具体行动推进回应，保留当前事件结果。','checks':['保留目标以外原文'],'needs_author':True,'uncertainty':'MOCK opinion, author decides'}
            else:
                calls.append(('PLAN',prompt));value=Plan(summary='一次明确的行动',steps=[Step(title='场景',instruction='在已有设定内完成当前对话。')],methods=['context','scene','character'],method_application=['过滤知识','用行动推进','保留人物差异']).model_dump()
            return {'status':'completed','output':json.dumps(value,ensure_ascii=False)}
    class Reviewer(Fake):
        def start_task(self,prompt,emit,**kw):
            calls.append(('REVIEW',prompt))
            if slow_review:
                for i in range(100):
                    if self.stop.is_set():return {'status':'interrupted','output':''}
                    emit('llm_delta','{REVIEW_JSON_NOT_PROSE}',{'delta':'{REVIEW_JSON_NOT_PROSE}'});time.sleep(.02)
            return {'status':'completed','output':json.dumps({'verdict':'WARN','summary':'MOCK review','issues':[{'severity':'minor','message':'RAW_CHECKER_REPORT_MARKER','evidence':['需要修改的中段。',NEW],'priority':'SUGGESTION','confidence':'HIGH'}]},ensure_ascii=False)}
    monkeypatch.setattr('app.creative.director.adapter',lambda center,p,group,prompt,model=None,**kw:Commander(prompt) if group=='scene_design' else Writer(prompt))
    monkeypatch.setattr('app.creative.reviews.adapter',lambda *args,**kw:Reviewer(''))
    return calls

def start(lab,**kw):return new(lab,mode=kw.pop('mode','director'),executor='fixture-writer::writer',collaboration='codex_api',auto_review=True,**kw)
async def ready(lab,monkeypatch,**kw):
    calls=install(lab,monkeypatch,**kw);s,p,*_=lab;row=start(lab)
    row=await done(s,p,await s.control(p,row['id'],body(row,'plan')))
    row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
    return row,calls

def request(row,**kw):return FeedbackRequest(etag=row['etag'],report_id=row['review_id'],issue=0,quote=0,**kw)

def test_full_dispatch_review_and_directed_rework_never_changes_source(lab,monkeypatch):
    async def run():
        s,p,root,path,*_=lab;source=(root/path).read_bytes();row,calls=await ready(lab,monkeypatch)
        assert row['status']=='REVIEW_READY' and row['draft']==TEXT and row['calls']==3
        row=await done(s,p,s.feedback(p,row['id'],request(row)))
        assert row['status']=='REWORK_REVIEW' and row['feedback_state']['valid'] and row['feedback_proposal']['target']['quote']=='需要修改的中段。'
        proposal=row['feedback_proposal'];denied=FeedbackApproval(etag=row['etag'],proposal_id=proposal['id'],confirm=True)
        with pytest.raises(ConsoleError):s.approve_feedback(p,row['id'],denied)
        approved=s.approve_feedback(p,row['id'],FeedbackApproval(etag=row['etag'],proposal_id=proposal['id'],confirm=True,confirm_important=True,instruction='用更明确的动作回应，保持原有结果。'))
        assert approved['draft']==TEXT and approved['rewrite'] and len(calls)==4
        with pytest.raises(ConsoleError):s.approve_feedback(p,row['id'],denied)
        row=await done(s,p,await s.control(p,row['id'],body(approved,'run')))
        assert row['draft']==TEXT.replace('需要修改的中段。',NEW) and row['calls']==6 and row['status']=='REVIEW_READY'
        assert row['feedback_proposal']['status']=='APPLIED' and row['review_validity']['status']=='MATCHES_CANDIDATE'
        assert [v[0] for v in calls]==['PLAN','WRITE','REVIEW','FEEDBACK','WRITE','REVIEW']
        assert 'RAW_CHECKER_REPORT_MARKER' not in calls[4][1] and '用更明确的动作回应' in calls[4][1]
        assert (root/path).read_bytes()==source
    asyncio.run(run())

def test_missing_evidence_and_changed_proposals_cannot_execute(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row,calls=await ready(lab,monkeypatch)
        with pytest.raises(ConsoleError):s.feedback(p,row['id'],request(row,location=99))
        assert len(calls)==3
        row=await done(s,p,s.feedback(p,row['id'],request(row)));proposal=row['feedback_proposal'];row=s.patch(p,row['id'],Patch(etag=row['etag'],instruction='作者改变了本次目标。'))
        assert row['feedback_state']['status']=='HISTORICAL'
        with pytest.raises(ConsoleError):s.approve_feedback(p,row['id'],FeedbackApproval(etag=row['etag'],proposal_id=proposal['id'],confirm=True,confirm_important=True))
        assert row['draft']==TEXT and len(calls)==4
    asyncio.run(run())

def test_cancel_during_review_retains_prose_and_never_appends_report_json(lab,monkeypatch):
    async def run():
        calls=install(lab,monkeypatch,slow_review=True);s,p,*_=lab;row=start(lab,mode='quick');active=await s.control(p,row['id'],body(row,'run'))
        for _ in range(200):
            await asyncio.sleep(.01);row=s.get(p,row['id'])
            if any(k=='REVIEW' for k,_ in calls):break
        assert row['status']=='REVIEWING'
        await s.control(p,row['id'],body(row,'interrupt'));await s.manager(p).get(active['active_task']).runner
        result=s.get(p,row['id']);assert result['draft']==TEXT and 'REVIEW_JSON' not in result['draft'] and not result.get('review_id') and not result['active_task']
    asyncio.run(run())

def test_pause_blocks_automatic_review_and_author_can_take_over(lab,monkeypatch):
    async def run():
        calls=install(lab,monkeypatch,slow_writer=True);s,p,*_=lab;row=start(lab,mode='quick');active=await s.control(p,row['id'],body(row,'run'));await asyncio.sleep(.05);row=s.get(p,row['id']);await s.control(p,row['id'],body(row,'pause'));row=await done(s,p,active)
        assert [v[0] for v in calls]==['WRITE'] and row['draft']==TEXT
        row=s.patch(p,row['id'],Patch(etag=row['etag'],draft=TEXT+'作者接管。'));assert row['draft'].endswith('作者接管。')
    asyncio.run(run())

def test_rework_plan_cannot_smuggle_negative_secret_hints(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row,calls=await ready(lab,monkeypatch,secret=True);row=await done(s,p,s.feedback(p,row['id'],request(row)))
        assert row['status']=='FAILED' and not row.get('feedback_proposal') and row['draft']==TEXT
    asyncio.run(run())

def test_collaboration_profile_rejects_codex_as_api_writer(lab):
    with pytest.raises(ConsoleError):new(lab,collaboration='codex_api')


def test_planner_honors_explicit_timeout_and_classifies_transport_close(lab,monkeypatch):
    from types import SimpleNamespace
    calls=install(lab,monkeypatch);s,p,*_=lab
    class StalledPlanner(Fake):
        request_controls=SimpleNamespace(parameters={'timeout':5})
        def start_task(self,prompt,emit,**kw):
            self.stop.wait(8)
            raise RuntimeError('transport closed stdout')
    monkeypatch.setattr('app.creative.director.adapter',lambda *a,**kw:StalledPlanner(''))
    async def run():
        row=start(lab);row=await done(s,p,await s.control(p,row['id'],body(row,'plan')))
        assert row['status']=='FAILED' and row['failure']['code']=='TIMEOUT' and not row['failure']['automatic_retry']
        assert '超时' in row['last_error'] and row['calls']==1 and not row['draft']
    asyncio.run(run())


def test_feedback_http_route_owns_running_event_loop(lab,monkeypatch):
    from fastapi import FastAPI
    import httpx
    from app.creative.director import routes
    async def run():
        row,_=await ready(lab,monkeypatch);s,p,*_=lab;app=FastAPI();app.include_router(routes(s))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
            response=await c.post('/api/projects/'+p+'/creative-director/'+row['id']+'/feedback',json=request(row).model_dump())
        assert response.status_code==200
        result=await done(s,p,response.json());assert result['status']=='REWORK_REVIEW' and result['feedback_state']['valid']
    asyncio.run(run())


def test_ai_plan_cannot_silently_change_the_author_chosen_writer(lab,monkeypatch):
    install(lab,monkeypatch);s,p,*_=lab
    s.center.put(Provider(provider_id='other-api',display_name='MOCK other API',base_url='http://127.0.0.1:12346/v1',available_models=[Model(id='writer')]))
    class SwitchPlanner(Fake):
        def start_task(self,prompt,emit,**kw):
            return {'status':'completed','output':Plan(summary='MOCK recommendation',steps=[Step(title='scene',instruction='推进当前场景。',executor='other-api::writer')],methods=['context'],method_application=['遵循过滤资料'],recommended_executor='other-api::writer').model_dump_json()}
    monkeypatch.setattr('app.creative.director.adapter',lambda *a,**kw:SwitchPlanner(''))
    async def run():
        row=start(lab);row=await done(s,p,await s.control(p,row['id'],body(row,'plan')))
        assert row['status']=='PLAN_REVIEW' and row['executor']=='fixture-writer::writer'
        assert row['plan']['steps'][0]['executor'] is None and row['plan']['steps'][0]['request_controls'] is None
        assert row['plan']['recommended_executor']=='other-api::writer'
    asyncio.run(run())
