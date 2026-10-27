"""Typed literary annotations for the existing author notebook, not story facts."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
Kind=Literal['style','thought','clue','logic','clue_event']
Phase=Literal['PLANNED','PLACED','REINFORCED','MISDIRECTED','RESOLVED','PARTIAL','INTENTIONALLY_OPEN','ABANDONED']
class Evidence(Strict):
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    start:int=Field(ge=0)
    end:int=Field(gt=0)
    quote:str=Field(min_length=1,max_length=1500)
    scene_id:str=Field(default='',max_length=80)
class Link(Strict):
    type:Literal['character','chapter','scene','thread','clue','event','entity','item','record']
    id:str=Field(min_length=1,max_length=100)
class Position(Strict):
    character:str=Field(min_length=1,max_length=100)
    stance:str=Field(min_length=1,max_length=500)
    experience:str=Field(default='',max_length=500)
    choice:str=Field(default='',max_length=500)
    cost:str=Field(default='',max_length=500)
    challenge:str=Field(default='',max_length=500)
    change:str=Field(default='',max_length=500)
class Dependency(Strict):
    before:str=Field(min_length=1,max_length=100)
    after:str=Field(min_length=1,max_length=100)
    kind:Literal['strict_order','causal','conditional','association']='conditional'
    basis:str=Field(min_length=1,max_length=800)
class CoreDetails(Strict):
    version:Literal[1]=1
    kind:Kind
    title:str=Field(min_length=1,max_length=160)
    frame:str=Field(default='',max_length=500)
    question:str=Field(default='',max_length=1500)
    positions:list[Position]=Field(default_factory=list,max_length=8)
    links:list[Link]=Field(default_factory=list,max_length=20)
    evidence:list[Evidence]=Field(default_factory=list,max_length=8)
    symbols:list[str]=Field(default_factory=list,max_length=12)
    secret:str=Field(default='',max_length=1500)
    knowledge_fact_id:str=Field(default='',max_length=100)
    phase:Phase='PLANNED'
    parent:str=Field(default='',max_length=100)
    original_clue:str=Field(default='',max_length=100)
    dependencies:list[Dependency]=Field(default_factory=list,max_length=32)
    origin:Literal['AUTHOR','AI_ACCEPTED']='AUTHOR'
class Save(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    id:str=Field(default='',max_length=80)
    text:str=Field(min_length=1,max_length=12000)
    details:CoreDetails
    confirm:Literal[True]
class Event(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    phase:Phase
    text:str=Field(min_length=1,max_length=2000)
    evidence:list[Evidence]=Field(default_factory=list,max_length=6)
    confirm:Literal[True]
class Profile(Strict):
    title:str=Field(min_length=1,max_length=160)
    directives:list[str]=Field(min_length=1,max_length=30)
    character_id:str=Field(default='',max_length=100)
    scene_id:str=Field(default='',max_length=100)
    confirm:Literal[True]
class Adopt(Strict):
    record_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    pov:str=Field(default='',max_length=100)
    scene_id:str=Field(default='',max_length=100)
    writer_text:str=Field(min_length=1,max_length=3000)
    confirm:Literal[True]
class ReportCard(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    finding:int=Field(ge=0,le=39)
    kind:Literal['style','thought','clue','logic']
    title:str=Field(min_length=1,max_length=160)
    text:str=Field(min_length=1,max_length=12000)
    confirm:Literal[True]
class Quote(Strict):
    source_id:str=Field(min_length=1,max_length=350)
    quote:str=Field(min_length=1,max_length=1500)
class Finding(Strict):
    dimension:str=Field(min_length=1,max_length=100)
    claim:str=Field(min_length=1,max_length=2000)
    classification:Literal['TEXT_OBSERVATION','CONDITIONAL_RISK','INSUFFICIENT_EVIDENCE','INTENTIONAL_AMBIGUITY','AI_INTERPRETATION']
    evidence:list[Quote]=Field(default_factory=list,max_length=8)
    alternative:str=Field(default='',max_length=1800)
    missing_premise:str=Field(default='',max_length=1200)
    limitation:str=Field(min_length=1,max_length=1200)
    suggestion:str=Field(default='',max_length=1800)
    writer_instruction:str=Field(default='',max_length=2000)
class Reading(Strict):
    perspective:str=Field(min_length=1,max_length=200)
    interpretation:str=Field(min_length=1,max_length=2000)
    evidence:list[Quote]=Field(min_length=1,max_length=8)
    limitation:str=Field(min_length=1,max_length=1000)
class Analysis(Strict):
    summary:str=Field(min_length=1,max_length=3000)
    findings:list[Finding]=Field(max_length=40)
    counter_readings:list[Reading]=Field(default_factory=list,max_length=8)
    style_directives:list[str]=Field(default_factory=list,max_length=24)
    questions:list[str]=Field(default_factory=list,max_length=12)
    limitations:list[str]=Field(min_length=1,max_length=12)
class Execute(Strict):
    record_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirm:Literal[True]
