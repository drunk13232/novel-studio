"""Focused privacy/provenance/format checks, not a full application certification."""
import copy,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from knowledge_isolation import actor_knowledge_at
from yaml_io import loads
from app.roleplay.context import view,lore_entries
from app.creative.reviews import locate


def evidence_state():
    return {'knowledge-state.yaml':{'facts':{'F':{'canonical_truth':'PRIVATE_TRUTH_9123','introduced_chapter':0,'known_by':[{'character_id':'b','acquired_chapter':0,'story_time':'2040-01-01T08:00:00+08:00','source_event':'E0'}],'suspected_by':[{'character_id':'a','acquired_chapter':0,'story_time':'2040-01-01T08:00:00+08:00','source_event':'E0','belief':'有人隐瞒信息'}]}}},'timeline.yaml':{'events':{'E0':{'chapter':0,'story_time':'2040-01-01T07:00:00+08:00'}}},'current-story-state.yaml':{'project':{'story_date':'2040-01-01T09:00:00+08:00'}}}

def test_suspicion_is_not_truth_and_peer_isolated():
    state=evidence_state();a=actor_knowledge_at(state,'a',0,{0},True);b=actor_knowledge_at(state,'b',0,{0},True)
    assert a['suspected'][0]['text']=='有人隐瞒信息' and 'PRIVATE_TRUTH_9123' not in str(a)
    assert b['known'][0]['text']=='PRIVATE_TRUTH_9123'

@pytest.mark.parametrize('mutation',['future_chapter','late_time','no_event','uncommitted_event'])
def test_invalid_acquisition_never_grants_knowledge(mutation):
    state=evidence_state();r=state['knowledge-state.yaml']['facts']['F']['known_by'][0]
    if mutation=='future_chapter':r['acquired_chapter']=1
    if mutation=='late_time':r['story_time']='2040-01-01T10:00:00+08:00'
    if mutation=='no_event':r['source_event']='NO_SUCH_EVENT'
    if mutation=='uncommitted_event':state['timeline.yaml']['events']['E0']['chapter']=1
    assert not actor_knowledge_at(state,'b',0,{0},True)['known']


def session():
    return {'actors':[{'id':'a','name':'甲','snapshot':{'name':'甲','profile':{'goal':'谈判'},'knowledge':{'known':[],'suspected':[],'false_beliefs':[]}}},{'id':'b','name':'乙','snapshot':{'name':'乙','profile':{'goal':'PRIVATE_GOAL_B'},'knowledge':{'known':[{'text':'PRIVATE_TRUTH_B'}]}}}], 'persona':{'name':'用户','description':'公开来访者'}}


def test_actor_frame_does_not_include_other_profile_or_author_notes():
    frame=view(session(),'a',[],{'background':'公开场景','author_notes':'AUTHOR_SECRET','reader_known_fact_ids':['PRIVATE_TRUTH_B']},[],[])
    assert 'PRIVATE_GOAL_B' not in str(frame) and 'PRIVATE_TRUTH_B' not in str(frame) and 'AUTHOR_SECRET' not in str(frame)


def test_lore_filter_runs_before_matching():
    lore=[{'id':'x','name':'秘密','text':'PRIVATE_B','audiences':['b'],'keys':['港口'],'enabled':True},{'id':'y','name':'公开','text':'问路','audiences':['a'],'keys':['港口'],'enabled':True}]
    result=lore_entries(lore,'a','港口')
    assert len(result)==1 and result[0]['id']=='y'


def test_private_dialogue_and_other_branch_memory_not_received():
    messages=[{'id':'n1','speaker_name':'乙','text':'PRIVATE_SPEECH','kind':'npc','audiences':['b']},{'id':'n2','speaker_name':'用户','text':'公开','kind':'user'}]
    memory=[{'text':'OTHER_BRANCH_SECRET','audiences':['a'],'status':'CONFIRMED','source_node_ids':['other']}]
    result=view(session(),'a',messages,{},[],memory)
    assert 'PRIVATE_SPEECH' not in str(result) and 'OTHER_BRANCH_SECRET' not in str(result)


def test_long_chat_context_is_bounded_without_mutating_history():
    messages=[{'id':str(i),'speaker_name':'用户','text':'长对话'+('字'*2000),'kind':'user'} for i in range(1000)]
    result=view(session(),'a',messages,{},[],[])
    assert len(result['visible_conversation'])<32 and len(messages)==1000 and result['stored_turn_count']==1000


def test_safe_yaml_domain_sequences_and_scalar_compatibility():
    assert loads('goals:\n  short_term:\n  - 核对线索\n  long_term: []\n')['goals']['short_term']==['核对线索']
    assert loads('date: 2041-01-02\nflag: OFF\nitems:\n- a\n')['date']=='2041-01-02'
    assert loads('date: 2041-01-02\nflag: OFF\nitems:\n- a\n')['flag']=='OFF'

@pytest.mark.parametrize('text',['a: 1\na: 2\n', 'a: &x [1]\nb: *x\n', 'a: !!python/object/apply:os.system ["unsafe"]\n'])
def test_yaml_duplicate_alias_and_code_never_execute(text):
    with pytest.raises(ValueError):loads(text)


def test_unicode_quote_locations_and_ambiguity():
    value=locate('这段有依据。','😀这段有依据。\n这段有依据。')
    assert value['verified'] and value['ambiguous'] and value['locations'][0]['start']==2
    assert not locate('不存在的引用','真实原文')['verified']
