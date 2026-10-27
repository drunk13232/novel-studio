import copy
import re
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from .storage import safe,read,write,uid,now,digest

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class CustomField(Strict):
    id:str=Field(pattern=r'^[a-z][a-z0-9_]{0,63}$')
    name:str=Field(min_length=1,max_length=100)
    type:Literal['text','longtext','number','date','select','multiselect','boolean','image','entity','tags','quantity','calendar','list','group','rule','evidence','entities']='text'
    options:list[str]=Field(default_factory=list,max_length=100)
    help:str=Field(default='',max_length=1200)
    group:str=Field(default='基本信息',max_length=80)
    order:int=Field(default=0,ge=0,le=10000)
    required:bool=False
    primary:bool=True
    ai_allowed:bool=True
    author_only:bool=False
    locked:bool=False
    default:Any=None
    minimum:float|None=None
    maximum:float|None=None
    unit:str=Field(default='',max_length=80)
    target_types:list[Literal['entity','character','chapter']]=Field(default_factory=list,max_length=3)
    visible_when:dict[str,Any]=Field(default_factory=dict,max_length=1)
    children:list['CustomField']=Field(default_factory=list,max_length=20)
class Category(Strict):
    id:str=Field(pattern=r'^[a-z][a-z0-9_-]{0,63}$')
    name:str=Field(min_length=1,max_length=100)
    group:str=Field(default='自定义',max_length=80)
    fields:list[CustomField]=Field(default_factory=list,max_length=100)
    description:str=Field(default='',max_length=3000)
    version:int=Field(default=1,ge=1,le=100000)
    modules:list[str]=Field(default_factory=list,max_length=12)
class Period(Strict):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    label:str=Field(min_length=1,max_length=100)
    story_start:str=''
    story_end:str=''
    description:str=''
    appearance:str=''
    calendar:str=Field(default='iso',max_length=80)
    confirmed:bool=False
    facts:dict[str,str|float|bool|None]=Field(default_factory=dict,max_length=40)
    writer_view:str=Field(default='',max_length=6000)
    source_references:list[dict[str,str]]=Field(default_factory=list,max_length=10)
class Entity(Strict):
    id:str=Field(default='',pattern=r'^(?:entity_[0-9a-f]{32})?$')
    name:str=Field(min_length=1,max_length=200)
    aliases:list[str]=Field(default_factory=list)
    category:str=Field(min_length=1,max_length=64)
    summary:str=Field(default='',max_length=4000)
    details:str=Field(default='',max_length=100000)
    tags:list[str]=Field(default_factory=list)
    first_appearance:str=''
    source:Literal['USER','AI_PROPOSED','RESEARCH','SOURCE_CANON','PROJECT_CANON']='USER'
    canon_level:Literal['HARD','STRONG','SOFT','PREFERENCE','REFERENCE']='REFERENCE'
    status:Literal['DRAFT','PENDING','FORMAL','LOCKED','DEPRECATED']='DRAFT'
    locked_fields:list[str]=Field(default_factory=list)
    valid_from:str=''
    valid_to:str=''
    periods:list[Period]=Field(default_factory=list)
    fields:dict[str,Any]=Field(default_factory=dict)
    template_version:int=Field(default=0,ge=0)
    template_snapshot:Category|None=None
    parent_id:str=Field(default='',max_length=80)
    writer_view:str=Field(default='',max_length=6000)
    writer_public:bool=False
    writer_known_by:list[str]=Field(default_factory=list,max_length=30)
    source_references:list[dict[str,str]]=Field(default_factory=list,max_length=30)
    favorite:bool=False
    version:int=0
    created_at:str=''
    updated_at:str=''

GROUPS={
 '基础世界':[('overview','世界概览'),('era','时代背景'),('nature','宇宙与自然规则'),('history','历史与纪年'),('geography','地理与气候')],
 '社会文明':[(x,y) for x,y in zip(['country','race','culture','religion','language','education','law','economy','class'],['国家','民族与种族','文化','宗教','语言','教育','法律','经济','社会阶层'])],
 '势力组织':[(x,y) for x,y in zip(['government','army','company','sect','family','secret-faction','faction'],['国家政权','军事组织','公司','宗门','家族','秘密组织','其他势力'])],
 '地点':[(x,y) for x,y in zip(['continent','region','city','town','building','location'],['大陆','国家区域','城市','村镇','建筑','特殊地点'])],
 '体系':[(x,y) for x,y in zip(['magic','cultivation','superpower','technology','industry','military','profession','levels'],['魔法','修炼','超能力','科技','工业','军事','职业','等级规则'])],
 '特殊实体':[(x,y) for x,y in zip(['item','weapon','equipment','resource','fauna','flora','creature'],['道具','武器','装备','资源','动物','植物','特殊生物'])],
 '故事资料':[(x,y) for x,y in zip(['event','timeline','clue','secret','term','plotline'],['重要事件','时间线','伏笔','秘密','术语','剧情线'])]}

def fields(spec):
    return [{'id':i,'name':n,'type':t,'options':[]} for i,n,t in spec]
FACTION=fields([('formal_name','正式名称','text'),('short_name','简称','text'),('established','建立时间','text'),('territory','领土 / 控制区域','longtext'),('population','人口','text'),('headquarters','首都 / 总部','entity'),('leadership','领导层 / 权力结构','longtext'),('law','制度与法律','longtext'),('finance','财政 / 货币','longtext'),('industry','主要产业','longtext'),('military','军事力量','longtext'),('diplomacy','外交关系','longtext'),('society','社会结构与文化','longtext'),('history','历史与下属组织','longtext')])
LOCATION=fields([('parent','上级区域','entity'),('position','地理位置','longtext'),('climate','气候','text'),('population','人口','text'),('environment','环境与建筑','longtext'),('economy','经济活动','longtext'),('authority','管辖势力','entity'),('events','主要人物与发生事件','longtext'),('map','地图','image')])
SYSTEM=fields([('principle','原理','longtext'),('acquisition','获得方式','longtext'),('levels','可选等级','text'),('conditions','使用条件','longtext'),('cost','消耗','text'),('limits','限制与副作用','longtext'),('counter','克制关系','longtext'),('users','已知使用者','longtext'),('history','历史变化','longtext')])

def defaults():
    result=[]
    for group,entries in GROUPS.items():
        for id,name in entries:
            fs=copy.deepcopy(FACTION if group=='势力组织' or id=='country' else LOCATION if group=='地点' else SYSTEM if group=='体系' else [])
            if id=='company':fs+=fields([('equity','股权','longtext'),('business','业务','longtext'),('management','管理层','longtext')])
            if id=='sect':fs+=fields([('lineage','传承','longtext'),('ranks','等级','longtext'),('disciples','弟子结构','longtext')])
            result.append({'id':id,'name':name,'group':group,'fields':fs})
    from .world_templates import enrich
    from .world_rules import template
    result=enrich(result)
    for c in result:
        if c['id'] in {'country','city','company','magic','technology','resource'}:
            c['fields'].append({'id':'applicable_rules','name':'关联世界规则卡','type':'entities','options':[],'target_types':['entity'],'group':'规则与依据','primary':False,'help':'仅建立引用；不自动将关联解释为因果，也不自动发送给 Writer。'})
    return [*result,template()]

class Bible:
    def __init__(self,registry):self.registry=registry
    def root(self,project):return self.registry.workspace(project).root
    def categories(self,project):
        custom=read(safe(self.root(project),'bible/categories.json'),{})
        rows={r['id']:r for r in defaults()};rows.update(custom)
        return [Category.model_validate(v).model_dump() for v in rows.values()]
    def category(self,project,value):
        row=Category.model_validate(value).model_dump()
        from .world_templates import check_template
        check_template(row)
        if len({f['id'] for f in row['fields']})!=len(row['fields']):raise ConsoleError('字段 ID 重复',422)
        existing=next((r for r in self.categories(project) if r['id']==row['id']),None)
        if existing:
            if row['version']!=existing.get('version',1):raise ConsoleError('模板版本已变化，请保留本次修改并重新比较',409)
            from .world_templates import compatible
            if not compatible(existing,row):raise ConsoleError('模板升级必须保留已有字段、类型和选项；请用新 ID 建立不兼容版本',409)
            for old in existing['fields']:
                replacement=next((f for f in row['fields'] if f['id']==old['id']),None)
                if replacement is None or replacement['type']!=old['type'] or not set(old['options']).issubset(replacement['options']):
                    raise ConsoleError('已有字段不能删除、改类型或移除选项；请添加新字段',409)
        row['version']=(existing.get('version',1)+1) if existing else 1
        if existing:
            history=safe(self.root(project),f"bible/template-versions/{row['id']}/{existing.get('version',1)}.json")
            if not history.exists():write(history,existing)
        p=safe(self.root(project),'bible/categories.json');custom=read(p,{});custom[row['id']]=row;write(p,custom)
        write(safe(self.root(project),f"bible/template-versions/{row['id']}/{row['version']}.json"),row)
        return row
    def list(self,project):
        root=self.root(project)
        # Resolve the project once per bounded read, not again for every entity.
        return [self._get_at(root,p.stem) for p in safe(root,'bible/entities').glob('entity_*.json')]
    def get(self,project,id):
        return self._get_at(self.root(project),id)
    def _get_at(self,root,id):
        if not re.fullmatch(r'entity_[0-9a-f]{32}',id):raise ConsoleError('无效实体 ID',403)
        p=safe(root,'bible/entities/'+id+'.json');row=read(p)
        if not row:raise ConsoleError('设定不存在',404)
        return {**row,'etag':digest(p.read_bytes())}
    def targets(self,project,*,entities=None):
        ws=self.registry.workspace(project);rows=[{'id':r['id'],'type':'entity','name':r['name'],'category':r['category']} for r in (self.list(project) if entities is None else entities)]
        for p in safe(ws.root,'characters').glob('*.yaml'):
            v=ws.yaml_file('characters/'+p.name);rows.append({'id':v['id'],'type':'character','name':v.get('name') or v['id']})
        from app.domain.planning import Planning
        from app.domain.characters import CharacterService
        from app.domain.proposals import Proposals
        plan=Planning(self.registry,CharacterService(self.registry),Proposals(self.registry))
        for c in plan.rows(project,'chapter'):rows.append({'id':c['id'],'type':'chapter','name':f"第 {c['number']} 章 · {c['title']}"})
        from app.projects.writing_config import story_row
        story=story_row(ws,self.registry.get(project))
        if story:rows.append({'id':story['id'],'type':'chapter','name':story['title']})
        planned={c['number'] for c in plan.rows(project,'chapter')}
        manual=read(safe(ws.root,'metadata/manual-chapters.json'),{})
        for chapter in ws.chapters():
            if chapter['number'] not in planned:
                n=chapter['number'];rows.append({'id':'manual_'+digest(('chapter-'+str(n)).encode())[:24],'type':'chapter','name':manual.get(str(n),{}).get('title') or f'第 {n} 章'})
        return rows
    def check_target(self,project,type,id):
        if not any(r['id']==id and r['type']==type for r in self.targets(project)):raise ConsoleError('关联对象不属于当前小说或已移除',422)
    def save(self,project,value,etag=None,approve=False,*,new_id=None):
        row=Entity.model_validate(value).model_dump();root=self.root(project)
        category=next((c for c in self.categories(project) if c['id']==row['category']),None)
        if not category:raise ConsoleError('分类不存在',422)
        previous=self.get(project,row['id']) if row['id'] else None
        if previous:
            if previous['etag']!=etag:raise ConsoleError('设定已变化，请重新读取',409)
            if previous['status']=='LOCKED' and row!= {k:v for k,v in previous.items() if k!='etag'}:raise ConsoleError('已锁定设定不能覆盖；请通过明确解锁操作',409)
            for f in previous['locked_fields']:
                a,b=(row['fields'].get(f[7:]),previous['fields'].get(f[7:])) if f.startswith('fields.') else (row.get(f),previous.get(f))
                if a!=b:raise ConsoleError('锁定字段不可覆盖：'+f,409)
            if not set(previous['locked_fields']).issubset(row['locked_fields']):raise ConsoleError('删除锁定字段需使用明确解锁操作',409)
        if (row['source']=='AI_PROPOSED' or previous and previous['source']=='AI_PROPOSED') and row['status'] in {'FORMAL','LOCKED'} and not approve:
            raise ConsoleError('AI 设定需明确接受 Proposal 才可正式采用',409)
        if row['source']=='AI_PROPOSED' and row['status']=='DRAFT':row['status']='PENDING'
        if row['canon_level']=='HARD' and row['status'] not in {'FORMAL','LOCKED'}:raise ConsoleError('待审核资料不能成为 HARD Canon',409)
        if row['source']=='RESEARCH' and row['canon_level']=='HARD':raise ConsoleError('研究资料不是 HARD Canon；请由作者明确采用为本书设定',409)
        from .world_templates import validate_values
        snapshot=previous.get('template_snapshot') if previous else None
        if snapshot and row.get('template_snapshot')!=snapshot and not approve:raise ConsoleError('升级实体模板必须明确确认，已有字段会保留',409)
        if snapshot and row.get('template_snapshot')==snapshot:category=snapshot
        elif row.get('template_snapshot') and row['template_snapshot']!=category:raise ConsoleError('模板快照必须与当前保存的模板一致',409)
        row['template_snapshot']=category;row['template_version']=category.get('version',1)
        validate_values(category,row['fields'],formal=row['status'] in {'FORMAL','LOCKED'})
        from .world_rules import is_rule,card,fragment
        if is_rule(row):
            rules=card(row)
            if rules['formal_model']:fragment(rules['formal_model'])
            if row['status'] in {'FORMAL','LOCKED'} and rules['rule_strength']=='HARD' and not approve:raise ConsoleError('正式硬规则需要作者明确确认',409)
        if any(p.get('confirmed') or p.get('writer_view') for p in row['periods']) and (not previous or row['periods']!=previous.get('periods',[])) and not approve:raise ConsoleError('确认历史时期或发布时期摘要需要作者明确确认',409)
        valid={f['id']:f for f in category['fields']}
        targets=None
        def check_references(fields,values):
            nonlocal targets
            for f in fields:
                v=values.get(f['id'])
                if v in (None,'',[]):continue
                if f['type']=='group':check_references(f.get('children',[]),v)
                if f['type'] in {'entity','entities'}:
                    if targets is None:targets=self.targets(project)
                    for id in v if f['type']=='entities' else [v]:
                        if not any(t['id']==id and (not f.get('target_types') or t['type'] in f['target_types']) for t in targets):raise ConsoleError('关联字段目标不属于当前作品或类型不符：'+f['name'],422)
                if f['type']=='image' and (not re.fullmatch(r'asset_[0-9a-f]{32}',v) or not safe(root,'assets/metadata/'+v+'.json').is_file()):raise ConsoleError('图片引用无效',422)
                if f['type']=='evidence':
                    path=v['path'];source=safe(root,path)
                    if not path.startswith('chapters/') or not source.is_file() or digest(source.read_bytes())!=v['revision'] or not v['quote'] or v['quote'] not in source.read_text('utf-8-sig'):raise ConsoleError('原文证据无法在当前版本定位',409)
        check_references(category['fields'],row['fields'])
        if previous:
            for f in valid.values():
                if f.get('locked') and previous['fields'].get(f['id'])!=row['fields'].get(f['id']):raise ConsoleError('模板锁定的字段不可覆盖：'+f['name'],409)
            if any(previous.get(k,False if k=='writer_public' else [] if k=='writer_known_by' else '')!=row.get(k) for k in ['writer_view','writer_public','writer_known_by']) and not approve:raise ConsoleError('修改 Writer 可见摘要需要作者明确确认',409)
        elif row['writer_view'] and not approve:raise ConsoleError('发布 Writer 可见摘要需要作者明确确认',409)
        if row['writer_known_by']:
            allowed={t['id'] for t in self.targets(project) if t['type']=='character'}
            if set(row['writer_known_by'])-allowed:raise ConsoleError('Writer 可见人物不属于当前作品',422)
        if row['parent_id']:
            self.check_target(project,'entity',row['parent_id'])
            seen={row['id']};cursor=row['parent_id']
            while cursor:
                if cursor in seen:raise ConsoleError('百科父级不能形成循环',422)
                seen.add(cursor);cursor=self.get(project,cursor).get('parent_id','')
        if set(row['fields'])-set(valid):raise ConsoleError('包含尚未定义的自定义字段',422)
        for key,value in row['fields'].items():
            if value in (None,'',[]):continue
            f=valid[key];t=f['type'];ok=True
            if t in {'text','longtext','date','select','image','entity','calendar','rule'}:ok=isinstance(value,str)
            if t=='number':ok=isinstance(value,(int,float)) and not isinstance(value,bool)
            if t=='boolean':ok=isinstance(value,bool)
            if t in {'tags','multiselect'}:ok=isinstance(value,list) and all(isinstance(x,str) for x in value)
            if t=='select':ok=ok and value in f['options']
            if t=='multiselect':ok=ok and all(x in f['options'] for x in value)
            if t=='date':
                from datetime import date
                try:date.fromisoformat(value)
                except (ValueError,TypeError):ok=False
            if t=='entity':ok=ok and any(r['id']==value for r in self.targets(project))
            if t=='image':ok=ok and bool(re.fullmatch(r'asset_[0-9a-f]{32}',value)) and safe(root,'assets/metadata/'+value+'.json').is_file()
            if t=='entities':ok=isinstance(value,list) and all(any(r['id']==v and (not f.get('target_types') or r['type'] in f['target_types']) for r in self.targets(project)) for v in value)
            if t=='entity' and f.get('target_types'):ok=ok and any(r['id']==value and r['type'] in f['target_types'] for r in self.targets(project))
            if not ok:raise ConsoleError('字段不符合类型或关联无效：'+f['name'],422)
        if any((f[7:] not in valid if f.startswith('fields.') else f not in row or f in {'id','version','created_at','updated_at','status','locked_fields'}) for f in row['locked_fields']):raise ConsoleError('无效锁定字段',422)
        if new_id and (not re.fullmatch(r'entity_[0-9a-f]{32}',new_id) or safe(root,'bible/entities/'+new_id+'.json').exists()):raise ConsoleError('稳定实体标识已被占用',409)
        row.update(id=row['id'] or new_id or uid('entity'),created_at=previous['created_at'] if previous else now(),updated_at=now(),version=(previous['version'] if previous else 0)+1)
        write(safe(root,'bible/entities/'+row['id']+'.json'),row)
        return self.get(project,row['id'])
    def explicit_relations(self,project):return read(safe(self.root(project),'bible/relations.json'),{'relations':[]})['relations']
    def relations(self,project,*,entities=None):
        rows=self.explicit_relations(project);entities=self.list(project) if entities is None else entities
        if not any(e.get('fields') for e in entities):return rows
        categories={c['id']:c for c in self.categories(project)};targets={t['id']:t for t in self.targets(project,entities=entities)}
        for e in entities:
            def links(fields,values,prefix=''):
                for f in fields:
                    value=values.get(f['id']);key=prefix+f['id']
                    if f['type']=='group' and isinstance(value,dict):yield from links(f.get('children',[]),value,key+'.')
                    for target in value if f['type']=='entities' and isinstance(value,list) else [value] if f['type']=='entity' else []:
                        if target in targets:yield key,f['name'],target
            selected=e.get('template_snapshot') or categories.get(e['category'],{})
            for key,name,target in links(selected.get('fields',[]),e['fields']):
                rows.append({'id':'field:'+e['id']+':'+key+':'+target,'source_type':'entity','source_id':e['id'],'target_type':targets[target]['type'],'target_id':target,'relation_type':name,'description':'来自已保存的专属字段','derived':True})
            if e.get('parent_id') in targets:
                rows.append({'id':'field:'+e['id']+':parent','source_type':'entity','source_id':e['id'],'target_type':'entity','target_id':e['parent_id'],'relation_type':'隶属条目','description':'来自已保存的百科父级','derived':True})
        return rows
    def link(self,project,value):
        row={k:str(value.get(k,'')) for k in ['source_type','source_id','target_type','target_id','relation_type','description']}
        for prefix in ['source','target']:self.check_target(project,row[prefix+'_type'],row[prefix+'_id'])
        if not row['relation_type'].strip():raise ConsoleError('请填写关系类型',422)
        rows=self.explicit_relations(project)
        row['id']=uid('relation');rows.append(row)
        write(safe(self.root(project),'bible/relations.json'),{'relations':rows});return row
    def copy(self,source,id,target):
        if source==target:raise ConsoleError('请选另一部小说',422)
        row=self.get(source,id);old=row['id'];category=next(c for c in self.categories(source) if c['id']==row['category'])
        existing=next((c for c in self.categories(target) if c['id']==category['id']),None)
        if existing and existing!=category:category['id']='copy-'+uid('type')[-12:]
        self.category(target,category);row.update(id='',category=category['id'],status='DRAFT',canon_level='REFERENCE',locked_fields=[],template_snapshot=None,template_version=0,parent_id='',writer_view='',writer_public=False,writer_known_by=[],source_references=[])
        for period in row.get('periods',[]):period.update(confirmed=False,writer_view='',source_references=[])
        row.pop('etag');dropped=[]
        for f in category['fields']:
            if f['type'] in {'entity','image'} and row['fields'].get(f['id']):dropped.append(f['id']);row['fields'].pop(f['id'])
        saved=self.save(target,row)
        return {'entity':saved,'id_map':{old:saved['id']},'unmapped_fields':dropped,'note':'仅复制选定实体；未选定的外部关系和图片引用已清空，不共享文件。'}
