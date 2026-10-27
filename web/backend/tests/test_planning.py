import copy,json
import pytest
from pydantic import ValidationError
from tests.test_projects import setup,create,ENGINE
from app.domain.characters import CharacterCanon,CharacterService
from app.domain.proposals import Proposals
from app.domain.planning import Planning,Volume,ChapterCard,PlanAction,dump
from app.domain.planning_tasks import PlanningTasks
from app.domain.tasks import DomainTask
from app.projects.foundation import Foundation
from app.projects.service import write_yaml
from app.errors import ConsoleError

def fixture(setup):
    c,r,d=setup;p=create(c)['id'];cs=CharacterService(r);ps=Proposals(r);planning=Planning(r,cs,ps)
    a=cs.create(p,CharacterCanon(id='x',name='A').model_dump())['canonical']['id'];b=cs.create(p,CharacterCanon(id='x',name='B').model_dump())['canonical']['id']
    volumes=[Volume(id='volume_'+str(i)*32,number=i,title='卷'+str(i),status='PLANNED').model_dump() for i in [1,2]]
    for v in volumes:write_yaml(r.workspace(p).resolve(planning.path(v['id'],'volume')),v)
    cards=[ChapterCard(id='chapter_'+str(i)*32,number=i,order=i,volume=volumes[0]['id'],status='PLANNED',pov={'character':a},characters=[a,b],state_changes_expected=['B 会死亡'] if i==3 else [],knowledge_changes_expected=['A learns K9'] if i==3 else []).model_dump() for i in [1,2,3]]
    cards[2]['depends_on']=[cards[0]['id']]
    for card in cards:write_yaml(r.workspace(p).resolve(planning.path(card['id'],'chapter')),card)
    return c,r,d,p,planning,ps,a,b,volumes,cards

def test_stable_reorder_outline_not_state_and_cross_project(setup):
    c,r,d,p,planning,ps,a,b,volumes,cards=fixture(setup);ws=r.workspace(p)
    before={f['path']:ws.content(f['path'])['etag'] for f in ws.list_files() if f['path'].startswith('state/')}
    board=planning.board(p,volumes[0]['id'])
    planning.manual(p,PlanAction(action='reorder',volume_id=volumes[0]['id'],chapter_ids=[cards[2]['id'],cards[0]['id'],cards[1]['id']],etags=board['etags'],confirm=True))
    assert planning.get(p,cards[2]['id'],'chapter')['value']['number']==1
    assert planning.get(p,cards[2]['id'],'chapter')['value']['depends_on']==[cards[0]['id']]
    assert before=={f['path']:ws.content(f['path'])['etag'] for f in ws.list_files() if f['path'].startswith('state/')}
    assert ws.yaml_file('state/characters/'+b+'.yaml')['status']['alive'] is True
    assert ws.yaml_file('state/knowledge-state.yaml')['facts']=={}
    q=create(c)['id'];assert c.get('/api/projects/'+q+'/planning/chapter/'+cards[0]['id']).status_code==404
    assert len(list((ws.root/'outlines/chapters').glob('*.yaml')))==3

def test_manual_dependants_split_merge_move_and_written_warning(setup):
    c,r,d,p,planning,ps,a,b,volumes,cards=fixture(setup);volume=volumes[0]['id']
    def act(**kwargs):return planning.manual(p,PlanAction(volume_id=volume,etags=planning.board(p,volume)['etags'],confirm=True,**kwargs))
    with pytest.raises(ConsoleError):act(action='delete',chapter_id=cards[0]['id'])
    act(action='split',chapter_id=cards[1]['id']);rows=planning.rows(p,'chapter');child=next(x for x in rows if x['id'] not in {c['id'] for c in cards})
    assert child['depends_on']==[cards[1]['id']]
    act(action='merge',chapter_id=cards[1]['id'],chapter_ids=[child['id']]);assert len(planning.rows(p,'chapter'))==3
    act(action='move',chapter_id=cards[1]['id'],target_volume=volumes[1]['id']);assert planning.get(p,cards[1]['id'],'chapter')['value']['volume']==volumes[1]['id']
    written=planning.get(p,cards[2]['id'],'chapter')['value'];written['status']='DRAFTED';write_yaml(r.workspace(p).resolve(planning.path(written['id'],'chapter')),written)
    with pytest.raises(ConsoleError):act(action='delete',chapter_id=written['id'])
    act(action='delete',chapter_id=written['id'],confirm_written=True);assert len(planning.rows(p,'chapter'))==2

def test_schema_timeline_and_raw_validation(setup):
    c,r,d,p,planning,ps,a,b,volumes,cards=fixture(setup);ws=r.workspace(p)
    with pytest.raises(ValidationError):Volume(id='volume-001',number=1)
    for i,time in enumerate(['2030-01-03','2030-01-02','2030-01-01']):
        cards[i]['story_time']=time
        if i==2:cards[i]['temporal_mode']='FLASHBACK'
        write_yaml(ws.resolve(planning.path(cards[i]['id'],'chapter')),cards[i])
    warnings=planning.board(p,volumes[0]['id'])['warnings'];assert [w['chapter_id'] for w in warnings]==[cards[1]['id']]
    bad=copy.deepcopy(cards[0]);bad['status']='DRAFTING'
    with pytest.raises(ConsoleError):planning.validate(p,[{'path':planning.path(bad['id'],'chapter'),'content':dump(bad)}])
    raw=c.get('/api/projects/'+p+'/files/content',params={'path':planning.path(cards[0]['id'],'chapter')}).json()
    assert c.put('/api/projects/'+p+'/files/content',json={'path':raw['path'],'etag':raw['etag'],'content':dump(bad)}).status_code==409
    assert ws.content(raw['path'])['etag']==raw['etag']

def test_real_skill_prompt_and_ai_candidate_scope(setup):
    c,r,d,p,planning,ps,a,b,volumes,cards=fixture(setup)
    tasks=PlanningTasks(r,planning,planning.characters,ps,Foundation(ENGINE,r,d))
    class Capture:
        def prepared(self,request,prompt,readonly,scope,schema,complete,**kwargs):self.complete=complete;self.prompt=prompt;return self
    capture=Capture();tasks.start(p,DomainTask(type='chapter_cards_deepen',target=volumes[0]['id'],chapter_ids=[c['id'] for c in cards]),capture)
    assert 'sw-scene-craft' in capture.prompt and '进出与节奏' in capture.prompt
    candidate=copy.deepcopy(cards)
    for card in candidate:card['planning_level']='DETAILED';card['scenes']=[{'id':'scene_1','order':1,'characters':[a,b],'conflict':'目标相冲突','turn':'选择变化'}]
    result=capture.complete(json.dumps({'content':dump(candidate),'explanation':'候选','lock_verdict':'PASS','lock_reason':'保持'}))
    assert planning.get(p,cards[0]['id'],'chapter')['value']['planning_level']=='SKELETON'
    ps.commit(p,result['id'],1,lambda ops:planning.validate(p,ops))
    assert planning.get(p,cards[0]['id'],'chapter')['value']['planning_level']=='DETAILED'
    with pytest.raises(ConsoleError):planning.validate(p,[{'path':'state/characters/'+b+'.yaml','content':'status: {alive: false}'}])
