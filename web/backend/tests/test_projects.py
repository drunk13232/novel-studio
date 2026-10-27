import copy
import json
import shutil
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from app.errors import ConsoleError
from app.projects.models import Idea,ProjectCreate,FoundationTask,Proposal
from app.projects.service import DraftStore,ProjectRegistry,validate_locks,sha
from app.projects.foundation import Foundation

ENGINE=Path(__file__).resolve().parents[3]

@pytest.fixture
def setup(tmp_path):
    shutil.copytree(ENGINE/'engine',tmp_path/'engine')
    shutil.copytree(ENGINE/'templates',tmp_path/'templates')
    app=create_app(Settings(workspace=tmp_path));app.state.testing=True
    c=TestClient(app);c.headers['X-Novel-Request']=c.get('/api/session').json()['request_token']
    return c,app.state.registry,app.state.drafts

def create(c,title='Fixture Novel'):
    d=c.post('/api/drafts',json={'input':{'title':title,'premise':'A discovers B.'}}).json()
    r=c.post('/api/projects',json={'draft_id':d['id'],'version':d['version'],'confirm':True})
    assert r.status_code==201,r.text
    return r.json()

def test_draft_no_formal_pollution_and_confirm(setup):
    c,r,d=setup
    row=c.post('/api/drafts',json={'input':{'title':'中文/../标题？？','total_words':'100-150 万'}}).json()
    assert list(r.root.iterdir())==[]
    assert c.post('/api/projects',json={'draft_id':row['id'],'version':row['version'],'confirm':False}).status_code==422
    p=c.post('/api/projects',json={'draft_id':row['id'],'version':row['version'],'confirm':True}).json()
    assert p['id'].startswith('novel_') and len(p['id'])==38
    assert p['title']=='中文/../标题？？'
    assert p['status']['phase']=='FOUNDATION'
    assert p['target']['total_words']=='100-150 万'
    assert p['workflow']['auto_state_commit'] is False
    ws=r.workspace(p['id'])
    for f in ['project.yaml','bible/world.md','outlines/master-outline.md','settings/canon-contract.yaml','settings/style-profile.yaml','state/knowledge-state.yaml','state/chapter-ledger.yaml']:
        assert (ws.root/f).is_file()
    assert ws.yaml_file('state/knowledge-state.yaml')=={'facts':{}}
    assert not list((ws.root/'chapters').glob('*.md'))

def test_registry_archive_rebuild_and_no_delete(setup):
    c,r,d=setup;p=create(c)
    assert c.get('/api/projects').json()['projects'][0]['project_id']==p['id']
    m=c.get('/api/projects/'+p['id']).json()
    assert c.post('/api/projects/'+p['id']+'/archive',json={'etag':m['etag']}).status_code==200
    assert c.get('/api/projects').json()['projects']==[]
    assert len(c.get('/api/projects?include_archived=true').json()['projects'])==1
    assert (r.root/p['id']).exists()
    assert ProjectRegistry(r.engine).get(p['id'])['status']['phase']=='ARCHIVED'
    assert c.delete('/api/projects/'+p['id']).status_code==405
    assert c.put('/api/projects/'+p['id']+'/files/content',json={'path':'bible/world.md','content':'bad','etag':'a'*64}).status_code==409

@pytest.mark.parametrize('path',['../other/bible/world.md','projects/novel_123/bible/world.md','bible/../../settings/a.yaml','C:/auth.json','bible\\world.md'])
def test_cross_project_paths(setup,path):
    c,r,d=setup;p=create(c)
    assert c.get('/api/projects/'+p['id']+'/files/content',params={'path':path}).status_code==403

def test_independent_stats_and_version_conflicts(setup):
    c,r,d=setup;a=create(c);b=create(c)
    ws=r.workspace(a['id']);(ws.root/'chapters/001.md').write_text('# 测试\n你好 world',encoding='utf8')
    assert r.status(a['id'])['stats']['chinese_words']==5
    assert r.status(b['id'])['stats']['chinese_words']==0
    path='/api/projects/'+a['id']+'/files/content'
    original=c.get(path,params={'path':'bible/world.md'}).json()
    (ws.root/'bible/world.md').write_text('external',encoding='utf8')
    assert c.put(path,json={'path':'bible/world.md','etag':original['etag'],'content':'local'}).status_code==409

def fixture_proposal():
    char={'name':'A','identity':'主角 A 为女性。','personality':'普通','core_desire':'找到 B','fear':'失去线索','story_function':'推动发现','arc':'敢于求证'}
    return {'premise':'A discovers B.','core_conflict':'寻找与隐瞒','story_engine':'线索引出选择','themes':[],'reader_promises':[],
            'protagonist_concept':char,'major_character_roles':[],'world_concept':'背景为现代中国。','power_or_rule_system':'现实规则','major_factions':[],
            'macro_structure':dict.fromkeys(['opening','development','midpoint','escalation','climax','ending_direction'],'TBD'),
            'volume_concepts':[],'risks':[],'open_questions':[],'user_locked':{'protagonist':'主角 A 为女性。','era':'背景为现代中国。'},'lock_verdict':'PASS','lock_reason':'保留原文'}

def test_user_locks_and_canon_style_schema(setup):
    c,r,d=setup
    idea=Idea(title='Fixture Novel',locked_constraints={'protagonist':'主角 A 为女性。','era':'背景为现代中国。'},style='不要网络梗。',pacing='慢热')
    row=d.create(idea);p=fixture_proposal()
    bad=copy.deepcopy(p);bad['protagonist_concept']['identity']='主角是男性'
    with pytest.raises(ConsoleError):validate_locks(bad,idea.model_dump())
    bad=copy.deepcopy(p);bad['user_locked']['protagonist']='男性'
    with pytest.raises(ConsoleError):validate_locks(bad,idea.model_dump())
    row=d.update(row['id'],1,proposal=p)
    assert c.post('/api/projects',json={'draft_id':row['id'],'version':row['version'],'confirm':True}).status_code==409
    project=r.create(d,ProjectCreate(draft_id=row['id'],version=row['version'],confirm=True,accept_proposal=True))
    ws=r.workspace(project['id']);canon=ws.yaml_file('settings/canon-contract.yaml')
    assert len(canon['hard'])==2 and len(canon['strong'])==3
    assert ws.yaml_file('settings/style-profile.yaml')['description_preferences']==['不要网络梗。']
    import sys
    sys.path.insert(0,str(ENGINE/'scripts'));import model
    for f,key in model.FILE_SCHEMAS.items():model.validate(ws.yaml_file('state/'+f),model.SCHEMAS['$defs'][key])
    model.validate(canon,model.SCHEMAS['$defs']['contract'])
    model.validate(ws.yaml_file('settings/style-profile.yaml'),model.SCHEMAS['$defs']['style'])
    model.validate(ws.yaml_file('state/characters/character_001.yaml'),model.SCHEMAS['$defs']['character'])

def test_partial_merge_preserves_frozen_sections_and_stale_result(setup):
    c,r,d=setup
    row=d.create(Idea(title='Fixture Novel',locked_constraints={'protagonist':'主角 A 为女性。','era':'背景为现代中国。'}));row=d.update(row['id'],1,proposal=fixture_proposal())
    foundation=Foundation(ENGINE,r,d)
    # Capture the real final-result handler; no substitute model is used for E2E.
    class Capture:
        def prepared(self,request,prompt,readonly,scope,schema,complete):self.complete=complete;self.prompt=prompt;return self
    manager=Capture();foundation.start_draft(row['id'],FoundationTask(type='story_architect_refine',version=row['version'],section='protagonist_concept',instruction='更普通'),manager)
    replacement=copy.deepcopy(row['proposal']['protagonist_concept']);replacement['personality']='更普通'
    result=manager.complete(json.dumps({'replacement':replacement,'lock_verdict':'PASS','lock_reason':'保留锁定'}))
    assert {k:v for k,v in result['proposal'].items() if k!='protagonist_concept'}=={k:v for k,v in row['proposal'].items() if k!='protagonist_concept'}
    with pytest.raises(ConsoleError):manager.complete(json.dumps({'replacement':replacement,'lock_verdict':'PASS','lock_reason':'保留锁定'}))

def test_thread_files_and_task_ids_are_scoped(setup):
    c,r,d=setup;a=create(c);b=create(c)
    from app.tasks.manager import TaskManager
    from app.tasks.router import TaskRouter
    ma=TaskManager(r.workspace(a['id']),TaskRouter(r.workspace(a['id']),ENGINE),r.engine)
    mb=TaskManager(r.workspace(b['id']),TaskRouter(r.workspace(b['id']),ENGINE),r.engine)
    assert ma._thread_file!=mb._thread_file
    assert c.get('/api/projects/'+b['id']+'/tasks/unknown').status_code==404
    from app.models.requests import TaskRequest
    prompt,_,_=ma.router.build(TaskRequest(type='custom_prompt',prompt='状态',options={'read_only':True}))
    assert str(r.workspace(a['id']).root) in prompt and str(r.workspace(b['id']).root) not in prompt


def test_candidate_review_commit_conflicts_and_archived_readonly(setup):
    c,r,d=setup;a=create(c);b=create(c)
    ws=r.workspace(a['id']);f=Foundation(ENGINE,r,d)
    class Capture:
        def prepared(self,request,prompt,readonly,scope,schema,complete):self.complete=complete;return self
    manager=Capture();original=ws.content('bible/world.md')
    f.start_project(a['id'],FoundationTask(type='world_expand',instruction='仅 fixture'),manager)
    value=manager.complete(json.dumps({'content':'# Fixture world\nTBD','explanation':'fixture','lock_verdict':'PASS','lock_reason':''}))
    assert ws.content('bible/world.md')['etag']==original['etag']
    path='/api/projects/'+a['id']+'/proposals/'+value['id']
    assert c.get('/api/projects/'+b['id']+'/proposals/'+value['id']).status_code==404
    edited=c.patch(path,json={'version':1,'content':'# Fixture world\nUNKNOWN'}).json()
    assert edited['version']==2 and 'UNKNOWN' in edited['diff']
    assert c.post(path+'/accept',json={'version':1,'confirm':True}).status_code==409
    assert c.post(path+'/accept',json={'version':2,'confirm':True}).status_code==200
    assert 'UNKNOWN' in ws.content('bible/world.md')['content']
    assert c.post(path+'/accept',json={'version':2,'confirm':True}).status_code==409
    f.start_project(a['id'],FoundationTask(type='world_expand'),manager)
    value=manager.complete(json.dumps({'content':'new','explanation':'fixture','lock_verdict':'PASS','lock_reason':''}))
    path='/api/projects/'+a['id']+'/proposals/'+value['id']
    ws.save('bible/world.md','external',ws.content('bible/world.md')['etag'])
    assert c.post(path+'/accept',json={'version':1,'confirm':True}).status_code==409
    m=c.get('/api/projects/'+a['id']).json()
    c.post('/api/projects/'+a['id']+'/archive',json={'etag':m['etag']})
    assert c.patch(path,json={'version':1,'content':'bad'}).status_code==409
    assert c.post(path+'/discard',json={'version':1,'confirm':True}).status_code==409


def test_character_candidate_without_locks_and_invalid_schema(setup):
    c,r,d=setup;p=create(c);ws=r.workspace(p['id']);f=Foundation(ENGINE,r,d)
    card=yaml.safe_load((ENGINE/'engine/templates/character.yaml').read_text(encoding='utf8'))
    card.update(id='character_a',name='A',role='PROTAGONIST')
    f.check_change(ws,'characters/character_a.yaml',yaml.safe_dump(card),ws.yaml_file('metadata/user-input.yaml'))
    bad=copy.deepcopy(card);bad['arc']='wrong'
    with pytest.raises(ConsoleError):f.check_change(ws,'characters/character_a.yaml',yaml.safe_dump(bad),ws.yaml_file('metadata/user-input.yaml'))
    with pytest.raises(ConsoleError):f.start_project(p['id'],FoundationTask(type='character_refine',target='characters/missing.yaml'),None)
    assert set(['story_architect','story_architect_refine','world_expand','character_create','character_refine','master_outline_generate','volume_outline_generate']).issubset(c.get('/api/task-types').json())


def test_candidate_commit_keeps_original_crlf_and_bom(setup):
    c,r,d=setup;p=create(c);ws=r.workspace(p['id']);f=Foundation(ENGINE,r,d)
    (ws.root/'bible/world.md').write_bytes(b'\xef\xbb\xbf# Fixture\r\n')
    class Capture:
        def prepared(self,request,prompt,readonly,scope,schema,complete):self.complete=complete;return self
    m=Capture();f.start_project(p['id'],FoundationTask(type='world_expand'),m)
    value=m.complete(json.dumps({'content':'# Fixture\nTBD\r\n','explanation':'fixture','lock_verdict':'PASS','lock_reason':''}))
    from app.projects.models import ReviewAccept
    f.accept(p['id'],value['id'],ReviewAccept(version=1,confirm=True))
    assert (ws.root/'bible/world.md').read_bytes()==b'\xef\xbb\xbf# Fixture\r\nTBD\r\n'
