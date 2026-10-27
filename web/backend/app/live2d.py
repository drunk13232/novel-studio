"""Private Live2D data adapter and card-only reuse of existing Roleplay.
No model code, shell, Canon or filesystem tool is exposed to a character.
"""
import copy,hashlib,io,json,math,os,re,shutil,stat,threading,uuid,zipfile
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
from fastapi import APIRouter,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from app.errors import ConsoleError
from app.library.storage import safe,read,write
from app.companion import safe_local
from app.roleplay.service import Roleplay
from app.roleplay.context import view
from app.roleplay.models import Create,Persona,Actor,Scene,Reply,Memory,Lore,SessionEdit
from app.projects.service import NovelWorkspace

RUNTIME_SHA='7e2da1360a2d58515343f2dfe5b42dd772588c3a96580b5bbf2f90eeb4496d1e'
CHARACTERS={'yoshino':{'name':'朝武芳乃','description':'《千恋＊万花》的朝武芳乃，神社的巫女姬。个人陪伴对话，不把原作或对话写入小说。','personality':'认真、端正，有责任感；外表克制，亲近后能表达情绪和偶尔的笨拙。温柔而不盲从，遇到含混信息会询问。用自然中文交流，简短、有个人感，不反复复述自己是助手。不复制原作台词。'},
'rem':{'name':'蕾姆','description':'《Re:从零开始的异世界生活》的蕾姆，蓝发女仆。个人陪伴对话，不是原配音演员的声音。','personality':'细心、勤勉，待人温和而有自己的判断。熟悉后亲近，但不把所有请求一概赞同。安静陪伴，能提出不同意见，不擅自假设用户关系。用自然中文交流，不复制原作台词。'},
'haru':{'name':'Haru（官方技术示例）','description':'Live2D 官方 Haru 示例，用于动画、对话和口型技术验收；不是芳乃或蕾姆。','personality':'以自然中文进行简短、友好的技术演示对话。不要冒充其他角色。'}}
EMOTIONS=('neutral','happy','confused','surprised','displeased','shy','thinking')
INTENTS=('greet','tap','agree','think')
BEHAVIORS=(*INTENTS,'nod','shake','look','rest','read','search','execute','confirm','present','error')
PRESENTATION={'pet_x','pet_y','pet_passthrough','autonomous','quiet','duet','partner_x','partner_y'}
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Profile(Strict):
    model_id:str=Field(default='',pattern=r'^[a-zA-Z0-9_-]{0,80}$')
    ai_model:str=Field(default='',max_length=250)
    voice:str=Field(default='',max_length=500)
    voice_enabled:bool=False
    volume:int=Field(default=65,ge=0,le=100)
    rate:int=Field(default=0,ge=-10,le=10)
    expressions:dict[str,str]=Field(default_factory=dict,max_length=7)
    motions:dict[str,dict]=Field(default_factory=dict,max_length=4)
class CompanionSettings(Strict):
    character:Literal['yoshino','rem','haru']='yoshino'
    size:int=Field(default=220,ge=150,le=460)
    scale:float=Field(default=1,ge=.5,le=1.5)
    offset_x:float=Field(default=0,ge=-.8,le=.8)
    offset_y:float=Field(default=0,ge=-.8,le=.8)
    animation:bool=True
    # Normalized position inside the app, independent of window size or DPI.
    pet_x:float=Field(default=1,ge=0,le=1)
    pet_y:float=Field(default=1,ge=0,le=1)
    pet_passthrough:bool=False
    autonomous:bool=True
    quiet:bool=False
    duet:bool=False
    partner_x:float=Field(default=0,ge=0,le=1)
    partner_y:float=Field(default=1,ge=0,le=1)
    profiles:dict[str,Profile]=Field(default_factory=lambda:{k:Profile() for k in CHARACTERS},max_length=3)
class DialogueBody(Strict):
    project:str|None=None
    text:str=Field(default='',max_length=6000)
    model:str|None=Field(default=None,max_length=250)
    etag:str=Field(default='',max_length=64)
class Remember(DialogueBody):
    source_node_ids:list[str]=Field(default_factory=list,max_length=12)
    confirm:Literal[True]
class LoreBody(Strict):
    project:str|None=None
    etag:str=Field(min_length=64,max_length=64)
    entries:list[Lore]=Field(default_factory=list,max_length=60)
class ImportInfo(Strict):
    character:Literal['yoshino','rem','haru']
    name:str=Field(min_length=1,max_length=100)
    license_note:str=Field(min_length=1,max_length=2000)
    confirm_rights:Literal[True]

def data_file(base,name):
    # No URLs, absolute paths, parent traversal, control characters or NTFS ADS.
    if not isinstance(name,str) or len(name)>240 or any(ord(x)<32 for x in name) or any(x in name for x in ('\\',':','?','#','%')):raise ConsoleError('模型引用必须是包内相对文件名',422)
    rel=PurePosixPath(name)
    if rel.is_absolute() or any(p in {'','..','.'} for p in name.split('/')):raise ConsoleError('模型引用越出资源包',422)
    target=base/rel
    if not safe_local(target,base):raise ConsoleError('模型文件缺失、链接或路径无效',422)
    return target

def decode(path,limit=2*1024*1024):
    if path.stat().st_size>limit:raise ConsoleError('模型 JSON 超过资源限制',413)
    try:
        value=json.loads(path.read_text('utf-8-sig'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError()))
        def finite(v,depth=0):
            if depth>80:raise ValueError()
            if isinstance(v,float) and not math.isfinite(v):raise ValueError()
            if isinstance(v,dict):
                for x in v.values():finite(x,depth+1)
            elif isinstance(v,list):
                for x in v:finite(x,depth+1)
        finite(value);return value
    except (ValueError,UnicodeError):raise ConsoleError('模型 JSON 无效',422) from None

class ModelResources:
    def __init__(self,root):self.root=root
    def runtime(self,name='l2d.js'):
        allowed={'l2d.js':RUNTIME_SHA,'cubism2.js':'612ac06fc888c193ffe432831ffb3831729967b20cc944b3dc6dc96328bbd2ad'}
        if name not in allowed:raise ConsoleError('运行时文件不在白名单',404)
        path=self.root/'runtime'/name
        if not safe_local(path,self.root) or path.stat().st_size>2*1024*1024 or hashlib.sha256(path.read_bytes()).hexdigest()!=allowed[name]:raise ConsoleError('尚未安装经过核实的 l2d 2.1.1 私人运行时',503)
        return path
    def model(self,id):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',id):raise ConsoleError('模型 ID 无效',422)
        base=self.root/'models'/id;meta=decode(data_file(base,'slot.json'),4096)
        if not isinstance(meta,dict):raise ConsoleError('模型槽位数据无效',422)
        document=data_file(base,meta.get('model',''));body=decode(document)
        if not isinstance(body,dict):raise ConsoleError('模型定义必须是对象',422)
        refs=body.get('FileReferences',{})
        if body.get('Version')!=3 or not isinstance(refs,dict) or set(refs)-{'Moc','Textures','Physics','Pose','DisplayInfo','Expressions','Motions','UserData'}:raise ConsoleError('仅支持受控 Cubism model3 运行包',422)
        names=[meta['model']];moc=data_file(base,refs.get('Moc',''))
        with moc.open('rb') as handle:magic=handle.read(4)
        if moc.suffix!='.moc3' or moc.stat().st_size>20*1024*1024 or magic!=b'MOC3':raise ConsoleError('缺少真正的 moc3 模型数据',422)
        names.append(refs['Moc']);textures=refs.get('Textures',[])
        if not isinstance(textures,list) or not 1<=len(textures)<=8:raise ConsoleError('模型贴图数量无效',422)
        from PIL import Image
        total_pixels=0
        for name in textures:
            path=data_file(base,name)
            if path.suffix.lower() not in {'.png','.webp','.jpg','.jpeg'} or path.stat().st_size>20*1024*1024:raise ConsoleError('模型贴图格式或大小无效',422)
            with Image.open(path) as im:
                total_pixels+=im.width*im.height
                if total_pixels>16_777_216:raise ConsoleError('模型贴图过大',413)
                im.verify()
            names.append(name)
        for key in ['Physics','Pose','DisplayInfo','UserData']:
            if refs.get(key):decode(data_file(base,refs[key]));names.append(refs[key])
        expressions=refs.get('Expressions',[]);motions=refs.get('Motions',{})
        if not isinstance(expressions,list) or len(expressions)>60 or not isinstance(motions,dict) or len(motions)>30:raise ConsoleError('动作或表情数量过多',413)
        for item in expressions:
            if not isinstance(item,dict) or not isinstance(item.get('Name'),str):raise ConsoleError('表情定义无效',422)
            if not str(item.get('File','')).endswith('.exp3.json'):raise ConsoleError('表情必须是 exp3 数据',422)
            decode(data_file(base,item['File']));names.append(item['File'])
        count=0
        for group,items in motions.items():
            if not isinstance(group,str) or not isinstance(items,list):raise ConsoleError('动作组无效',422)
            for item in items:
                count+=1
                if count>128 or not isinstance(item,dict) or not str(item.get('File','')).endswith('.motion3.json'):raise ConsoleError('动作资源无效或过多',422)
                decode(data_file(base,item['File']));names.append(item['File'])
                # Motion recordings never play; personal TTS is separately selected.
                item.pop('Sound',None)
        display_aspect=meta.get('display_aspect',1.0)
        if isinstance(display_aspect,bool) or not isinstance(display_aspect,(int,float)) or not math.isfinite(display_aspect) or not .5<=display_aspect<=2.2:raise ConsoleError('模型显示比例无效',422)
        canvas_aspect=meta.get('canvas_aspect')
        if canvas_aspect is not None and (isinstance(canvas_aspect,bool) or not isinstance(canvas_aspect,(int,float)) or not math.isfinite(canvas_aspect) or not .1<=canvas_aspect<=10):raise ConsoleError('模型画布比例无效',422)
        if meta.get('character') not in CHARACTERS:raise ConsoleError('模型角色归属未设置',422)
        result={'id':id,'name':str(meta.get('name',id))[:100],'character':meta['character'],'sample':meta.get('sample') is True,'display_aspect':float(display_aspect),'canvas_aspect':canvas_aspect,'model':meta['model'],
                'expressions':[x['Name'] for x in expressions],'motions':{g:len(v) for g,v in motions.items()},
                'mouth_ids':[i for g in body.get('Groups',[]) if g.get('Name')=='LipSync' for i in g.get('Ids',[])],
                'license_note':str(meta.get('license_note','未说明使用权限'))[:2000],'files':list(dict.fromkeys(names)), 'definition':body}
        behaviors=meta.get('behaviors',{})
        if not isinstance(behaviors,dict) or set(behaviors)-set(BEHAVIORS):raise ConsoleError('行为映射不在白名单',422)
        for intent,value in behaviors.items():
            if not isinstance(value,dict) or set(value)!={'group','index'} or value['group'] not in motions or type(value['index']) is not int or not 0<=value['index']<len(motions[value['group']]):raise ConsoleError('行为必须绑定已有动作',422)
        result['behaviors']=behaviors
        result['hit_areas']=[h['Name'] for h in body.get('HitAreas',[]) if isinstance(h,dict) and isinstance(h.get('Name'),str)]
        result['physics_available']=bool(refs.get('Physics'))
        return result
    def catalog(self):
        rows=[];errors=[]
        for folder in sorted((self.root/'models').glob('*')):
            if not folder.is_dir():continue
            try:
                model=self.model(folder.name);rows.append({k:v for k,v in model.items() if k not in {'files','definition'}})
            except (ConsoleError,OSError,ValueError) as e:errors.append({'id':folder.name,'error':str(e)[:300]})
        try:self.runtime();self.runtime('cubism2.js');available=True
        except ConsoleError:available=False
        return {'runtime_available':available,'runtime':'l2d 2.1.1 (private Cubism Core)','models':rows,'errors':errors,'characters':{k:{'name':v['name'],'model_available':any(m['character']==k for m in rows)} for k,v in CHARACTERS.items()}}
    def import_zip(self,payload,info):
        if len(payload)>60*1024*1024:raise ConsoleError('运行包超过 60 MiB',413)
        id='model_'+uuid.uuid4().hex;folder=self.root/'models'/id
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as z:
                items=z.infolist()
                if len({x.filename.casefold() for x in items})!=len(items):raise ConsoleError('模型包含重名资源',422)
                if len(items)>512 or sum(x.file_size for x in items)>128*1024*1024:raise ConsoleError('解压资源超过限制',413)
                for item in items:
                    name=item.filename
                    if item.is_dir():continue
                    rel=PurePosixPath(name)
                    if not name or any(ord(x)<32 for x in name) or rel.is_absolute() or any(x in {'..','.'} for x in rel.parts) or any(x in name for x in ('\\',':','%')) or stat.S_ISLNK(item.external_attr>>16):raise ConsoleError('运行包含不安全路径或链接',422)
                    if rel.suffix.lower() not in {'.json','.moc3','.png','.webp','.jpg','.jpeg','.txt','.md'} or item.file_size>20*1024*1024:raise ConsoleError('仅接受模型数据、图片及许可说明；不导入代码、声音或编辑工程',422)
                candidates=[x.filename for x in items if x.filename.endswith('.model3.json')]
                if len(candidates)!=1:raise ConsoleError('请导入只包含一个 model3 的完整运行包',422)
                prefix=str(PurePosixPath(candidates[0]).parent);prefix='' if prefix=='.' else prefix+'/'
                folder.mkdir(parents=True)
                for item in items:
                    if item.is_dir() or not item.filename.startswith(prefix):continue
                    rel=item.filename[len(prefix):]
                    if not rel or rel=='slot.json':continue
                    target=folder/rel
                    if not target.resolve().is_relative_to(folder.resolve()):raise ConsoleError('模型路径无效',422)
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
                meta={'schema_version':1,'name':info.name,'character':info.character,'model':candidates[0][len(prefix):],'sample':False,'license_note':info.license_note}
                # Keep only bounded display metadata from a private exported bundle.
                # Identity, name and rights still come from the author's import form.
                slot_name=prefix+'slot.json'
                if slot_name in z.namelist():
                    if z.getinfo(slot_name).file_size>4096:raise ConsoleError('模型槽位数据过大',413)
                    imported_meta=json.loads(z.read(slot_name).decode('utf-8-sig'))
                    if isinstance(imported_meta,dict):
                        for field in ['canvas_aspect','behaviors']:
                            if field in imported_meta:meta[field]=imported_meta[field]
                write(folder/'slot.json',meta);result=self.model(id);return {k:v for k,v in result.items() if k not in {'definition','files'}}
        except Exception:
            # Only this freshly-created, contained import is removed on failure.
            if folder.is_dir() and not folder.is_symlink() and folder.resolve().is_relative_to((self.root/'models').resolve()):shutil.rmtree(folder)
            raise

class PrivateRegistry:
    def __init__(self,home,real):self.home=home;self.engine=real.engine;self.real=real;self.cache={}
    def get(self,p):
        if not re.fullmatch(r'companion-(yoshino|rem|haru|duet)(?:-novel_[a-f0-9]{32})?',p):raise ConsoleError('陪伴会话作用域无效',403)
        if '-novel_' in p:self.real.get('novel_'+p.split('-novel_')[1])
        return {'id':p,'title':'私人角色对话','language':'zh-CN'}
    def workspace(self,p):
        self.get(p)
        if p not in self.cache:
            path=safe(self.home,'dialogues/'+p);path.mkdir(parents=True,exist_ok=True);self.cache[p]=NovelWorkspace(path)
        return self.cache[p]
class CardDialogue(Roleplay):
    def hidden_terms(self,p):return [] # It never reads any novel source or Canon.
    def frame(self,p,row,branch,aid):
        self.registry.get(p)
        result=view(row,aid,self.nodes(p,row,branch),branch['scene'],branch['lore'],row['memories'])
        if hasattr(self,'performance'):
            actor=next(x for x in row['actors'] if x['id']==aid)
            result['performance_capabilities']=self.performance(actor['name'])
            result['performance_rules']='仅选择实际绑定的情绪与动作；不要把叙述当成已执行动作。没有挥手等动作时坦率说明。软件操作只有用户点击现有操作卡并收到回执后才成立。'
        return result

class LiveCompanion:
    def __init__(self,home,app):
        self.home=home;self.app=app;self.resources=ModelResources(home/'live2d');self.lock=threading.RLock()
        registry=PrivateRegistry(home,app.state.registry)
        tools=SimpleNamespace(writable=lambda p:registry.get(p))
        world=SimpleNamespace(source=lambda *_:(_ for _ in ()).throw(ConsoleError('陪伴世界书不能隐式读取 Canon；请明确提供选取的资料',403)))
        self.dialogue=CardDialogue(registry,SimpleNamespace(list=lambda p:[]),SimpleNamespace(tools=tools),lambda p:app.state.manager,app.state.ai_center,world)
        self.dialogue.performance=self.performance
    def performance(self,name):
        char=next((k for k,v in CHARACTERS.items() if v['name']==name),None)
        profile=self.settings().profiles.get(char,Profile())
        return {'emotions':[k for k,v in profile.expressions.items() if v],'motion_intents':list(profile.motions),'voice':'用户选择的合成音色；不是原配音演员','missing':'未列入已绑定 motion_intents 的能力不可声称已执行；文字中的动作叙述不等于模型执行'}
    def scope(self,char,project=None):
        if char not in {*CHARACTERS,'duet'}:raise ConsoleError('未知陪伴角色',422)
        if project:self.app.state.registry.get(project)
        return 'companion-'+char+('-'+project if project else '')
    def settings(self):
        # Keep the original model/session configuration readable by older releases.
        with self.lock:
            values=read(self.home/'companion-settings.json',{})
            presentation=read(self.home/'companion-presentation.json',{})
        values.update({k:v for k,v in presentation.items() if k in PRESENTATION})
        return CompanionSettings.model_validate(values)
    def save_settings(self,b):
        if set(b.profiles)-set(CHARACTERS):raise ConsoleError('未知角色配置',422)
        for key,p in b.profiles.items():
            if set(p.expressions)-set(EMOTIONS) or set(p.motions)-set(INTENTS):raise ConsoleError('动作／情绪映射不在白名单',422)
            if p.model_id:
                m=self.resources.model(p.model_id)
                if m['character']!=key:raise ConsoleError('模型归属与角色不符；Haru 示例不能绑定成芳乃或蕾姆',422)
                if any(v and v not in m['expressions'] for v in p.expressions.values()):raise ConsoleError('映射表情不属于当前模型',422)
                for value in p.motions.values():
                    if set(value)!={'group','index'} or value['group'] not in m['motions'] or type(value['index']) is not int or not 0<=value['index']<m['motions'][value['group']]:raise ConsoleError('映射动作不属于当前模型',422)
        with self.lock:
            fields=PRESENTATION
            write(self.home/'companion-settings.json',b.model_dump(exclude=fields))
            write(self.home/'companion-presentation.json',b.model_dump(include=fields))
        return b.model_dump()
    def session(self,char,project=None,create=False):
        scope=self.scope(char,project);registry=self.dialogue.registry;path=registry.workspace(scope).root/'companion-index.json';index=read(path,{})
        if not index and create:
            chars=['yoshino','rem'] if char=='duet' else [char]
            profiles=self.settings().profiles
            cards=[self.dialogue.import_card(scope,json.dumps(CHARACTERS[k],ensure_ascii=False)) for k in chars]
            result=self.dialogue.create(scope,Create(title='芳乃与蕾姆的共同场景' if char=='duet' else CHARACTERS[char]['name']+'的私人会话',persona=Persona(name='作者'),actors=[Actor(source_type='card',source_id=card['id'],model=profiles.get(k,Profile()).ai_model or None) for k,card in zip(chars,cards)],scene=Scene(background='安静陪伴作者。只使用作者在这个场景提供的内容、自己可见记忆与听到的对话。不会导入其他角色的私人对话。每人简短回应，也可以提出不同意见，不重复前一人的回答。不得声称已经操控软件。',dialogue_language='zh-CN')))
            index={'session_id':result['id']};write(path,index)
        if not index:return {'session':None}
        result=self.dialogue.get(scope,index['session_id']);return {'session':result,'scope':scope}
    def reply(self,char,b):
        with self.lock:data=self.session(char,b.project,True);row=data['session']
        if b.etag and row['etag']!=b.etag:raise ConsoleError('对话已经变化，请刷新',409)
        profiles=self.settings().profiles
        if char=='duet':
            row=self.dialogue.edit(data['scope'],row['id'],SessionEdit(etag=row['etag'],branch_id=row['selected_branch'],actor_models={a['id']:profiles.get(k,Profile()).ai_model or None for k,a in zip(['yoshino','rem'],row['actors'])}))
        profile=profiles.get(char,Profile())
        return self.dialogue.reply(data['scope'],row['id'],Reply(etag=row['etag'],branch_id=row['selected_branch'],text=b.text,actor_ids=[a['id'] for a in row['actors']],model=b.model or profile.ai_model or None))
    def owned_task(self,id):
        task=self.app.state.manager.get(id)
        if not task.scope.startswith('roleplay-session_'):raise ConsoleError('不是陪伴文本任务',403)
        session_id=task.scope.removeprefix('roleplay-')
        if not any(read(p,{}).get('session_id')==session_id for p in (self.home/'dialogues').glob('*/companion-index.json')):raise ConsoleError('任务不属于陪伴会话',403)
        return task

def live_companion_routes(c):
    r=APIRouter(prefix='/api/studio/live2d')
    @r.get('/catalog')
    def catalog():return c.resources.catalog()
    @r.get('/settings')
    def settings():return c.settings().model_dump()
    @r.put('/settings')
    def configure(b:CompanionSettings):return c.save_settings(b)
    @r.get('/runtime/{name}')
    def runtime(name:str):return FileResponse(c.resources.runtime(name),media_type='text/javascript')
    @r.get('/models/{id}/{name:path}')
    def model_file(id:str,name:str):
        m=c.resources.model(id)
        if name not in m['files']:raise ConsoleError('不是模型声明的数据资源',404)
        if name==m['model']:return JSONResponse(m['definition'])
        path=data_file(c.resources.root/'models'/id,name)
        mime={'.json':'application/json','.png':'image/png','.webp':'image/webp','.jpg':'image/jpeg','.jpeg':'image/jpeg'}.get(path.suffix.lower(),'application/octet-stream')
        return FileResponse(path,media_type=mime)
    @r.post('/import')
    async def import_model(character:str,name:str,license_note:str,confirm_rights:bool,file:UploadFile=File()):
        info=ImportInfo(character=character,name=name,license_note=license_note,confirm_rights=confirm_rights)
        return c.resources.import_zip(await file.read(60*1024*1024+1),info)
    @r.get('/dialogue/{char}')
    def dialogue(char:str,project:str|None=None):return c.session(char,project)
    @r.post('/dialogue/{char}')
    def create(char:str,b:DialogueBody):return c.session(char,b.project,True)
    @r.post('/dialogue/{char}/reply')
    async def reply(char:str,b:DialogueBody):return c.reply(char,b)
    @r.post('/dialogue/{char}/memory')
    def memory(char:str,b:Remember):
        if char=='duet':raise ConsoleError('共同场景不自动合并私人记忆，请分别管理角色记忆',422)
        data=c.session(char,b.project);row=data['session']
        if not row:raise ConsoleError('请先开始角色会话',409)
        return c.dialogue.memory(data['scope'],row['id'],Memory(etag=b.etag,branch_id=row['selected_branch'],text=b.text,source_node_ids=b.source_node_ids,audiences=[row['actors'][0]['id']],confirm=True))
    @r.put('/dialogue/{char}/lore')
    def lore(char:str,b:LoreBody):
        if char=='duet':raise ConsoleError('请在各自私人会话管理世界书，不自动共享',422)
        data=c.session(char,b.project);row=data['session']
        if not row:raise ConsoleError('请先开始角色会话',409)
        for item in b.entries:
            item.audiences=[row['actors'][0]['id']]
            if item.source_type=='CONFIRMED_SOURCE':raise ConsoleError('不能将陪伴资料自动标为 Canon',422)
        return c.dialogue.edit(data['scope'],row['id'],SessionEdit(etag=b.etag,branch_id=row['selected_branch'],lore=b.entries))
    @r.post('/action')
    async def action(body:dict):
        from app.assistant.models import Start,Context
        if set(body)-{'tool','arguments','context'}:raise ConsoleError('操作字段不受支持',422)
        ctx=Context.model_validate(body.get('context',{}));ctx.selection=''
        return c.app.state.assistant.start_local_action(Start(instruction='用户点击角色提出的浏览操作',context=ctx),body.get('tool'),body.get('arguments',{}))
    @r.get('/tasks/{id}')
    def task(id:str):return c.owned_task(id).public()
    @r.post('/tasks/{id}/cancel')
    async def cancel(id:str):c.owned_task(id);return (await c.app.state.manager.cancel(id)).public()
    return r


def assert_public_live2d(root):
    """Only the owned frame adapter may be distributed, never Core/model data."""
    if not root.is_dir() or {p.name for p in root.iterdir()}!={'frame.html','frame.mjs'}:raise RuntimeError('Private Live2D runtime or models entered public resources')
    for name in ['frame.html','frame.mjs']:
        path=root/name
        if not safe_local(path,root) or path.stat().st_size>32*1024:raise RuntimeError('Invalid public Live2D adapter')


