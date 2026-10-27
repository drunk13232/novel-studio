"""Declarative plugin contract. No host imports or install hooks."""
import re
from typing import Literal,Any
from pydantic import BaseModel,ConfigDict,Field,model_validator
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
ID=r'^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$'
VERSION=r'^[0-9]+\.[0-9]+\.[0-9]+$'
SECTIONS={'general','appearance','writing','api','models','assistant','plugins','images','storage','backup','keys','help'}
PAGES={'write','outline','characters','world','references','styles','knowledge','timeline','data','book','search','notes','gallery','images','history','worldlogic','roleplay','literary','python'}
class Option(Strict):
    id:str=Field(pattern=r'^[a-z][a-z0-9_]{0,39}$')
    label:str=Field(min_length=1,max_length=80)
    description:str=Field(default='',max_length=300)
    type:Literal['string','integer','number','boolean','select']='string'
    default:Any=''
    choices:list[str]=Field(default_factory=list,max_length=30)
    minimum:float|None=None
    maximum:float|None=None
    @model_validator(mode='after')
    def valid(self):
        if re.search(r'key|token|password|secret|credential|authorization',self.id,re.I):raise ValueError('Plugin settings cannot contain credentials; use the existing provider settings')
        if self.type=='select' and not self.choices:raise ValueError('Select needs choices')
        if self.minimum is not None and self.maximum is not None and self.minimum>self.maximum:raise ValueError('Invalid option bounds')
        self.check(self.default);return self
    def check(self,value):
        if self.type=='boolean':ok=type(value)is bool
        elif self.type in {'integer','number'}:
            import math
            ok=type(value) in ({int} if self.type=='integer' else {int,float}) and math.isfinite(value) and (self.minimum is None or value>=self.minimum) and (self.maximum is None or value<=self.maximum)
        else:ok=isinstance(value,str) and len(value)<=1000 and (self.type!='select' or value in self.choices)
        if not ok:raise ValueError('Invalid setting: '+self.id)
        return value
class Target(Strict):
    type:Literal['settings','page']
    value:str=Field(min_length=1,max_length=40)
    @model_validator(mode='after')
    def valid(self):
        if self.value not in (SECTIONS if self.type=='settings' else PAGES):raise ValueError('Unknown application entry')
        return self
class Command(Strict):
    id:str=Field(pattern=ID,max_length=80)
    title:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=600)
    kind:Literal['action','python','entry']
    action:str|None=None
    arguments:dict=Field(default_factory=dict)
    script:str|None=None
    target:Target|None=None
    @model_validator(mode='after')
    def valid(self):
        if self.kind=='action' and (not self.action or self.script or self.target):raise ValueError('Action command requires only an action')
        if self.kind=='python' and (not self.script or self.action or self.target or self.arguments):raise ValueError('Python command requires only a script')
        if self.kind=='entry' and (not self.target or self.action or self.script or self.arguments):raise ValueError('Entry command requires only a target')
        return self
class Resource(Strict):
    id:str=Field(pattern=ID,max_length=80)
    title:str=Field(min_length=1,max_length=100)
    kind:Literal['experiment','reference','template']
    file:str=Field(min_length=1,max_length=120)
class Manifest(Strict):
    schema_version:Literal['novel-studio-plugin/1']
    id:str=Field(pattern=ID,min_length=3,max_length=80)
    name:str=Field(min_length=1,max_length=100)
    version:str=Field(pattern=VERSION,max_length=32)
    min_app_version:str=Field(default='2.20.0',pattern=VERSION,max_length=32)
    description:str=Field(min_length=1,max_length=1200)
    author:str=Field(min_length=1,max_length=100)
    license:str=Field(min_length=1,max_length=150)
    actions:list[str]=Field(default_factory=list,max_length=66)
    commands:list[Command]=Field(default_factory=list,max_length=30)
    settings:list[Option]=Field(default_factory=list,max_length=30)
    resources:list[Resource]=Field(default_factory=list,max_length=20)
    files:dict[str,str]=Field(default_factory=dict,max_length=60)
    @model_validator(mode='after')
    def unique(self):
        for items in (self.commands,self.settings,self.resources):
            if len({v.id for v in items})!=len(items):raise ValueError('Duplicate contribution ID')
        if len(set(self.actions))!=len(self.actions):raise ValueError('Duplicate permissions')
        if not self.commands and not self.resources:raise ValueError('Plugin has no contributions')
        return self
class Change(Strict):
    revision:str=Field(pattern=r'^[a-f0-9]{64}$')
    enabled:bool
class Configure(Strict):
    revision:str=Field(pattern=r'^[a-f0-9]{64}$')
    values:dict=Field(default_factory=dict)
class Install(Strict):
    token:str=Field(pattern=r'^[a-f0-9]{32}$')
    expected_revision:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
