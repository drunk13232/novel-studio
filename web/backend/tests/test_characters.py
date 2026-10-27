import copy,json
import pytest,yaml
from tests.test_projects import setup,create,ENGINE
from app.domain.characters import CharacterCanon,CharacterService
from app.domain.proposals import Proposals
from app.domain.tasks import CharacterTasks,DomainTask
from app.projects.foundation import Foundation
from app.errors import ConsoleError

def test_character_schema_runtime_and_asymmetry(setup):
    c,r,d=setup;p=create(c)['id'];base='/api/projects/'+p
    a=c.post(base+'/characters',json=CharacterCanon(id='x',name='A',appearance={'height':'148cm'}).model_dump()).json()
    b=c.post(base+'/characters',json=CharacterCanon(id='x',name='B').model_dump()).json()
    aid=a['canonical']['id'];bid=b['canonical']['id'];ws=r.workspace(p)
    before=ws.content('state/characters/'+aid+'.yaml')['etag']
    a['canonical']['relationships']['initial'][bid]={'type':['love'],'public_state':{},'private_state':{'description':'爱慕 B'},'history':[]}
    assert c.put(base+'/characters/'+aid,json={'canonical':a['canonical'],'etag':a['etag']}).status_code==200
    assert c.get(base+'/characters/'+bid).json()['canonical']['relationships']['initial']=={}
    assert ws.content('state/characters/'+aid+'.yaml')['etag']==before
    raw=c.get(base+'/files/content',params={'path':'characters/'+aid+'.yaml'}).json()
    assert c.put(base+'/files/content',json={'path':raw['path'],'etag':raw['etag'],'content':'schema_version: "0.4"\nid: wrong\nidentity: bad'}).status_code==422
    assert ws.content(raw['path'])['etag']==raw['etag']

def test_partial_freeze_lock_and_review_commit(setup):
    c,r,d=setup;p=create(c)['id'];cs=CharacterService(r);ps=Proposals(r)
    card=CharacterCanon(id='x',name='A',appearance={'height':'148cm'},canon={'hard':[{'path':'appearance.height','value':'148cm','statement':'身高 148cm'}]}).model_dump()
    row=cs.create(p,card);card=row['canonical'];ws=r.workspace(p)
    ct=CharacterTasks(r,cs,ps,Foundation(ENGINE,r,d))
    class Capture:
        def prepared(self,request,prompt,readonly,scope,schema,complete,**kwargs):self.complete=complete;self.prompt=prompt;return self
    m=Capture();ct.start(p,DomainTask(type='character_refine',character_id=card['id'],section='personality'),m)
    candidate=copy.deepcopy(card);candidate['personality']['core_traits']=['外向'];candidate['speech']['tone']='越权变化';candidate['appearance']['height']='999cm'
    result=m.complete(json.dumps({'content':yaml.safe_dump(candidate,allow_unicode=True),'explanation':'候选','lock_verdict':'PASS','lock_reason':'保持'}))
    assert cs.get(p,card['id'])['canonical']==card
    runtime=ws.content('state/characters/'+card['id']+'.yaml')['etag']
    ps.commit(p,result['id'],1,lambda ops:ct.validate(p,ops))
    final=cs.get(p,card['id'])['canonical'];assert final['personality']['core_traits']==['外向']
    assert final['speech']==card['speech'] and final['appearance']==card['appearance']
    assert ws.content('state/characters/'+card['id']+'.yaml')['etag']==runtime
    ct.start(p,DomainTask(type='character_refine',character_id=card['id']),m)
    with pytest.raises(ConsoleError):m.complete(json.dumps({'content':yaml.safe_dump(candidate),'explanation':'破坏锁定','lock_verdict':'PASS','lock_reason':'保持'}))
    ct.start(p,DomainTask(type='character_create',character_id=card['id']),m)
    assert '保持 id='+card['id'] not in m.prompt

def test_knowledge_projection_and_project_isolation(setup):
    c,r,d=setup;p=create(c)['id'];q=create(c)['id'];cs=CharacterService(r)
    a=cs.create(p,CharacterCanon(id='x',name='A',secrets={'author_only':['PRIVATE_SENTINEL']}).model_dump())['canonical'];id=a['id'];ws=r.workspace(p)
    from app.projects.service import write_yaml
    facts={'K1':{'canonical_truth':'X 已死亡','known_by':[{'character_id':id}]},'K2':{'canonical_truth':'B 隐瞒身份','suspected_by':[{'character_id':id}]},'K3':{'canonical_truth':'真实出生地','false_beliefs':{id:{'belief':'来自帝都'}}},'K4':{'canonical_truth':'不可泄露真相'}}
    write_yaml(ws.resolve('state/knowledge-state.yaml'),{'facts':facts})
    runtime=ws.yaml_file('state/characters/'+id+'.yaml');runtime['knowledge']['does_not_know']=['K4'];write_yaml(ws.resolve('state/characters/'+id+'.yaml'),runtime)
    knowledge=cs.get(p,id)['knowledge'];assert [len(v) for v in knowledge.values()]==[1,1,1,1]
    assert '不可泄露真相' not in json.dumps(knowledge)
    assert c.get('/api/projects/'+q+'/characters/'+id).status_code==404
    assert c.post('/api/projects/'+q+'/characters',json={**CharacterCanon(id='x').model_dump(),'relationships':{'initial':{id:{}}}}).status_code==404

def test_author_only_static_card_not_in_real_context():
    import importlib.util
    spec=importlib.util.spec_from_file_location('core_context_fixture',ENGINE/'tests/test_workflow.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fixture=module.WorkflowTests();fixture.setUp()
    try:
        static=fixture.root/'characters/A.yaml';static.parent.mkdir(exist_ok=True)
        static.write_text(yaml.safe_dump(CharacterCanon(id='A',secrets={'author_only':['PRIVATE_CANON_SECRET']}).model_dump()),encoding='utf8')
        packet=module.w.context(fixture.root,fixture.plan)
        assert 'PRIVATE_CANON_SECRET' not in json.dumps(packet)
        assert module.FIXTURE['secret'] not in json.dumps(packet,ensure_ascii=False)
    finally:fixture.doCleanups()

def test_character_bootstrap_rollback_in_same_journal(setup,monkeypatch):
    c,r,d=setup;p=create(c)['id'];cs=CharacterService(r);ps=Proposals(r);ws=r.workspace(p)
    card=CharacterCanon(id='character_fixture',name='B').model_dump();path=cs.path(card['id'])
    proposal=ps.stage(p,'character_create',[{'path':path,'content':yaml.safe_dump(card),'action':'write'}],'bootstrap test',[],{path:None},lambda ops:None)
    original=ps.write;calls=[]
    def crash_after_runtime(path,data):
        original(path,data);calls.append(str(path))
        if len(calls)==2:raise OSError('SIMULATED crash after bootstrap')
    monkeypatch.setattr(ps,'write',crash_after_runtime)
    with pytest.raises(OSError):ps.commit(p,proposal['id'],1,lambda ops:None,initialize=lambda value:cs.runtime_initializations(ws,card))
    assert not (ws.root/path).exists() and not (ws.root/'state/characters/character_fixture.yaml').exists()
    assert ws.yaml_file('metadata/transactions/'+proposal['id']+'.yaml')['status']=='ROLLED_BACK'
