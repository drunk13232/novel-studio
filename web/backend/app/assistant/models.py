from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.ai.controls import RequestControls
from app.appearance import ThemeId
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class AssistantSettings(Strict):
    model:str='codex-software'
    mode:Literal['suggest','navigate','draft']='navigate'
    page:bool=True
    selection:bool=False
    setting_context:bool=False
    manuscript:bool=False
    references:bool=False
    style:bool=False
    history:bool=True
    save_conversation:bool=True
    voice_reply:bool=False
    communication_style:str=Field(default='',max_length=2000)
    reply_length:Literal['short','medium','long']='medium'
    max_steps:int=Field(default=12,ge=1,le=64)
class Context(Strict):
    project:str|None=None
    page:str=Field(default='home',max_length=40)
    path:str=Field(default='',max_length=300)
    character:str=Field(default='',max_length=64)
    entity:str=Field(default='',max_length=64)
    theme:ThemeId='moon'
    selection:str=Field(default='',max_length=16000)
    start:int=Field(default=0,ge=0)
    end:int=Field(default=0,ge=0)
    document_revision:str=Field(default='',max_length=64)
    original_hash:str=Field(default='',max_length=64)
    chapter_id:str=Field(default='',max_length=64)
Persona=Literal['assistant','yoshino','rem','haru']
class Start(Strict):
    voice_reply:bool=False
    persona:Persona='assistant'
    previous_session:str|None=Field(default=None,pattern=r"^[0-9a-f]{32}$")
    request_id:str|None=Field(default=None,pattern=r"^[0-9a-f]{32}$")
    client_elapsed_ms:float=Field(default=0,ge=0,le=60000)
    instruction:str=Field(min_length=1,max_length=4000)
    context:Context
    model:str|None=Field(default=None,max_length=250)
    ai_controls:RequestControls|None=None
class LocalAction(Start):
    tool:str=Field(min_length=1,max_length=80)
    arguments:dict=Field(default_factory=dict)
class Reply(Strict):
    context:Context|None=None
    token:str
    approved:bool=False
    result:dict=Field(default_factory=dict)
class Empty(Strict):pass
class Query(Strict):query:str=Field(default='',max_length=200)
class Target(Strict):id:str=Field(min_length=1,max_length=120)
class Chapter(Strict):number:int=Field(ge=0,le=99999)
class Page(Strict):
    page:str=Field(pattern='^(write|characters|world|references|styles|knowledge|timeline|data|book|search|notes|outline|gallery|images|history|worldlogic|roleplay|literary|python)$')
    report_id:str|None=Field(default=None,pattern=r'^review_[0-9a-f]{32}$')
class Document(Strict):id:str=Field(min_length=1,max_length=120)
class CharacterDraft(Strict):
    name:str=Field(min_length=1,max_length=100)
    summary:str=Field(default='',max_length=1000)
    occupation:str=Field(default='',max_length=200)
    age:int|None=Field(default=None,ge=0,le=300)
class CharacterEdit(Strict):
    id:str=Field(default='',max_length=64)
    name:str|None=Field(default=None,max_length=100)
    age:int|None=Field(default=None,ge=0,le=300)
    occupation:str|None=Field(default=None,max_length=200)
    summary:str|None=Field(default=None,max_length=1000)
class ChapterDraft(Strict):
    number:int=Field(ge=1,le=99999)
    title:str=Field(default='',max_length=200)
    volume_id:str|None=None
class ChapterDraftCandidate(Strict):
    parent_id:str|None=Field(default=None,pattern=r'^[0-9a-f]{32}$')
    insert_before:str=Field(default='',max_length=1000)
    number:int=Field(ge=1,le=99999)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    content:str=Field(min_length=1,max_length=32000)
    note:str=Field(default='',max_length=1000)

class ChapterCandidateRead(Strict):
    id:str=Field(pattern=r'^[0-9a-f]{32}$')
    start:int=Field(default=0,ge=0,le=32000)
    limit:int=Field(default=4000,ge=1,le=8000)

class CreativeWritingStart(Strict):
    entry_state:str=Field(default='',max_length=500)
    exit_state:str=Field(default='',max_length=500)
    goal_han:int|None=Field(default=None,ge=0,le=16000)
    steps:list[str]=Field(default_factory=list,max_length=4)
    number:int=Field(ge=1,le=99999)
    context_id:str=Field(pattern=r'^ctx_[0-9a-f]{32}$')
    goal:str=Field(min_length=1,max_length=2500)
    timeout:int=Field(default=180,ge=30,le=300)
    output_characters:int=Field(default=8000,ge=100,le=16000)
    @field_validator('steps')
    @classmethod
    def bounded_steps(cls,steps):
        if any(not x.strip() or len(x)>800 for x in steps):raise ValueError('每段创作要求需为1至800字')
        return steps

class CreativeWritingRead(Strict):
    id:str=Field(pattern=r'^director_[0-9a-f]{32}$')
    start:int=Field(default=0,ge=0,le=32000)
    limit:int=Field(default=4000,ge=1,le=8000)
class CreativeWritingStage(Strict):
    id:str=Field(pattern=r'^director_[0-9a-f]{32}$')
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')

class WorldDraft(Strict):
    name:str=Field(min_length=1,max_length=200)
    category:str=Field(default='term',max_length=64)
    summary:str=Field(default='',max_length=4000)
class WorldEdit(Strict):id:str;summary:str=Field(max_length=4000)
class Note(Strict):text:str=Field(min_length=1,max_length=4000)
class Link(Strict):
    source_type:str;source_id:str;target_type:str;target_id:str
    description:str=Field(default='',max_length=1000)
class Theme(Strict):theme:ThemeId
class Font(Strict):size:int=Field(ge=14,le=32)
class Leading(Strict):height:float=Field(ge=1.3,le=2.8)
class Section(Strict):section:Literal['general','appearance','writing','api','models','assistant','plugins','images','storage','backup','keys','help']
class Revision(Strict):instruction:str=Field(default='保留事实与人物声音，改善自然度',max_length=2000)
class AITask(Strict):
    type:Literal['contract_check','continuity_check','story_knowledge_check','character_consistency_check','chapter_plan_review','chapter_review','final_check']
    chapter:int|None=Field(default=None,ge=1,le=99999)
class Backup(Strict):note:str=Field(default='AI 助手手动备份',max_length=200)

class ExperimentTarget(Strict):
    id:str=Field(pattern=r'^exp_[0-9a-f]{32}$')
class ExperimentTemplate(Strict):
    template_id:str=Field(pattern=r'^exp_[0-9a-f]{32}$')
    name:str=Field(default='',max_length=200)
class ExperimentRun(ExperimentTarget):
    version:int=Field(ge=1)
    fingerprint:str=Field(min_length=64,max_length=64)
class ExperimentDesign(Strict):
    instruction:str=Field(min_length=1,max_length=4000)
    mode:Literal['design','acceptance','adversarial','explain','rebuild','rebuttal']='design'
    strength:Literal['explore','strict','extreme']='explore'
    experiment_id:str|None=Field(default=None,pattern=r'^exp_[0-9a-f]{32}$')
    report_id:str|None=Field(default=None,pattern=r'^run_[0-9a-f]{32}$')
class ExperimentReport(Strict):
    id:str=Field(pattern=r'^run_[0-9a-f]{32}$')

class PageRange(Strict):
    offset:int=Field(default=0,ge=0,le=100000)
    limit:int=Field(default=100,ge=1,le=200)
class ChapterRead(Chapter):
    start:int=Field(default=0,ge=0,le=10000000)
    limit:int=Field(default=8000,ge=1,le=16000)
class Reference(Strict):
    kind:Literal['chapter','character','world','document']
    number:int|None=Field(default=None,ge=0,le=99999)
    id:str|None=Field(default=None,max_length=120)
class Layout(Strict):preset:Literal['writing','reference','ai','focus','personal','save','reset']
class Entries(Strict):kind:Literal['inspiration','todo','revision']='inspiration'
class PythonPlan(Strict):
    code:str=Field(min_length=1,max_length=64000)
    title:str=Field(default='Python 操作计划',max_length=120)
    timeout:int=Field(default=90,ge=10,le=180)
class TextTask(Strict):
    instruction:str=Field(min_length=1,max_length=2000)
    chapters:list[int]=Field(default_factory=list,max_length=10)
    controls:RequestControls|None=None
class TaskEvents(Target):after:int=Field(default=0,ge=0)
class TaskWait(Target):timeout:int=Field(default=30,ge=1,le=150)
class TaskSteer(Target):instruction:str=Field(min_length=1,max_length=2000)
class TaskShare(Target):
    persona:Literal['yoshino','rem','assistant']
    note:str=Field(default='',max_length=500)
class InspirationTodos(Strict):
    ids:list[str]=Field(min_length=1,max_length=30)
    chapter:int=Field(ge=0,le=99999)
