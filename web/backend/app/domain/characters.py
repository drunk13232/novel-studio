import copy
import json
import re
import uuid
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.projects.service import write_yaml

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

Text=str|None
Scalar=str|float|None

class Identity(Strict):
    summary:Text=None
    gender:Text=None
    age_at_start:Scalar=None
    birthday:Text=None
    occupation:Text=None
    affiliation:Text=None
    family_background:Text=None
class Appearance(Strict):
    summary:Text=None
    height:Scalar=None
    build:Text=None
    features:list[str]=Field(default_factory=list)
    clothing_preferences:list[str]=Field(default_factory=list)
    facial_features:Text=None
    hairstyle:Text=None
    eye_color:Text=None
    age_changes:Text=None
class Personality(Strict):
    core_traits:list[str]=Field(default_factory=list)
    strengths:list[str]=Field(default_factory=list)
    flaws:list[str]=Field(default_factory=list)
    contradictions:list[str]=Field(default_factory=list)
class Psychology(Strict):
    core_desire:Text=None
    core_need:Text=None
    fear:Text=None
    wound:Text=None
    values:list[str]=Field(default_factory=list)
    boundaries:list[str]=Field(default_factory=list)
class Behavior(Strict):
    default_patterns:list[str]=Field(default_factory=list)
    stress_patterns:list[str]=Field(default_factory=list)
    habits:list[str]=Field(default_factory=list)
    tells:list[str]=Field(default_factory=list)
class Speech(Strict):
    tone:Text=None
    vocabulary:Text=None
    sentence_style:Text=None
    habits:list[str]=Field(default_factory=list)
    avoids:list[str]=Field(default_factory=list)
    catchphrases:list[str]=Field(default_factory=list)
    forms_of_address:list[str]=Field(default_factory=list)
class Biography(Strict):
    origin:Text=None
    education:Text=None
    important_events:list[str]=Field(default_factory=list)
    trauma:Text=None
    turning_points:list[str]=Field(default_factory=list)
    first_appearance:Text=None
class Abilities(Strict):
    skills:list[str]=Field(default_factory=list)
    knowledge:list[str]=Field(default_factory=list)
    combat:Text=None
    professional:Text=None
    weaknesses:list[str]=Field(default_factory=list)
    growth_limits:list[str]=Field(default_factory=list)
class Period(Strict):
    label:str
    story_start:str=''
    story_end:str=''
    description:str=''
    appearance:str=''
class Goals(Strict):
    initial_short_term:list[str]=Field(default_factory=list)
    initial_long_term:list[str]=Field(default_factory=list)
class Relationship(Strict):
    type:list[str]=Field(default_factory=list)
    public_state:dict[str,str|float|None]=Field(default_factory=dict)
    private_state:dict[str,str|None]=Field(default_factory=dict)
    history:list[str]=Field(default_factory=list)
class Relationships(Strict):
    initial:dict[str,Relationship]=Field(default_factory=dict)
class Story(Strict):
    function:Text=None
    arc_start:Text=None
    arc_direction:Text=None
    possible_end:Text=None
class Secrets(Strict):
    author_only:list[str]=Field(default_factory=list)
class Lock(Strict):
    path:str=Field(min_length=1,max_length=150)
    value:str|float|list[str]|None
    statement:str=Field(min_length=1,max_length=1000)
class Canon(Strict):
    hard:list[Lock]=Field(default_factory=list)
    strong:list[str]=Field(default_factory=list)
    soft:list[str]=Field(default_factory=list)
class CharacterCanon(Strict):
    schema_version:Literal['0.4']='0.4'
    id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    name:Text=None
    aliases:list[str]=Field(default_factory=list)
    role:Literal['PROTAGONIST','STRUCTURAL','SECONDARY','TEMPORARY']='SECONDARY'
    importance:Literal['MAIN','SUPPORTING','MINOR']='SUPPORTING'
    identity:Identity=Field(default_factory=Identity)
    appearance:Appearance=Field(default_factory=Appearance)
    personality:Personality=Field(default_factory=Personality)
    psychology:Psychology=Field(default_factory=Psychology)
    behavior:Behavior=Field(default_factory=Behavior)
    speech:Speech=Field(default_factory=Speech)
    biography:Biography=Field(default_factory=Biography)
    abilities:Abilities=Field(default_factory=Abilities)
    periods:list[Period]=Field(default_factory=list)
    goals:Goals=Field(default_factory=Goals)
    relationships:Relationships=Field(default_factory=Relationships)
    story:Story=Field(default_factory=Story)
    secrets:Secrets=Field(default_factory=Secrets)
    canon:Canon=Field(default_factory=Canon)
    tags:list[str]=Field(default_factory=list)

class CharacterSave(Strict):
    canonical:CharacterCanon
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')

def at(value,path):
    try:
        for part in path.split('.'):value=value[part]
        return value
    except (KeyError,TypeError):raise ConsoleError('锁定路径不存在：'+path,422)

def normalize(value):
    if not isinstance(value,dict):raise ConsoleError('人物卡必须为映射',422)
    if value.get('schema_version')=='0.4':return CharacterCanon.model_validate(value).model_dump()
    if not isinstance(value.get('arc',{}),dict) or not isinstance(value.get('canon',{}),dict):raise ConsoleError('旧人物卡结构无效',422)
    for key in ['identity','appearance','personality','core_desire','fear','speech','story_function']:
        if value.get(key) is not None and not isinstance(value[key],str):raise ConsoleError('旧人物卡字段类型无效：'+key,422)
    c=CharacterCanon(id=value['id'],name=value.get('name'),role=value.get('role') or 'SECONDARY').model_dump()
    c['aliases']=value.get('aliases',[]);c['identity']['summary']=value.get('identity');c['appearance']['summary']=value.get('appearance')
    c['personality'].update(core_traits=[value['personality']] if value.get('personality') else [],strengths=value.get('strengths',[]),flaws=value.get('weaknesses',[]))
    c['psychology'].update(core_desire=value.get('core_desire'),fear=value.get('fear'),values=value.get('values',[]));c['speech']['tone']=value.get('speech')
    c['story'].update(function=value.get('story_function'),arc_start=value.get('arc',{}).get('start'),arc_direction=value.get('arc',{}).get('direction'),possible_end=value.get('arc',{}).get('potential_end'))
    c['canon']['hard']=[{'path':'identity.summary','value':c['identity']['summary'],'statement':x} for x in value.get('canon',{}).get('locked',[])]
    return CharacterCanon.model_validate(c).model_dump()

def validate_card(card,id,previous=None):
    card=CharacterCanon.model_validate(card).model_dump()
    if card['id']!=id:raise ConsoleError('人物稳定 ID 不匹配',422)
    for lock in card['canon']['hard']:
        if lock['path']=='id' or lock['path'].startswith(('canon.','secrets.')):raise ConsoleError('此字段不能作为人物可重做锁定',422)
        if at(card,lock['path'])!=lock['value']:raise ConsoleError('人物 HARD 与字段值冲突：'+lock['statement'],409)
    if previous:
        if card['canon']['hard']!=previous['canon']['hard']:raise ConsoleError('AI 不得修改锁定清单',409)
        for lock in previous['canon']['hard']:
            if at(card,lock['path'])!=lock['value']:raise ConsoleError('AI 修改了人物 HARD：'+lock['statement'],409)
    return card

class CharacterService:
    def __init__(self,registry):self.registry=registry
    def path(self,id):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',id):raise ConsoleError('无效人物 ID',403)
        return 'characters/'+id+'.yaml'
    def writable(self,project):
        if self.registry.get(project)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
        return self.registry.workspace(project)
    def get(self,project,id):
        ws=self.registry.workspace(project)
        return self._get(ws,id,ws.yaml_file('state/knowledge-state.yaml').get('facts',{}),ws.yaml_file('state/chapter-ledger.yaml').get('entries',[]))
    def _get(self,ws,id,facts,entries):
        # Request-local shared reads. No cross-project or persistent knowledge cache.
        p=self.path(id);raw=ws.content(p);parsed=ws.parse_yaml(raw['content']);card=normalize(parsed)
        runtime=ws.yaml_file('state/characters/'+id+'.yaml')
        knowledge={k:[] for k in ['knows','suspects','false_beliefs','does_not_know']}
        for fid,fact in facts.items():
            for kind,central in [('knows','known_by'),('suspects','suspected_by')]:
                if any(x.get('character_id')==id for x in fact.get(central,[])):knowledge[kind].append({'id':fid,'text':fact.get('canonical_truth'),'source':central})
            if id in fact.get('false_beliefs',{}):knowledge['false_beliefs'].append({'id':fid,'text':fact['false_beliefs'][id].get('belief'),'source':'false_beliefs'})
            if fid in runtime.get('knowledge',{}).get('does_not_know',[]):knowledge['does_not_know'].append({'id':fid,'text':'明确不知道此事实','source':'character knowledge projection'})
        appearances=[]
        for entry in entries:
            if id in entry.get('characters',entry.get('active_characters',[])):appearances.append(entry.get('chapter'))
        return {'canonical':card,'etag':raw['etag'],'runtime':runtime,'knowledge':knowledge,'appearances':appearances,'legacy':parsed.get('schema_version')!='0.4'}
    def list(self,project):
        ws=self.registry.workspace(project)
        facts=ws.yaml_file('state/knowledge-state.yaml').get('facts',{});entries=ws.yaml_file('state/chapter-ledger.yaml').get('entries',[])
        return [self._get(ws,Path(f['path']).stem,facts,entries) for f in ws.list_files() if f['path'].startswith('characters/') and f['path'].endswith('.yaml')]
    def references(self,project,card):
        for other in card['relationships']['initial']:
            if other==card['id']:raise ConsoleError('人物关系对象不能是自身',422)
            self.get(project,other) # only this project's registry/workspace
    def seed_runtime(self,ws,card):
        operations=self.runtime_initializations(ws,card)
        for op in operations:write_yaml(ws.resolve(op['path']),yaml.safe_load(op['content']))
    def runtime_initializations(self,ws,card):
        relative='state/characters/'+card['id']+'.yaml';p=ws.resolve(relative)
        if p.exists():return []
        state=yaml.safe_load((self.registry.engine/'templates/state/character.yaml').read_text(encoding='utf8'))
        state.update(id=card['id'],name=card['name'],aliases=card['aliases'])
        state['goals'].update(short_term=card['goals']['initial_short_term'],long_term=card['goals']['initial_long_term'])
        return [{'path':relative,'content':yaml.safe_dump(state,allow_unicode=True,sort_keys=False),'action':'write'}]
    def create(self,project,value):
        with self.registry.lock:
            ws=self.writable(project);id='character_'+uuid.uuid4().hex
            value={**value,'id':id};card=validate_card(value,id);self.references(project,card)
            write_yaml(ws.resolve(self.path(id)),card);self.seed_runtime(ws,card)
            return self.get(project,id)
    def save(self,project,id,value,etag):
        with self.registry.lock:
            ws=self.writable(project);card=validate_card(value,id);self.references(project,card)
            current=ws.content(self.path(id))
            if current['etag']!=etag:raise ConsoleError('人物文件已变化，请刷新合并',409)
            raw=ws.parse_yaml(current['content'])
            if raw.get('schema_version')!='0.4':
                backup=ws.resolve('metadata/character-migrations/'+id+'-original.yaml')
                if not backup.exists():write_yaml(backup,raw)
            ws.save(self.path(id),yaml.safe_dump(card,allow_unicode=True,sort_keys=False),etag)
            return self.get(project,id)
