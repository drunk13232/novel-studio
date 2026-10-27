"""Data-only roleplay contracts. Imports never grant tools or system prompts."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.ai.models import Parameters

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Persona(Strict):
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=3000)
    character_id:str|None=Field(default=None,max_length=64)
class Actor(Strict):
    source_type:Literal['character','card']='character'
    source_id:str=Field(min_length=1,max_length=100)
    model:str|None=Field(default=None,max_length=250)
class SceneFact(Strict):
    id:str=Field(default='',max_length=80)
    text:str=Field(min_length=1,max_length=1800)
    audiences:list[str]=Field(default_factory=list,max_length=8)
    shareable:bool=False
    basis:Literal['AUTHOR_SCENARIO','SOURCE_QUOTE']='AUTHOR_SCENARIO'
class Scene(Strict):
    time:str=Field(default='',max_length=200)
    location:str=Field(default='',max_length=200)
    background:str=Field(default='',max_length=5000)
    chapter:int|None=Field(default=None,ge=0,le=99999)
    author_notes:str=Field(default='',max_length=5000)
    reader_known_fact_ids:list[str]=Field(default_factory=list,max_length=40)
    dialogue_language:str=Field(default='',max_length=40)
    temporary_facts:list[SceneFact]=Field(default_factory=list,max_length=40)
    disclosure_fact_ids:list[str]=Field(default_factory=list,max_length=40)
class Lore(Strict):
    id:str=Field(default='',max_length=80)
    name:str=Field(min_length=1,max_length=150)
    text:str=Field(min_length=1,max_length=3000)
    keys:list[str]=Field(default_factory=list,max_length=20)
    secondary_keys:list[str]=Field(default_factory=list,max_length=20)
    match:Literal['ANY','ALL']='ANY'
    constant:bool=False
    enabled:bool=True
    priority:int=Field(default=0,ge=-100,le=100)
    audiences:list[str]=Field(default_factory=list,max_length=8)
    source_type:Literal['AUTHOR_SCENARIO','IMPORTED_DATA','CONFIRMED_SOURCE']='AUTHOR_SCENARIO'
    source_id:str=Field(default='',max_length=100)
    shareable:bool=False
class Card(Strict):
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=6000)
    personality:str=Field(default='',max_length=4000)
    scenario:str=Field(default='',max_length=4000)
    first_message:str=Field(default='',max_length=4000)
    example_dialogue:str=Field(default='',max_length=4000)
    lore:list[Lore]=Field(default_factory=list,max_length=60)
class Create(Strict):
    title:str=Field(min_length=1,max_length=200)
    persona:Persona
    actors:list[Actor]=Field(min_length=1,max_length=8)
    scene:Scene=Field(default_factory=Scene)
    lore:list[Lore]=Field(default_factory=list,max_length=60)
    model:str|None=Field(default=None,max_length=250)
class Reply(Strict):
    etag:str=Field(min_length=64,max_length=64)
    branch_id:str=Field(max_length=80)
    text:str=Field(default='',max_length=6000)
    actor_ids:list[str]=Field(min_length=1,max_length=4)
    model:str|None=Field(default=None,max_length=250)
    parameters:Parameters|None=None
class Utterance(Strict):
    actor_id:str
    text:str=Field(min_length=1,max_length=5000)
    action_basis:list[str]=Field(default_factory=list,max_length=8)
    uncertainties:list[str]=Field(default_factory=list,max_length=8)
    emotion:Literal['neutral','happy','confused','surprised','displeased','shy','thinking']='neutral'
    motion_intent:Literal['none','greet','tap','agree','think']='none'
    operation:Literal['none','open_chapter','search_characters']='none'
    chapter_number:int|None=Field(default=None,ge=1,le=99999)
    query:str=Field(default='',max_length=200)
class Fork(Strict):
    etag:str=Field(min_length=64,max_length=64)
    branch_id:str=Field(max_length=80)
    node_id:str|None=Field(default=None,max_length=80)
    name:str=Field(min_length=1,max_length=150)
    edited_text:str|None=Field(default=None,max_length=6000)
    scene:Scene|None=None
class SessionEdit(Strict):
    etag:str=Field(min_length=64,max_length=64)
    branch_id:str=Field(max_length=80)
    scene:Scene|None=None
    lore:list[Lore]|None=Field(default=None,max_length=60)
    model:str|None=Field(default=None,max_length=250)
    actor_models:dict[str,str|None]=Field(default_factory=dict,max_length=8)
class Memory(Strict):
    etag:str=Field(min_length=64,max_length=64)
    branch_id:str=Field(max_length=80)
    text:str=Field(min_length=1,max_length=2500)
    audiences:list[str]=Field(min_length=1,max_length=8)
    source_node_ids:list[str]=Field(default_factory=list,max_length=12)
    shareable:bool=False
    interpretation:Literal['KNOWN_IN_SCENE','SUSPECTED','FALSE_BELIEF']='KNOWN_IN_SCENE'
    confirm:Literal[True]
class Adopt(Strict):
    etag:str=Field(min_length=64,max_length=64)
    branch_id:str=Field(max_length=80)
    node_ids:list[str]=Field(min_length=1,max_length=20)
    kind:Literal['inspiration','scene','chapter_material']='scene'
    title:str=Field(default='',max_length=200)
    confirm:Literal[True]
class Analyze(Strict):
    branch_id:str=Field(max_length=80)
    actor_id:str=Field(max_length=80)
    question:str=Field(min_length=1,max_length=4000)
    model:str|None=Field(default=None,max_length=250)
class Possibility(Strict):
    action:str=Field(min_length=1,max_length=1800)
    basis:list[str]=Field(min_length=1,max_length=8)
    premises:list[str]=Field(default_factory=list,max_length=8)
    consequences:list[str]=Field(default_factory=list,max_length=8)
    uncertainty:list[str]=Field(min_length=1,max_length=8)
class BehaviorReport(Strict):
    summary:str=Field(max_length=3000)
    possibilities:list[Possibility]=Field(min_length=1,max_length=5)
    missing_information:list[str]=Field(default_factory=list,max_length=12)
    experiment_question:str=Field(default='',max_length=3000)
class ImportCard(Strict):text:str=Field(min_length=1,max_length=160000)

class CompareScenes(Strict):
    branches:list[str]=Field(min_length=2,max_length=3)

class MemoryDesign(Strict):
    branch_id:str=Field(max_length=80)
    actor_id:str=Field(max_length=80)
    model:str|None=Field(default=None,max_length=250)
class MemoryProposal(Strict):
    text:str=Field(min_length=1,max_length=2500)
    source_node_ids:list[str]=Field(min_length=1,max_length=12)
    interpretation:Literal['KNOWN_IN_SCENE','SUSPECTED','FALSE_BELIEF']='KNOWN_IN_SCENE'
    uncertainties:list[str]=Field(default_factory=list,max_length=8)
