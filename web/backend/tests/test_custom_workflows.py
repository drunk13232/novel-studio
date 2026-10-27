"""Custom workflows: isolated real services + HTTP fixtures, never remote AI proof."""
import asyncio,copy,json,threading,time
import httpx,pytest
from openai import OpenAI
from pydantic import ValidationError
from test_creative_director import lab,fake
from app.creative.workflows import Workflows,Definition,Step,Save,RunCreate,Control,Edit,Design
from app.ai.models import Provider,Model,Parameters
from app.ai.controls import RequestControls
from app.errors import ConsoleError

def service(lab):
    d,p,root,path,doc,ctx=lab
    return Workflows(d,d.writing.world_studio),p,root,path,doc,ctx

def make(f,p,scope='world',steps=None,**kw):
    t=f.save(p,Save(definition=Definition(name='Original isolated workflow',scope=scope,steps=steps or [Step(kind='world_overview',title='World')])) )
    return t,f.create(p,RunCreate(template_id=t['id'],template_etag=t['etag'],goal='Only original isolated fixture content.',**kw))

def control(row,action='run',**kw):return Control(etag=row['etag'],action=action,confirm_send=True,**kw)
async def wait(f,p,row,timeout=10):
    for _ in range(int(timeout*50)):
        row=f.get(p,row['id'])
        if not row.get('active_task'):return row
        await asyncio.sleep(.02)
    raise AssertionError('Workflow did not settle')

def protocol(f,p,monkeypatch,slow=False):
    captured=[];interrupted=threading.Event()
    models=[Model(id=k,capabilities={'streaming':False,'tools':False,'structured':False,'temperature':True,'reasoning':False},parameters=Parameters(streaming=False)) for k in ['world-a','world-b']]
    f.center.put(Provider(provider_id='workflow_fixture',display_name='LOCAL HTTP MOCK ONLY',provider_type='lmstudio',base_url='http://127.0.0.1:1234/v1',available_models=models))
    def handler(req):
        body=json.loads(req.content);captured.append(body)
        if slow:time.sleep(.2)
        text=chr(10).join(m.get('content','') for m in body.get('messages',[]))
        if 'Write manuscript prose only' in text:
            result='江予把信纸折好。周栖仍在门口等着。'
        elif 'Evidence strings must be verbatim excerpts' in text:
            result={'verdict':'PASS','summary':'LOCAL MOCK review only','issues':[]}
        elif 'Design an editable Novel Studio workflow' in text:
            result=Definition(name='AI workflow proposal',scope='world',steps=[Step(kind='world_overview',title='AI world',pause_after=False,use_sources=True)]).model_dump()
        else:
            out_schema=json.loads(text.rsplit('仅返回以下 Schema 对应的 JSON，不使用 Markdown：'+chr(10),1)[1])
            category=out_schema['$defs']['Candidate']['properties']['category']['enum'][0]
            result={'summary':'LOCAL MOCK world proposal','questions':[],'unknowns':['External conditions remain unknown.'],'entries':[{'key':'fixture_world','name':'Original fixture world','category':category,'summary':'Original isolated islands.','details':'Not a real remote model result.','values':[]}],'relations':[],'limitations':['MOCK ONLY']}
        return httpx.Response(200,json={'id':'workflow-test','object':'chat.completion','created':1,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':result if isinstance(result,str) else json.dumps(result,ensure_ascii=False)},'finish_reason':'stop'}],'usage':{'prompt_tokens':40,'completion_tokens':30,'total_tokens':70}})
    def client(provider,key,timeout):return OpenAI(api_key='FIXTURE_NOT_REAL_KEY',base_url=provider.base_url,max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr('app.ai.provider.client',client)
    return captured

def test_definition_rejects_code_unknown_actions_duplicates_and_scope():
    with pytest.raises(ValidationError):Step(kind='shell',title='bad',command='remove')
    with pytest.raises(ValidationError):Definition(name='bad',scope='world',steps=[Step(kind='chapter_write',title='bad')])
    s=Step(kind='manual',title='human')
    with pytest.raises(ValidationError):Definition(name='bad',scope='world',steps=[s,s])
    with pytest.raises(ValidationError):Step(kind='manual',title='bad',controls={'api_key':'MUST_NOT_BE_ACCEPTED'})

def test_template_snapshot_versions_archive_and_cross_project_boundaries(lab):
    f,p,*_=service(lab);t,row=make(f,p)
    new=Definition.model_validate(t['definition']);new.name='Updated template';new.steps[0].instruction='New instruction'
    newer=f.save(p,Save(etag=t['etag'],definition=new),t['id'])
    assert newer['version']==2 and f.get(p,row['id'])['snapshot']['name']!='Updated template'
    assert f.template(p,t['id'])['versions'][0]['definition']['name']=='Original isolated workflow'
    with pytest.raises(ConsoleError):f.save(p,Save(etag=t['etag'],definition=new),t['id'])
    f.archive(p,t['id'],newer['etag']);assert not f.listing(p)['templates']
    assert f.get(p,row['id'])['template_name']=='Original isolated workflow'
    with pytest.raises(ConsoleError):f.get('novel_'+'f'*32,row['id'])
    exported=Definition.model_validate(newer['definition']).model_dump()
    assert 'project_id' not in exported and 'goal' not in exported and 'entity_ids' not in exported
    copy=f.save(p,Save(definition=Definition.model_validate(exported)));assert copy['id']!=t['id']

def test_manual_skip_disabled_steps_and_pending_edits(lab):
    f,p,*_=service(lab);t,row=make(f,p,steps=[Step(id='step_off',kind='manual',title='off',enabled=False),Step(id='step_human',kind='manual',title='human'),Step(id='step_last',kind='manual',title='last')])
    step=Step.model_validate(row['snapshot']['steps'][1]);step.instruction='Author directions'
    row=f.edit(p,row['id'],Edit(etag=row['etag'],step_id=step.id,step=step,handoff='Confirmed author handoff'))
    async def run():
        a=await f.control(p,row['id'],control(row));assert a['index']==2 and a['steps']['step_off']['status']=='SKIPPED'
        assert a['steps']['step_human']['result']['text']=='Confirmed author handoff'
        with pytest.raises(ConsoleError):f.edit(p,a['id'],Edit(etag=a['etag'],step_id=step.id,step=step))
        a=await f.control(p,a['id'],control(a,'skip'));assert a['status']=='COMPLETED' and a['calls']==0
    asyncio.run(run())

def test_real_domain_world_chain_http_fixture_models_and_explicit_confirmation(lab,monkeypatch):
    f,p,root,*_=service(lab);calls=protocol(f,p,monkeypatch)
    steps=[Step(id='step_one',kind='world_overview',title='Overview',model='workflow_fixture::world-a',pause_after=False,controls=RequestControls(parameters={'temperature':.25,'streaming':False})),Step(id='step_two',kind='world_rules',title='Rules',model='workflow_fixture::world-b',input_mode='previous',pause_after=False)]
    _,row=make(f,p,steps=steps);before={str(x.relative_to(root)):x.read_bytes() for x in root.rglob('*') if x.is_file() and x.relative_to(root).parts[0] in {'chapters','state','settings','characters'}}
    async def run():
        with pytest.raises(ConsoleError):await f.control(p,row['id'],Control(etag=row['etag'],action='run'))
        a=await f.control(p,row['id'],control(row,auto_continue=True));return await wait(f,p,a)
    result=asyncio.run(run());assert result['status']=='COMPLETED',result.get('last_error')
    assert [x['model'] for x in calls]==['world-a','world-b']
    assert calls[0]['temperature']==.25
    assert 'Original isolated islands' in json.dumps(calls[1],ensure_ascii=False)
    assert not f.world.bible.list(p)==[]  # existing original demo data, not adopted workflow entries
    assert all((root/name).read_bytes()==body for name,body in before.items())
    assert result['steps']['step_one']['result']['basis']=='WORLD_PROPOSAL'
    restarted=Workflows(f.director,f.world);assert restarted.get(p,result['id'])['status']=='COMPLETED'
    assert all(x['status']=='SUCCEEDED' for x in result['steps'].values())

def test_author_pause_and_cancel_do_not_advance_or_accept_late_results(lab,monkeypatch):
    f,p,*_=service(lab);calls=protocol(f,p,monkeypatch,True)
    steps=[Step(kind='world_overview',title='one',model='workflow_fixture::world-a',pause_after=False),Step(kind='world_overview',title='two',model='workflow_fixture::world-b',pause_after=False)]
    _,row=make(f,p,steps=steps)
    async def run():
        a=await f.control(p,row['id'],control(row,auto_continue=True));a=await f.control(p,a['id'],control(a,'pause'));a=await wait(f,p,a)
        assert a['index']==1 and a['status']=='WAITING' and len(calls)==1
        a=await f.control(p,a['id'],control(a));a=await f.control(p,a['id'],control(a,'stop'));a=await wait(f,p,a)
        assert a['status']=='CANCELLED' and a['index']==1
        with pytest.raises(ConsoleError):await f.control(p,row['id'],control(row))
        return a
    result=asyncio.run(run());assert result['steps'][steps[0].id]['status']=='SUCCEEDED'

def test_retry_only_failed_current_step_and_missing_previous_is_not_fabricated(lab,monkeypatch):
    f,p,*_=service(lab);calls=protocol(f,p,monkeypatch)
    _,row=make(f,p,steps=[Step(kind='manual',title='empty',enabled=False),Step(kind='world_rules',title='needs prior',model='workflow_fixture::world-a',input_mode='previous')])
    async def run():
        with pytest.raises(ConsoleError):await f.control(p,row['id'],control(row))
        a=f.get(p,row['id']);assert a['status']=='FAILED' and not calls
        step=Step.model_validate(a['snapshot']['steps'][a['index']]);step.input_mode='goal'
        a=f.edit(p,a['id'],Edit(etag=a['etag'],step_id=step.id,step=step));a=await f.control(p,a['id'],control(a));return await wait(f,p,a)
    result=asyncio.run(run());assert result['status']=='COMPLETED' and len(calls)==1

def test_chapter_flow_uses_existing_candidate_without_manuscript_writes(lab,monkeypatch):
    f,p,root,path,doc,ctx=service(lab);calls=fake(monkeypatch)
    _,row=make(f,p,'chapter',steps=[Step(kind='chapter_write',title='Draft')],path=path,revision=doc['etag'],context_id=ctx['id'])
    before=(root/path).read_bytes()
    async def run():
        a=await f.control(p,row['id'],control(row));return await wait(f,p,a)
    a=asyncio.run(run());assert a['status']=='COMPLETED',a['last_error']
    assert len(calls)==1 and a['steps'][row['snapshot']['steps'][0]['id']]['result']['kind']=='director'
    assert (root/path).read_bytes()==before
    assert f.director.get(p,a['steps'][row['snapshot']['steps'][0]['id']]['result']['id'])['status']=='CANDIDATE'

def test_restart_recovery_never_replays_unknown_task(lab):
    f,p,*_=service(lab);_,row=make(f,p)
    row.update(status='RUNNING',active_task='nonexistent_task');f.put(p,row,'runs')
    restarted=Workflows(f.director,f.world);v=restarted.get(p,row['id']);assert v['status']=='PAUSED' and not v['active_task'] and v['auto_continue'] is False

def test_ai_design_produces_sanitized_template_and_never_executes(lab,monkeypatch):
    f,p,*_=service(lab);calls=protocol(f,p,monkeypatch)
    async def run():
        t=f.design(p,Design(goal='Build a world only; no characters.',scope='world',controls=RequestControls(model='workflow_fixture::world-a'),confirm_send=True));await f.manager(p).get(t['id']).runner;return f.manager(p).get(t['id'])
    t=asyncio.run(run());assert t.status=='SUCCEEDED',t.error
    saved=f.template(p,t.result['template_id']);assert saved['definition']['steps'][0]['pause_after'] is True
    assert saved['definition']['steps'][0]['use_sources'] is False
    assert len(calls)==1 and not f.listing(p)['runs']


def test_candidate_review_is_separate_and_cannot_automatically_reenter_writer(lab,monkeypatch):
    f,p,root,path,doc,ctx=service(lab);calls=protocol(f,p,monkeypatch);writer=fake(monkeypatch)
    steps=[Step(id='step_draft',kind='chapter_write',title='Draft',pause_after=False),Step(id='step_review',kind='chapter_review',title='Review',model='workflow_fixture::world-a',input_mode='previous',pause_after=False,controls=RequestControls(context={'budget':131072})),Step(id='step_unsafe',kind='chapter_write',title='Not allowed to import reviewer secrets',input_mode='previous')]
    _,row=make(f,p,'chapter',steps=steps,path=path,revision=doc['etag'],context_id=ctx['id']);before=(root/path).read_bytes()
    async def run():
        a=await f.control(p,row['id'],control(row,auto_continue=True));return await wait(f,p,a)
    a=asyncio.run(run());assert a['status']=='FAILED' and a['index']==2,a['last_error']
    assert len(writer)==1 and len(calls)==1
    assert a['steps']['step_review']['result']['basis']=='REVIEW_NOT_WRITER_CONTEXT'
    assert (root/path).read_bytes()==before


def test_disabled_final_step_does_not_leave_an_artificial_confirmation(lab,monkeypatch):
    f,p,*_=service(lab);protocol(f,p,monkeypatch)
    _,row=make(f,p,steps=[Step(kind='world_overview',title='only',model='workflow_fixture::world-a'),Step(id='step_off',kind='manual',title='off',enabled=False)])
    async def run():return await wait(f,p,await f.control(p,row['id'],control(row)))
    a=asyncio.run(run());assert a['status']=='COMPLETED' and a['steps']['step_off']['status']=='SKIPPED'


def test_cancelled_writer_retains_prefix_and_retry_does_not_replay_completed_steps(lab,monkeypatch):
    f,p,root,path,doc,ctx=service(lab);calls=fake(monkeypatch,True)
    _,row=make(f,p,'chapter',steps=[Step(kind='manual',title='human'),Step(id='step_writer',kind='chapter_write',title='Draft')],path=path,revision=doc['etag'],context_id=ctx['id'])
    before=(root/path).read_bytes()
    async def run():
        a=await f.control(p,row['id'],control(row));a=await f.control(p,a['id'],control(a))
        for _ in range(100):
            await asyncio.sleep(.02)
            d=f.director.get(p,a['active_operation']['id'])
            if d.get('partial'):break
        a=await f.control(p,a['id'],control(a,'stop'));a=await wait(f,p,a)
        kept=a['steps']['step_writer']['result']['text'];assert kept
        assert a['steps']['step_writer']['status']=='CANCELLED'
        a=await f.control(p,a['id'],control(a));a=await wait(f,p,a)
        assert a['steps']['step_writer']['result']['text'].startswith(kept)
        assert a['steps']['step_writer']['attempt_history'][0]['result']['text']==kept
        assert a['calls']==2 and len(calls)==2
        return a
    result=asyncio.run(run());assert result['status']=='COMPLETED' and (root/path).read_bytes()==before


def test_actual_writer_http_request_uses_step_parameters_and_context_budget(lab,monkeypatch):
    f,p,root,path,doc,ctx=service(lab);calls=protocol(f,p,monkeypatch)
    controls=RequestControls(parameters={'temperature':.15,'streaming':False},context={'budget':131072})
    _,row=make(f,p,'chapter',steps=[Step(kind='chapter_write',title='Writer controls',model='workflow_fixture::world-b',controls=controls)],path=path,revision=doc['etag'],context_id=ctx['id'])
    original=(root/path).read_bytes()
    async def run():return await wait(f,p,await f.control(p,row['id'],control(row)))
    a=asyncio.run(run());assert a['status']=='COMPLETED',a['last_error']
    assert len(calls)==1 and calls[0]['model']=='world-b' and calls[0]['temperature']==.15
    assert a['steps'][row['snapshot']['steps'][0]['id']]['result']['ai']['backend']=='llm'
    assert (root/path).read_bytes()==original


def test_small_context_budget_fails_before_sending_and_never_drops_writer_safety(lab,monkeypatch):
    f,p,root,path,doc,ctx=service(lab);calls=protocol(f,p,monkeypatch)
    _,row=make(f,p,'chapter',steps=[Step(kind='chapter_write',title='Too small',model='workflow_fixture::world-a',controls=RequestControls(context={'budget':1024}))],path=path,revision=doc['etag'],context_id=ctx['id'])
    async def run():
        with pytest.raises(ConsoleError):await f.control(p,row['id'],control(row))
    asyncio.run(run());assert not calls and f.get(p,row['id'])['status']=='FAILED'


def test_local_proofread_is_a_real_local_report_without_ai_or_writer_approval(lab,monkeypatch):
    f,p,root,path,doc,ctx=service(lab)
    def forbidden(*args,**kwargs):raise AssertionError('Local-only flow must not initialize an AI adapter')
    monkeypatch.setattr('app.creative.tasks.adapter',forbidden)
    _,row=make(f,p,'chapter',steps=[Step(kind='local_proofread',title='Local only')],path=path,revision=doc['etag'])
    before=(root/path).read_bytes()
    result=asyncio.run(f.control(p,row['id'],control(row)))
    assert result['status']=='COMPLETED' and not result['active_task']
    saved=result['steps'][row['snapshot']['steps'][0]['id']]['result']
    assert saved['ai']['backend']=='local' and saved['kind']=='review'
    assert (root/path).read_bytes()==before
