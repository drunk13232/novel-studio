"""World-first correctness. HTTP MockTransport is MOCK, never remote AI proof."""
import asyncio,copy,json
import httpx,pytest,yaml
from test_ai_controls import center,creation,transport
from test_projects import setup
from test_world_studio import service,setup as world_setup,capture
from app.ai.controls import RequestControls,ControlSave
from app.ai.world_start import WORLD_START_FIELDS
from app.projects.creation import Creation,CreationEdit,InterviewRequest
from app.projects.models import Idea,ProjectCreate
from app.library.world_studio import Design,Start
from app.errors import ConsoleError

def edit(c,d,id,action,**kw):
    return c.edit(id,CreationEdit(version=d.get(id)['version'],action=action,**kw))

def test_world_scope_is_persisted_bounded_and_does_not_require_story_skill(center):
    c,d,row,m=creation(center);id=row['id']
    edit(c,d,id,'field',field_id='protagonist',value='STORY_CHARACTER_NOT_IN_WORLD_CONTEXT')
    edit(c,d,id,'field',field_id='themes',value='LITERARY_THEME_NOT_IN_WORLD_CONTEXT')
    raw=d.get(id);raw['creation']['messages']=[{'id':'old_story','role':'assistant','content':'OLD_STORY_CONVERSATION','timestamp':'2026-01-01'}];d.persist(raw)
    edit(c,d,id,'focus',value='world');edit(c,d,id,'description',value='构建一个有浮岛的虚构世界，先给可编辑概览。')
    (d.engine/'.agents/skills/novel-story-architect/SKILL.md').unlink()
    row=c.view(id);assert {v['field_id'] for v in row['catalog']}==WORLD_START_FIELDS
    before=d.get(id)
    packet=c.start(id,InterviewRequest(version=row['version'],mode='analyze',ai_controls=RequestControls(model='local::model-a',parameters={'streaming':False})),m,preview=True)
    assert d.get(id)==before
    assert 'World-first creation' in packet['prompt']
    assert not any(x in packet['prompt'] for x in ['STORY_CHARACTER_NOT_IN_WORLD_CONTEXT','LITERARY_THEME_NOT_IN_WORLD_CONTEXT','OLD_STORY_CONVERSATION'])
    restored=Creation(type(d)(d.engine),None).view(id);assert restored['creation']['focus']=='world'
    with pytest.raises(ConsoleError):c.start(id,InterviewRequest(version=row['version'],mode='refine',field_id='protagonist'),m,preview=True)

def test_world_mock_generation_routes_world_and_requires_author_acceptance(center,monkeypatch):
    captured=[];transport(monkeypatch,captured);c,d,row,m=creation(center);id=row['id']
    edit(c,d,id,'focus',value='world')
    def response(request,body,stream=False):
        value={'message':'世界概览候选。','layer':'世界观','question':None,'suggestions':[{'field_id':'world','value':'虚构浮岛通过固定航线相连。','source':'AI_SUGGESTED','source_quote':'','related_message_id':''}],'issues':[],'cover_concepts':[]}
        return httpx.Response(200,json={'id':'fixture','object':'chat.completion','created':1,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(value,ensure_ascii=False)},'finish_reason':'stop'}]})
    monkeypatch.setattr('test_ai_controls.response',response)
    async def run():
        t=c.start(id,InterviewRequest(version=d.get(id)['version'],mode='analyze',ai_controls=RequestControls(model='local::model-a',parameters={'streaming':False})),m)
        await t.runner;return t
    t=asyncio.run(run());assert t.status=='SUCCEEDED',t.error
    state=c.view(id)['creation'];assert state['fields']['world']['status']=='AI_SUGGESTED'
    assert state['fields']['protagonist']['status']=='EMPTY' and state['fields']['themes']['status']=='EMPTY'
    assert state['messages'][-1]['focus']=='world'
    assert 'World-first creation' in json.dumps(captured,ensure_ascii=False)
    sent_schema=json.loads(captured[0]['messages'][0]['content'].rsplit('仅返回以下 Schema 对应的 JSON，不使用 Markdown：'+chr(10),1)[1])
    assert sent_schema['$defs']['Suggestion']['properties']['field_id']['enum']==sorted(WORLD_START_FIELDS)
    assert 'response_format' not in captured[0]  # Unknown native schema capability is not fabricated.
    assert not list((d.engine/'projects').glob('novel_*')) if (d.engine/'projects').exists() else True
    edit(c,d,id,'accept',field_id='world');assert c.view(id)['creation']['fields']['world']['status']=='USER_CONFIRMED'

def test_world_response_rejects_character_fields(center,monkeypatch):
    captured=[];transport(monkeypatch,captured);c,d,row,m=creation(center);id=row['id'];edit(c,d,id,'focus',value='world')
    def response(request,body,stream=False):
        value={'message':'This is an invalid character suggestion.','layer':'世界观','question':None,'suggestions':[{'field_id':'protagonist','value':'MUST_NOT_BE_APPLIED','source':'AI_SUGGESTED'}],'issues':[],'cover_concepts':[]}
        return httpx.Response(200,json={'id':'fixture','object':'chat.completion','created':1,'model':body['model'],'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(value)},'finish_reason':'stop'}]})
    monkeypatch.setattr('test_ai_controls.response',response)
    async def run():
        t=c.start(id,InterviewRequest(version=d.get(id)['version'],mode='analyze',ai_controls=RequestControls(model='local::model-a',parameters={'streaming':False})),m);await t.runner;return t
    asyncio.run(run());state=c.view(id)['creation'];assert state['extraction_error'] and state['fields']['protagonist']['value']==''

def test_world_project_has_no_placeholder_cast_outline_or_committed_facts(setup):
    client,registry,drafts=setup
    row=drafts.create(Idea(title='Original world fixture',idea='Only fictional world setup.'))
    c=Creation(drafts,None);id=row['id'];edit(c,drafts,id,'focus',value='world')
    for key,value in [('title','原创世界测试'),('world','虚构浮岛世界。'),('power_system','浮岛高度由虚构矿石维持。')]:edit(c,drafts,id,'field',field_id=key,value=value)
    row=drafts.get(id);project=registry.create(drafts,ProjectCreate(draft_id=id,version=row['version'],confirm=True));ws=registry.workspace(project['id'])
    assert not list((ws.root/'characters').glob('*.yaml'))
    assert not list((ws.root/'state/characters').glob('*.yaml'))
    assert '虚构浮岛世界' in (ws.root/'bible/world.md').read_text(encoding='utf-8')
    assert yaml.safe_load((ws.root/'state/knowledge-state.yaml').read_text(encoding='utf-8'))=={'facts':{}}
    assert not (ws.root/'metadata/story-proposal.yaml').exists()
    assert (ws.root/'outlines/master-outline.md').read_bytes()==(registry.engine/'engine/templates/project/outlines/master-outline.md').read_bytes()
    assert not list((ws.root/'chapters').rglob('final.*'))
    assert c.view(id)['creation']['fields']['protagonist']['value']==''

def test_existing_world_designer_starter_uses_one_overview_without_story_methods(service,monkeypatch):
    s,p,_=world_setup(service);before=s.bible.list(p)
    with pytest.raises(ConsoleError):s.create(p,Design(goal='Only build a world',mode='starter',categories=['country']))
    d=s.create(p,Design(goal='Build a world of floating islands',mode='starter',depth='brief',categories=['overview']))
    box=capture(s,p,monkeypatch);s.start(p,d['id'],Start(etag=d['etag'],batch=0,confirm_send=True))
    assert 'World-first creation' in box['prompt'] and 'METHOD world' not in box['prompt']
    assert box['schema']['properties']['entries']['maxItems']==1
    value={'summary':'Editable world fixture','questions':[],'unknowns':[],'entries':[{'key':'island_world','name':'Original Islands','category':'overview','summary':'Fictional islands.','details':'No cast or plot.','values':[]}],'relations':[],'limitations':[]}
    box['complete'](json.dumps(value));saved=s.get(p,d['id'])
    assert saved['batches'][0]['status']=='DONE' and not saved['batches'][0]['methods']
    assert s.bible.list(p)==before


def test_world_uses_configured_world_route_in_the_actual_mock_request(center,monkeypatch):
    captured=[];transport(monkeypatch,captured);c,d,row,m=creation(center);id=row['id'];edit(c,d,id,'focus',value='world')
    center.put_controls(ControlSave(scope='feature',feature='world',value={'model':'local::model-b'}))
    async def run():
        t=c.start(id,InterviewRequest(version=d.get(id)['version'],mode='analyze',ai_controls=RequestControls(parameters={'streaming':False})),m);await t.runner;return t
    t=asyncio.run(run());assert t.status=='SUCCEEDED',t.error
    assert captured[0]['model']=='model-b'


def test_stage_and_next_model_metadata_preserve_new_content_but_content_versions_stay_strict(center):
    c,d,row,m=creation(center);id=row['id'];old=row['version']
    edit(c,d,id,'description',value='NEW_AUTHOR_WORLD_IDEA')
    changed=c.edit(id,CreationEdit(version=old,action='stage',value='profile'))
    assert changed['creation']['stage']=='profile' and changed['creation']['description']=='NEW_AUTHOR_WORLD_IDEA'
    c.edit(id,CreationEdit(version=old,action='ai_controls',ai_controls=RequestControls(model='local::model-b')))
    assert c.view(id)['creation']['description']=='NEW_AUTHOR_WORLD_IDEA'
    with pytest.raises(ConsoleError):c.edit(id,CreationEdit(version=old,action='field',field_id='world',value='UNSEEN_OVERWRITE'))
    with pytest.raises(ConsoleError):c.edit(id,CreationEdit(version=old,action='accept',field_id='world'))
    with pytest.raises(ConsoleError):c.edit(id,CreationEdit(version=old,action='focus',value='world'))
    assert c.view(id)['creation']['fields']['world']['value']==''


def test_cancelled_world_prefix_keeps_its_world_history_scope(center,monkeypatch):
    from types import SimpleNamespace
    c,d,row,m=creation(center);id=row['id'];edit(c,d,id,'focus',value='world')
    captured={}
    task=SimpleNamespace(id='fixture_cancelled_world',status='CANCELLED',result={'partial_output':'已生成的世界规则片段'},error='已取消')
    def prepared(*args,**kwargs):
        captured.update(kwargs);return task
    monkeypatch.setattr(m,'prepared',prepared)
    c.start(id,InterviewRequest(version=d.get(id)['version'],mode='analyze',ai_controls=RequestControls(model='local::model-a',parameters={'streaming':False})),m)
    captured['finished'](task)
    state=c.view(id)['creation'];message=state['messages'][-1]
    assert state['active_task'] is None and message['focus']=='world'
    assert message['content']=='已生成的世界规则片段' and message['status']=='CANCELLED'
