"""Versioned, evidence-bound evaluation contracts inside the existing ReviewCenter."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
class Strict(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
Dimension=Literal['style','character','structure','thought','clue','logic','emotion','innovation']
Scope=Literal['selection','chapter','chapters','range','book']
class Anchors(Strict):
    low:str=Field(min_length=1,max_length=1200)
    middle:str=Field(min_length=1,max_length=1200)
    high:str=Field(min_length=1,max_length=1200)
class Criterion(Strict):
    id:Dimension
    enabled:bool=True
    weight:float=Field(default=1,gt=0,le=100)
    focus:str=Field(min_length=1,max_length=1800)
    anchors:Anchors
class Rubric(Strict):
    name:str=Field(min_length=1,max_length=160)
    version:str=Field(default='1',min_length=1,max_length=40)
    positioning:str=Field(default='',max_length=2000)
    dimensions:list[Criterion]=Field(min_length=1,max_length=8)
    @model_validator(mode='after')
    def valid(self):
        if len({d.id for d in self.dimensions})!=len(self.dimensions):raise ValueError('评价维度不能重复')
        if not any(d.enabled for d in self.dimensions):raise ValueError('至少选择一个评价维度')
        return self
class Target(Strict):
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(default='',max_length=64)
class Selection(Strict):
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    start:int=Field(ge=0)
    end:int=Field(gt=0)
    quote:str=Field(min_length=1,max_length=100000)
class Request(Strict):
    purpose:Literal['scoring','editorial']='scoring'
    editorial_goal:str=Field(default='',max_length=2000)
    editorial_lens:str=Field(default='',max_length=2000)
    editorial_methods:list[Literal['context','scene','character','style','continuity','review']]=Field(default_factory=lambda:['context','continuity','review'],max_length=4)
    scope:Scope='chapter'
    targets:list[Target]=Field(default_factory=list,max_length=2000)
    selection:Selection|None=None
    volume_id:str=Field(default='',max_length=100)
    first:int=Field(default=1,ge=1,le=99999)
    last:int=Field(default=1,ge=1,le=99999)
    rubric:Rubric
    model:str|None=Field(default=None,max_length=250)
    second_model:str|None=Field(default=None,max_length=250)
    literary_ids:list[str]=Field(default_factory=list,max_length=12)
    order:Literal['forward','reverse']='forward'
    allow_author_context:bool=False
class Create(Strict):
    request:Request
    preview_hash:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirm:Literal[True]
class EditorialPreset(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    request:Request
    confirm:Literal[True]
class Run(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    calls:int=Field(default=4,ge=1,le=20)
    seconds:int=Field(default=600,ge=30,le=1800)
    confirm:Literal[True]
    retry_incomplete:bool=False
class SavedRubric(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    rubric:Rubric
    confirm:Literal[True]
class Quote(Strict):
    source_id:str=Field(pattern=r'^source_[0-9]{1,4}$')
    quote:str=Field(min_length=1,max_length=500)
class DimensionResult(Strict):
    dimension:Dimension
    status:Literal['SCORED','NA','INSUFFICIENT_EVIDENCE']
    score:float|None=Field(default=None,ge=0,le=100)
    rationale:str=Field(min_length=1,max_length=1200)
    strengths:list[str]=Field(default_factory=list,max_length=3)
    weaknesses:list[str]=Field(default_factory=list,max_length=3)
    evidence:list[Quote]=Field(default_factory=list,max_length=3)
    uncertainty:str=Field(min_length=1,max_length=1000)
    alternative:str=Field(default='',max_length=1000)
    influential_judgment:str=Field(default='',max_length=1000)
    suggestion:str=Field(default='',max_length=1200)
class EditorialFinding(Strict):
    dimension:Dimension
    priority:Literal['HIGH','MEDIUM','LOW']
    classification:Literal['TEXT_OBSERVATION','CONDITIONAL_RISK','AI_INTERPRETATION','INSUFFICIENT_EVIDENCE','INTENTIONAL_DIFFERENCE']
    diagnosis:str=Field(min_length=1,max_length=1600)
    why:str=Field(min_length=1,max_length=1400)
    evidence:list[Quote]=Field(default_factory=list,max_length=5)
    alternatives:list[str]=Field(default_factory=list,max_length=3)
    revision_options:list[str]=Field(default_factory=list,max_length=3)
    tradeoffs:str=Field(default='',max_length=1200)
    uncertainty:str=Field(min_length=1,max_length=1200)
class EditorialLetter(Strict):
    declared_lens:str=Field(min_length=1,max_length=1800)
    intended_shape:str=Field(min_length=1,max_length=1400)
    set_aside_rules:list[str]=Field(default_factory=list,max_length=6)
    findings:list[EditorialFinding]=Field(default_factory=list,max_length=6)
    questions:list[str]=Field(default_factory=list,max_length=8)
    observations:list['EditorialObservation']=Field(default_factory=list,max_length=12)
class EditorialObservation(Strict):
    observation:str=Field(min_length=1,max_length=1200)
    epistemic:Literal['NARRATOR_ACCOUNT','ATTRIBUTED_CLAIM','BELIEF','AUTHOR_PLAN','AI_INTERPRETATION','TIME_ANCHOR']
    evidence:list[Quote]=Field(min_length=1,max_length=4)
    temporal_note:str=Field(default='',max_length=600)
class Assessment(Strict):
    summary:str=Field(min_length=1,max_length=2200)
    horizon:Literal['LOCAL','CHAPTER','SELECTED_RANGE','BOOK']
    dimensions:list[DimensionResult]=Field(default_factory=list,max_length=8)
    limitations:list[str]=Field(min_length=1,max_length=12)
    editorial:EditorialLetter|None=None
class Note(Strict):
    text:str=Field(max_length=10000)
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
class Compare(Strict):
    ids:list[str]=Field(min_length=2,max_length=4)
    anonymous:bool=False
class Bridge(Strict):
    model:int=Field(default=0,ge=0,le=1)
    node:str=Field(pattern=r'^node_[0-9]+$')
    dimension:Dimension
    editorial_issue:int|None=Field(default=None,ge=0,le=5)
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirm:Literal[True]
