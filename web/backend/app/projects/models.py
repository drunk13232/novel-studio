from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .writing_config import WritingConfig
from app.studio import UiLocale

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

Phase = Literal['IDEA','FOUNDATION','OUTLINING','WRITING','REVISION','COMPLETED','ARCHIVED']

class Idea(Strict):
    title: str = Field(min_length=1,max_length=180)
    writing: WritingConfig | None = None
    language: UiLocale = 'zh-CN'
    genre: str = Field(default='其他',max_length=40)
    secondary: list[str] = Field(default_factory=list,max_length=12)
    premise: str = Field(default='',max_length=3000)
    idea: str = Field(default='',max_length=8000)
    attractions: list[str] = Field(default_factory=list,max_length=12)
    tone: str = Field(default='',max_length=1500)
    pacing: str = Field(default='',max_length=40)
    narrative: str = Field(default='',max_length=40)
    romance: str = Field(default='',max_length=400)
    style: str = Field(default='',max_length=4000)
    total_words: str = Field(default='',max_length=120)
    estimated_chapters: str = Field(default='',max_length=120)
    estimated_volumes: str = Field(default='',max_length=120)
    locked_constraints: dict[Literal['protagonist','era','ending'],str] = Field(default_factory=dict)
    fanfiction: dict[Literal['source','timeline','characters','major_changes','original_characters'],str] = Field(default_factory=dict)

class CharacterConcept(Strict):
    name: str
    identity: str
    personality: str
    core_desire: str
    fear: str
    story_function: str
    arc: str

class Macro(Strict):
    opening: str
    development: str
    midpoint: str
    escalation: str
    climax: str
    ending_direction: str

class Volume(Strict):
    title: str
    function: str
    protagonist_change: str
    conflict: str
    ending_state: str

class Proposal(Strict):
    premise: str
    core_conflict: str
    story_engine: str
    themes: list[str]
    reader_promises: list[str]
    protagonist_concept: CharacterConcept
    major_character_roles: list[CharacterConcept] = Field(max_length=6)
    world_concept: str
    power_or_rule_system: str
    major_factions: list[str]
    macro_structure: Macro
    volume_concepts: list[Volume] = Field(max_length=20)
    risks: list[str]
    open_questions: list[str]
    user_locked: dict[str,str]
    lock_verdict: Literal['PASS','FAIL']
    lock_reason: str

class DraftCreate(Strict):
    input: Idea

class DraftEdit(Strict):
    version: int
    input: Idea | None = None
    proposal: Proposal | None = None
    discard_proposal: bool = False
    wizard_step: int | None = Field(default=None,ge=1,le=6)
    accepted: bool | None = None

class DraftDiscard(Strict):
    version: int
    confirm: Literal[True]

class ProjectCreate(Strict):
    draft_id: str
    version: int
    confirm: Literal[True]
    accept_proposal: bool = False

class ProjectPatch(Strict):
    etag: str
    title: str | None = Field(default=None,min_length=1,max_length=180)
    phase: Phase | None = None

class ReviewAccept(Strict):
    version: int
    confirm: Literal[True]

class ChangeEdit(Strict):
    version: int
    content: str = Field(max_length=2*1024*1024)

class FoundationTask(Strict):
    type: Literal['story_architect','story_architect_refine','world_expand','character_create','character_refine','master_outline_generate','volume_outline_generate']
    version: int | None = None
    section: str | None = Field(default=None,max_length=100)
    instruction: str = Field(default='',max_length=8000)
    target: str | None = Field(default=None,max_length=240)

class ChangeOutput(Strict):
    content: str
    explanation: str
    lock_verdict: Literal['PASS','FAIL']
    lock_reason: str
