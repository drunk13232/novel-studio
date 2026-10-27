"""Request-level correctness. MockTransport tests are protocol MOCK, not remote AI."""
import asyncio,copy,json,shutil,threading
from pathlib import Path
from types import SimpleNamespace
import httpx,pytest
from openai import OpenAI
from app.ai.center import AICenter
from app.ai.controls import ContextPolicy,RequestControls,ControlSave,build,item
from app.ai.models import Provider,Model,Parameters
from app.ai.parameters import request_arguments
from app.ai.provider import LLMProviderAdapter
from app.errors import ConsoleError
from app.projects.creation import Creation,CreationEdit,InterviewRequest
from app.projects.models import Idea
from app.projects.service import DraftStore,NovelWorkspace
from app.tasks.manager import TaskManager
from app.tasks.router import TaskRouter
ROOT=Path(__file__).resolve().parents[3]

def model(id='model-a',protocol='chat'):
    return Model(id=id,protocol=protocol,context_length=65536,chat_token_parameter='max_completion_tokens',reasoning_levels=['low','high'],capability_source='USER',capabilities={'reasoning':True,'streaming':True,'temperature':False},parameters=Parameters(streaming=False))

@pytest.fixture
def center(tmp_path):
    engine=tmp_path/'engine';engine.mkdir();skill=engine/'.agents/skills/novel-story-architect';skill.mkdir(parents=True)
    shutil.copyfile(ROOT/'.agents/skills/novel-story-architect/SKILL.md',skill/'SKILL.md')
    c=AICenter(tmp_path/'data',SimpleNamespace(engine=engine,rows={}),None)
    p=Provider(provider_id='local',display_name='MOCK protocol fixture',base_url='http://127.0.0.1:12345/v1',available_models=[model(),model('model-b'),model('response-a','responses')])
    c.put(p);return c

def response(request,body,stream=False):
    if request.url.path.endswith('/responses'):
        return httpx.Response(200,json={'id':'resp-test','object':'response','created_at':1,'model':body['model'],'status':'completed','output':[{'id':'msg-test','type':'message','status':'completed','role':'assistant','content':[{'type':'output_text','text':'OK','annotations':[]}]}],'usage':{'input_tokens':10,'output_tokens':2,'total_tokens':12}})
    text=json.dumps({'message':'隔离测试回复。','layer':'方向','question':None,'suggestions':[],'issues':[],'cover_concepts':[]},ensure_ascii=False)
    return httpx.Response(200,json={'id':'chat-test','object':'chat.completion','created':1,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}})

def transport(monkeypatch,requests):
    def handler(request):
        body=json.loads(request.content);requests.append(body);return response(request,body)
    def client(p,key,timeout):return OpenAI(api_key='LOCAL_TEST_KEY_NOT_A_SECRET',base_url=p.base_url,max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr('app.ai.provider.client',client)

def test_context_budget_changes_payload_and_preserves_pins():
    sources=[item('task','task','必要任务','检查逻辑',required=True),item('rule','world','固定规则','必须保留的规则',locked=True)]
    sources += [item('m'+str(i),'history','历史',str(i)+'字'*700) for i in range(12)]
    a=build(sources,ContextPolicy(budget=8192,output_reserve=1024,history='all'))
    b=build(sources,ContextPolicy(budget=32768,output_reserve=1024,history='all'))
    assert a['input_estimate']+a['output_reserve']<=8192
    assert len(a['items'])<len(b['items']) and any(i['reason']=='TOTAL_BUDGET' for i in a['excluded'])
    assert {'task','rule'}<={v['id'] for v in a['items']}
    assert a['prompt']!=b['prompt']
    with pytest.raises(ConsoleError):build(sources,ContextPolicy(budget=1024,output_reserve=1000))
    with pytest.raises(ConsoleError):build(sources,ContextPolicy(pins=['not-authorized']))

def test_manual_sources_exclusions_and_known_model_cap():
    sources=[item('task','task','必要','本次指令',required=True),item('person','characters','人物','ALLOWED_PERSON'),item('ref','references','文献','EXCLUDED_REFERENCE'),item('rule','world','世界规则','LOCKED_RULE')]
    p=ContextPolicy(mode='manual',budget=65536,output_reserve=1024,include=['person'],exclude=['ref'],pins=['rule'])
    r=build(sources,p,8192)
    assert r['user_budget']==65536 and r['effective_budget']==8192 and r['model_limit']==8192
    assert 'ALLOWED_PERSON' in r['prompt'] and 'LOCKED_RULE' in r['prompt'] and 'EXCLUDED_REFERENCE' not in r['prompt']
    assert sources[1]['content']=='ALLOWED_PERSON'

@pytest.mark.parametrize('mode,expected',[('off',{'m0'}),('messages',{'m0','m5'}),('turns',{'m0','m4','m5'}),('manual',{'m0','m3'}),('all',{'m0','m1','m2','m3','m4','m5'})])
def test_history_selection_never_deletes_original(mode,expected):
    sources=[item('m'+str(i),'history','消息',str(i)) for i in range(6)]
    before=copy.deepcopy(sources);r=build(sources,ContextPolicy(history=mode,history_limit=1,pins=['m0'],include=['m3'] if mode=='manual' else []))
    assert {r['id'] for r in r['items']}==expected and sources==before

def test_unknown_and_ineffective_parameters_are_rejected():
    p=Provider(provider_id='p',display_name='test',base_url='https://api.example.com/v1');m=model()
    with pytest.raises(ConsoleError):request_arguments(p,m,Parameters(reasoning_effort='medium'))
    with pytest.raises(ConsoleError):request_arguments(p,m,Parameters(temperature=.5))
    with pytest.raises(ConsoleError):request_arguments(p,m,Parameters(top_p=.5))
    p.provider_type='deepseek';p.base_url='https://api.deepseek.com/v1';m.reasoning_levels=['none','low','high','max'];m.capabilities['temperature']=True
    args=request_arguments(p,m,Parameters(reasoning_effort='high'))
    assert args['reasoning_effort']=='high' and args['extra_body']=={'thinking':{'type':'enabled'}}
    with pytest.raises(ConsoleError):request_arguments(p,m,Parameters(temperature=.5,reasoning_effort='high'))
    assert request_arguments(p,m,Parameters(reasoning_effort='none'))['extra_body']['thinking']['type']=='disabled'

def test_precise_models_and_protocol_effort_reach_official_sdk(center,monkeypatch):
    captured=[];transport(monkeypatch,captured)
    for id,effort in [('model-a','low'),('model-b','high'),('response-a','low')]:
        a=center.adapter('scope','brainstorm','PUBLIC_FIXTURE',f'local::{id}',Parameters(reasoning_effort=effort,streaming=False))
        result=a.start_task('PUBLIC_FIXTURE',lambda *a:None)
        assert result['status']=='completed' and a.metadata['observed_model']==id
    assert [r['model'] for r in captured]==['model-a','model-b','response-a']
    assert captured[0]['reasoning_effort']=='low' and captured[1]['reasoning_effort']=='high'
    assert captured[2]['reasoning']=={'effort':'low'} and captured[2]['store'] is False
    assert 'reasoning_content' not in str(captured)

def test_configuration_precedence_and_restart(center):
    c=center
    c.put_controls(ControlSave(scope='global',value={'model':'local::model-a','context':{'budget':8192}}))
    c.put_controls(ControlSave(scope='feature',feature='brainstorm',value={'parameters':{'reasoning_effort':'low'},'context':{'budget':16384}}))
    c.put_controls(ControlSave(scope='session',feature='brainstorm',session='conversation',value={'model':'local::model-b','parameters':{'reasoning_effort':'high'}}))
    r=c.controls_for('','brainstorm','conversation',{'context':{'budget':32768}})
    assert r.model=='local::model-b' and r.parameters['reasoning_effort']=='high' and r.context.budget==32768
    restored=AICenter(c.root,c.registry,None).controls_for('','brainstorm','conversation')
    assert restored.model=='local::model-b' and restored.context.budget==16384
    assert 'LOCAL_TEST_KEY_NOT_A_SECRET' not in (c.root/'ai-settings.json').read_text('utf8')
    with pytest.raises(ConsoleError):c.put_controls(ControlSave(scope='feature',project='other-project',value={}))

def creation(center):
    d=DraftStore(center.registry.engine);center.drafts=d;row=d.create(Idea(title='Original local fixture',idea='一封没有寄出的信。'))
    c=Creation(d,None);ws=NovelWorkspace(d.path(row['id']));m=TaskManager(ws,TaskRouter(ws,center.registry.engine),center.registry.engine);m.ai_center=center
    return c,d,row,m

def test_creation_preview_is_local_exact_and_history_switches_models(center,monkeypatch):
    captured=[];transport(monkeypatch,captured);c,d,row,m=creation(center);id=row['id']
    controls=RequestControls(model='local::model-a',parameters={'streaming':False,'reasoning_effort':'low'})
    r=InterviewRequest(version=row['version'],mode='answer',message='讨论信件，不补造既定事实。',ai_controls=controls)
    before=d.get(id);packet=c.start(id,r,m,preview=True)
    assert d.get(id)==before and not captured and '讨论信件' in packet['prompt']
    assert c.start(id,r,m,preview=True)['prompt_sha256']==packet['prompt_sha256']
    r.preview_sha256=packet['prompt_sha256']
    async def turn(req):
        t=c.start(id,req,m);await t.runner;assert t.status=='SUCCEEDED',t.error;return t
    first=asyncio.run(turn(r));assert captured[0]['model']=='model-a'
    row=d.get(id);controls.model='local::model-b';controls.parameters['reasoning_effort']='high'
    second=asyncio.run(turn(InterviewRequest(version=row['version'],mode='answer',message='继续讨论，同一段会话。',ai_controls=controls)))
    messages=c.view(id)['creation']['messages'];ai=[x for x in messages if x['role']=='assistant']
    assert len(ai)==2 and [x['ai']['request_model'] for x in ai]==['model-a','model-b']
    assert '隔离测试回复' in captured[1]['messages'][0]['content']
    assert first.ai_metadata['effective_parameters']['reasoning_effort']=='low'
    assert second.ai_metadata['effective_parameters']['reasoning_effort']=='high'
    restored=Creation(DraftStore(center.registry.engine),None).view(id)
    assert restored['creation']['messages']==messages

def test_generation_author_edit_is_preserved_and_old_suggestion_is_stale(center,monkeypatch):
    c,d,row,m=creation(center);id=row['id'];captured=[];transport(monkeypatch,captured)
    def reply(request,body,stream=False):
        latest=d.get(id);c.edit(id,CreationEdit(version=latest['version'],action='field',field_id='world',value='作者在生成期间写下的新世界设定。'))
        data={'message':'旧输入下的回复。','layer':'方向','question':None,'suggestions':[{'field_id':'world','value':'OLD_AI_OVERWRITE','source':'AI_SUGGESTED','source_quote':'','related_message_id':''}],'issues':[],'cover_concepts':[]}
        return httpx.Response(200,json={'id':'test','object':'chat.completion','created':1,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(data,ensure_ascii=False)},'finish_reason':'stop'}]})
    monkeypatch.setattr(__name__+'.response',reply)
    async def execute():
        t=c.start(id,InterviewRequest(version=row['version'],mode='answer',message='讨论世界',ai_controls=RequestControls(model='local::model-a',parameters={'streaming':False})),m);await t.runner;return t
    t=asyncio.run(execute());assert t.status=='SUCCEEDED',t.error
    state=c.view(id)['creation'];assert state['fields']['world']['value']=='作者在生成期间写下的新世界设定。'
    assert state['messages'][-1]['possibly_stale'] and 'OLD_AI_OVERWRITE' not in state['fields']['world']['value']

def test_streaming_cancel_retains_prefix_and_frozen_parameters(center,monkeypatch):
    captured=[]
    events=[]
    def handler(request):
        captured.append(json.loads(request.content))
        rows=[{'id':'s','object':'chat.completion.chunk','created':1,'model':'model-a','choices':[{'index':0,'delta':{'content':text},'finish_reason':None}]} for text in ['已生成片段','不应追加的迟到片段']]
        return httpx.Response(200,headers={'Content-Type':'text/event-stream'},content=''.join('data: '+json.dumps(r,ensure_ascii=False)+'\n\n' for r in rows).encode())
    monkeypatch.setattr('app.ai.provider.client',lambda p,k,t:OpenAI(api_key='mock',base_url=p.base_url,max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    a=center.adapter('scope','brainstorm','PUBLIC',override='local::model-a',params=Parameters(streaming=True,reasoning_effort='low'))
    # Editing a later preference cannot mutate this already-created adapter.
    center.put_controls(ControlSave(scope='feature',feature='brainstorm',value={'model':'local::model-b','parameters':{'reasoning_effort':'high'}}))
    def emit(kind,message,data):
        events.append(kind)
        if kind=='llm_delta':a.close()
    result=a.start_task('PUBLIC',emit)
    assert result['status']=='interrupted' and result['output']=='已生成片段'
    assert captured[0]['model']=='model-a' and captured[0]['reasoning_effort']=='low'
    assert events.count('llm_delta')==1

def test_summary_memory_and_branch_reopen_do_not_replace_history(center):
    c,d,row,m=creation(center);id=row['id'];value=c.view(id)['creation']
    value['messages']=[{'id':'m0','role':'user','content':'作者只确认方向。','timestamp':'2026-10-17T01:00:00Z'},{'id':'m1','role':'assistant','content':'这是建议，不是事实。','timestamp':'2026-10-17T01:00:01Z','ai':{'model':'model-a'}}]
    row=d.update(id,row['version'],creation=value)
    row=c.edit(id,CreationEdit(version=row['version'],action='summary',value='待讨论的创作方向。',source_message_ids=['m0','m1']))
    row=c.edit(id,CreationEdit(version=row['version'],action='memory',value='作者希望保留留白。',source_message_ids=['m0']))
    branch=c.branch(id,row['version'])
    assert branch['id']!=id and branch['creation']['active_task'] is None
    restored=Creation(DraftStore(center.registry.engine),None).view(id)['creation']
    assert len(restored['messages'])==2 and restored['summaries'][0]['source_message_ids']==['m0','m1']
    assert restored['memory_candidates'][0]['canon'] is False
    assert branch['creation']['branch_of']['draft_id']==id


def test_specific_codex_routes_persist_and_agent_work_stays_codex(center):
    from app.ai.models import SettingsUpdate
    settings=center.settings();settings.codex_models=[{'id':'catalog-codex-a','reasoning_levels':['low','high']}];center.save(settings)
    center.registry.rows={'fixture-project':{}}
    ref='codex::catalog-codex-a'
    center.update(SettingsUpdate(default=ref,routes={'workflow':ref,'polish':ref},projects={'fixture-project':{'files':ref,'default':ref}}))
    restored=AICenter(center.root,center.registry,None)
    assert restored.selection('fixture-project','files')==ref
    assert restored.selection('','workflow')==ref
    adapter=SimpleNamespace()
    restored.configure_codex(adapter,'','workflow',RequestControls(parameters={'reasoning_effort':'high'}))
    assert adapter.model_id=='catalog-codex-a' and adapter.reasoning_effort=='high'
    before=center.settings().model_dump()
    with pytest.raises(ConsoleError):center.update(SettingsUpdate(default=ref,routes={'workflow':'local::model-a'}))
    with pytest.raises(ConsoleError):center.update(SettingsUpdate(default='codex::not-in-catalog'))
    assert center.settings().model_dump()==before


def test_empty_codex_discovery_keeps_saved_models(center,monkeypatch):
    settings=center.settings();settings.codex_models=[{'id':'kept-model','reasoning_levels':['low'],'favorite':True}];center.save(settings)
    monkeypatch.setattr('app.codex.adapter.CodexAdapter.models',lambda self:{'data':[]})
    with pytest.raises(ConsoleError,match='空模型目录'):center.discover_codex()
    assert center.settings().codex_models==settings.codex_models


def test_discovered_default_and_efforts_come_from_metadata(center,monkeypatch):
    result={'data':[{'id':'catalog-id','model':'wire-model-id','displayName':'Model from official fixture','isDefault':True,'supportedReasoningEfforts':[{'reasoningEffort':'high'}],'defaultReasoningEffort':'high'}]}
    monkeypatch.setattr('app.codex.adapter.CodexAdapter.models',lambda self:result)
    row=center.discover_codex()['models'][0]
    assert row['ref']=='codex::wire-model-id' and row['is_default'] is True
    assert row['reasoning_levels']==['high'] and row['default_reasoning_effort']=='high'
