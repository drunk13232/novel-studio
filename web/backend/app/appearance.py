"""Bounded appearance preferences, shared with existing UI Actions."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

ThemeId=Literal['moon','mist','night','amber','sky','plum','yoshino','rem','rem-night','manuscript','ink','observatory','gothic','cyber','greenhouse','minimal']
THEME_IDS=tuple(ThemeId.__args__)
DARK_THEMES=frozenset({'night','plum','rem-night','observatory','gothic','cyber'})

class ThemeCustomization(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    name:str=Field(default='',max_length=60,pattern=r'^[^\x00-\x1f]*$')
    accent:str|None=Field(default=None,pattern=r'^#[0-9a-fA-F]{6}$')
    ink:str|None=Field(default=None,pattern=r'^#[0-9a-fA-F]{6}$')
    background:str|None=Field(default=None,pattern=r'^#[0-9a-fA-F]{6}$')
    radius:int|None=Field(default=None,ge=0,le=20)
    decoration:int=Field(default=70,ge=0,le=100)
    texture:int=Field(default=12,ge=0,le=50)
    motion:int=Field(default=70,ge=0,le=100)
    density:Literal['comfortable','compact']='comfortable'
