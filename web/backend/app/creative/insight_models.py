"""Typed author-only narrative observations and simulated reader profiles."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class CurveAnalyze(Strict):
    chapter_ids: list[str] = Field(default_factory=list, max_length=1000)
    whole_book: bool = False
    character_ids: list[str] = Field(default_factory=list, max_length=4)
    track_ids: list[str] = Field(default_factory=list, max_length=4)

class CurveOverride(Strict):
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    chapter_id: str = Field(min_length=1, max_length=100)
    series_id: str = Field(default='book', max_length=150)
    tension: float | None = Field(default=None, ge=0, le=10)
    emotion: float | None = Field(default=None, ge=0, le=10)
    note: str = Field(default='', max_length=4000)
    clear: bool = False

class CurveSettings(Strict):
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    flat_count: int = Field(default=3, ge=2, le=30)
    flat_threshold: float = Field(default=3, ge=0, le=10)

class ReaderPersona(Strict):
    id: str = Field(default='', max_length=80)
    name: str = Field(min_length=1, max_length=100)
    age_group: str = Field(default='', max_length=100)
    preferences: str = Field(default='', max_length=1500)
    abandonment_triggers: str = Field(default='', max_length=1500)
    payment_willingness: str = Field(default='', max_length=600)
    focus: Literal['general','suspense','character','pacing','editor'] = 'general'

class PersonaSave(Strict):
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    persona: ReaderPersona

class PersonaRemove(Strict):
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    confirm: Literal[True]

class ReaderReaction(Strict):
    kind: Literal['reaction','abandonment','moving']
    comment: str = Field(min_length=1, max_length=2000)
    evidence: list[str] = Field(default_factory=list, max_length=5)
    uncertainty: str = Field(min_length=1, max_length=1000)

class ReaderPrepare(Strict):
    persona_ids: list[str] = Field(min_length=1, max_length=4)
    chapter_ids: list[str] = Field(default_factory=list, max_length=1000)
    whole_book: bool = False
    model: str | None = Field(default=None, max_length=300)
    max_calls: int = Field(default=20, ge=1, le=1000)

class ReaderApprove(Strict):
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    preview_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    confirm: Literal[True]

class ReaderNext(Strict):
    etag: str = Field(pattern=r'^[a-f0-9]{64}$')
    confirm: Literal[True]

class ReaderRetry(ReaderNext):
    cell_id: str = Field(pattern=r'^cell_[0-9]+$')
