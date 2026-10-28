"""Director console: real local services/WASI, HTTP protocol fixtures marked MOCK."""
import asyncio,copy,json
import httpx,pytest
from openai import OpenAI
from test_creative_director import lab,new,body,done,fake
from app.creative.director import Patch,Plan,Step
from app.ai.controls import RequestControls
from app.ai.models import Provider,Model,Parameters
from app.errors import ConsoleError


def protocol(s,monkeypatch):
    calls=[]
    models=[Model(id=k,capabilities={'streaming':False,'temperature':True,'reasoning':True},reasoning_levels=['low','high'],chat_token_parameter='max_completion_tokens',parameters=Parameters(streaming=False)) for k in ('planner','writer')]
    s.center.put(Provider(provider_id='console_fixture',display_name='LOCAL MOCK ONLY',provider_type='lmstudio',base_url='http://127.0.0.1:1234/v1',available_models=models))
    def handler(request):
        data=json.loads(request.content);calls.append(data)
        result=Plan(summary='Fixture plan only',steps=[Step(title='Dialogue',instruction='Continue the permitted scene.')],methods=['context','scene','character'],method_application=['Context','Scene','Character']).model_dump_json() if data['model']=='planner' else '江予将信纸折好。周栖仍在门边等待。'
        return httpx.Response(200,json={'id':'console-fixture','object':'chat.completion','created':1,'model':data['model'],'choices':[{'index':0,'message':{'role':'assistant','content':result},'finish_reason':'stop'}],'usage':{'prompt_tokens':40,'completion_tokens':20,'total_tokens':60}})
    monkeypatch.setattr('app.ai.provider.client',lambda provider,key,timeout:OpenAI(api_key='FIXTURE_NOT_REAL_KEY',base_url=provider.base_url,max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    return calls


def test_independent_controls_reach_official_sdk_request_and_receipts(lab,monkeypatch):
    s,p,pr,path,doc,ctx=lab;calls=protocol(s,monkeypatch);original=(pr/path).read_bytes()
    async def run():
        row=new(lab,'director',executor='console_fixture::writer',commander='console_fixture::planner',request_controls=RequestControls(parameters={'temperature':.2,'reasoning_effort':'low','max_output_tokens':256},context={'budget':131072}),commander_controls=RequestControls(parameters={'temperature':.7,'reasoning_effort':'high','max_output_tokens':800},context={'budget':131072}))
        row=await done(s,p,await s.control(p,row['id'],body(row,'plan')))
        assert row['status']=='PLAN_REVIEW',row
        row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        assert row['status']=='CANDIDATE',row
        assert [c['model'] for c in calls]==['planner','writer']
        assert [c['temperature'] for c in calls]==[.7,.2]
        assert [c['reasoning_effort'] for c in calls]==['high','low']
        assert [c['max_completion_tokens'] for c in calls]==[800,256]
        assert row['usage'][0]['receipt']['effective_parameters']['temperature']==.7
        assert row['usage'][1]['receipt']['effective_parameters']['temperature']==.2
        assert row['usage'][1]['receipt']['context']['user_budget']==131072
        assert (pr/path).read_bytes()==original
    asyncio.run(run())


def test_controls_patch_roundtrip_legacy_fallback_and_stale_guard(lab,monkeypatch):
    s,p,*_=lab;fake(monkeypatch)
    row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],request_controls=RequestControls(parameters={'timeout':60}),commander_controls=RequestControls(parameters={'timeout':45})))
    assert s.get(p,row['id'])['request_controls']['parameters']['timeout']==60
    assert row['commander_controls']['parameters']['timeout']==45
    row.pop('controls_version',None);row.pop('commander_controls',None);s.put(p,row);row=s.get(p,row['id'])
    row=s.patch(p,row['id'],Patch(etag=row['etag'],request_controls=RequestControls(parameters={'timeout':80})))
    assert row['controls_version']==2 and row['commander_controls']['parameters']['timeout']==60
    assert row['request_controls']['parameters']['timeout']==80
    previous=copy.deepcopy(row)
    row=s.patch(p,row['id'],Patch(etag=row['etag'],instruction='Preserve the approved dialogue.'))
    with pytest.raises(ConsoleError):s.patch(p,row['id'],Patch(etag=previous['etag'],goal='stale overwrite'))
    assert s.get(p,row['id'])['goal']==row['goal']


def test_snapshot_is_fixed_scoped_and_excludes_context_packet(lab,monkeypatch):
    s,p,*_=lab;fake(monkeypatch)
    async def run():
        row=new(lab);row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        value=s.snapshot(p,row['id'],row['etag']);original=copy.deepcopy(value)
        assert 'context_id' not in value and 'context' not in value and 'WriterView' not in value
        value['draft']='tampered only in returned object'
        assert s.snapshot(p,row['id'],row['etag'])['draft']==original['draft']
        changed=s.patch(p,row['id'],Patch(etag=row['etag'],draft=row['draft']+'作者另存。'))
        with pytest.raises(ConsoleError):s.snapshot(p,row['id'],row['etag'])
        with pytest.raises(ConsoleError):s.snapshot('another-project',changed['id'],changed['etag'])
    asyncio.run(run())


def test_active_and_empty_candidates_cannot_be_handed_off(lab,monkeypatch):
    s,p,*_=lab;fake(monkeypatch,True);row=new(lab)
    with pytest.raises(ConsoleError):s.snapshot(p,row['id'],row['etag'])
    async def run():
        running=await s.control(p,row['id'],body(row,'run'))
        with pytest.raises(ConsoleError):s.snapshot(p,running['id'],running['etag'])
        stopped=await s.control(p,row['id'],body(s.get(p,row['id']),'interrupt'))
        await s.manager(p).get(running['active_task']).runner
    asyncio.run(run())
