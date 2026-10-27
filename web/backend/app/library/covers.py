"""Draft/project cover storage using the same Assets and ImageStudio worker."""
import copy
import re
import shutil
import uuid
from typing import Literal
from fastapi import APIRouter,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.projects.service import NovelWorkspace
from .storage import safe,read,write,digest,now
from .assets import MAX_BYTES

class CoverScopes:
    def __init__(self,registry,drafts):self.formal=registry;self.drafts=drafts;self.engine=registry.engine;self.scan()
    def scan(self):
        self.formal.scan();self.rows={**self.formal.rows,**{r['id']:r for r in self.drafts.list()}}
        return self.rows
    def get(self,id):
        if id.startswith('draft_'):
            row=self.drafts.get(id)
            if row.get('committed_project_id'):raise ConsoleError('草稿已创建；请打开正式作品封面',409)
            return row
        return self.formal.get(id)
    def workspace(self,id):
        self.get(id)
        return NovelWorkspace(self.drafts.path(id)) if id.startswith('draft_') else self.formal.workspace(id)

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class TextLayer(Strict):
    text:str=Field(default='',max_length=1000)
    font:str=Field(default='Microsoft YaHei',max_length=100)
    size:float=Field(default=48,ge=8,le=400)
    spacing:float=Field(default=0,ge=-200,le=2000)
    line_height:float=Field(default=1.2,ge=.5,le=4)
    align:Literal['left','center','right']='center'
    color:str=Field(default='#ffffff',pattern=r'^#[0-9a-fA-F]{6}$')
    shadow:bool=True
    x:float=Field(default=32,ge=-2048,le=4096)
    y:float=Field(default=80,ge=-2048,le=4096)
    width:float=Field(default=448,ge=20,le=4096)
    visible:bool=True
class Layout(Strict):
    width:int=Field(default=512,ge=128,le=2048)
    height:int=Field(default=768,ge=128,le=2048)
    title:TextLayer=Field(default_factory=TextLayer)
    author:TextLayer=Field(default_factory=lambda:TextLayer(text='',size=24,y=650))
    background_x:float=Field(default=0,ge=-10000,le=10000)
    background_y:float=Field(default=0,ge=-10000,le=10000)
    background_scale:float=Field(default=1,ge=.01,le=100)
    text_order:Literal['title','author']='title'
class GenerationSettings(Strict):
    workflow_id:str=Field(default='',pattern=r'^(?:workflow_[0-9a-f]{32})?$')
    model:str=Field(default='',max_length=300)
    seed:int=Field(default=12345,ge=0,le=9007199254740991)
    steps:int=Field(default=20,ge=1,le=150)
    cfg:float=Field(default=7,ge=0,le=30)
    reference:str=Field(default='',pattern=r'^(?:asset_[0-9a-f]{32})?$')
class CoverSave(Strict):
    id:str=Field(default='',pattern=r'^(?:cover_[0-9a-f]{32})?$')
    etag:str|None=None
    name:str=Field(default='封面方案',min_length=1,max_length=120)
    background_asset:str|None=None
    rendered_asset:str|None=None
    layout:Layout=Field(default_factory=Layout)
    concept:str=Field(default='',max_length=3000)
    prompt:str=Field(default='',max_length=8000)
    negative:str=Field(default='',max_length=2000)
    status:Literal['DRAFT','READY']='DRAFT'
    parameters:GenerationSettings=Field(default_factory=GenerationSettings)

class Covers:
    def __init__(self,images):self.images=images;self.registry=images.registry;self.assets=images.assets
    def root(self,id):return self.registry.workspace(id).root
    def get(self,scope,id):
        if not re.fullmatch(r'cover_[0-9a-f]{32}',id):raise ConsoleError('无效封面ID',403)
        p=safe(self.root(scope),'covers/'+id+'.json');row=read(p)
        if not row:raise ConsoleError('封面不存在',404)
        return {**row,'etag':digest(p.read_bytes())}
    def list(self,scope):
        root=self.root(scope);p=safe(root,'covers');official=read(safe(root,'covers/official.json')) or {}
        return {'versions':[self.get(scope,x.stem) for x in p.glob('cover_*.json')] if p.exists() else [],'official':official,'assets':self.assets.list(scope),'workflows':self.images.rows(scope,'workflows'),'jobs':self.images.rows(scope,'jobs')}
    def save(self,scope,request):
        root=self.root(scope);row=request.model_dump();id=row['id'] or 'cover_'+uuid.uuid4().hex
        if request.id:
            old=self.get(scope,id)
            if request.etag!=old['etag']:raise ConsoleError('封面已被修改，请刷新后再保存',409)
            row['created_at']=old['created_at']
        else:row['created_at']=now()
        for key in ['background_asset','rendered_asset']:
            if row[key]:self.assets.get(scope,row[key])
        background=self.assets.get(scope,row['background_asset']) if row['background_asset'] else {}
        row.pop('etag',None);row.update(id=id,updated_at=now(),generation=background.get('generation'))
        write(safe(root,'covers/'+id+'.json'),row)
        return self.get(scope,id)
    def official(self,scope,id,etag):
        row=self.get(scope,id)
        if row['etag']!=etag:raise ConsoleError('封面版本已变化',409)
        if not row['rendered_asset']:raise ConsoleError('请先保存包含文字的完整封面预览',409)
        write(safe(self.root(scope),'covers/official.json'),{'cover_id':id,'asset_id':row['rendered_asset'],'updated_at':now()})
        return self.list(scope)
    def migrate(self,draft,staging,project_id):
        root=self.root(draft)
        # Originals are copies managed by Assets; imported source paths never enter this store.
        for relative in ['assets','covers','art']:
            source=safe(root,relative)
            if not source.exists():continue
            for p in source.rglob('*'):
                if p.is_symlink() or p.is_junction():raise ConsoleError('封面资源链接被拒绝',403)
                if p.is_file():
                    dest=safe(staging,p.relative_to(root).as_posix());dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
                    if p.relative_to(root).as_posix().startswith('art/jobs/') and p.suffix=='.json':
                        job=read(dest);job.update(origin_draft=draft,project_id=project_id);write(dest,job)
        official=read(safe(staging,'covers/official.json'))
        if official:
            import yaml
            from app.projects.service import write_yaml
            manifest=yaml.safe_load((staging/'project.yaml').read_text(encoding='utf8'));manifest['cover']={'manifest':'covers/official.json'};write_yaml(staging/'project.yaml',manifest)

def cover_routes(covers,drafts):
    router=APIRouter()
    from .api import limited
    def register(prefix):
        @router.get(prefix)
        def listing(scope:str):return covers.list(scope)
        @router.post(prefix)
        def save(scope:str,body:CoverSave):return covers.save(scope,body)
        @router.post(prefix+'/official')
        def official(scope:str,body:dict):return covers.official(scope,body.get('id',''),body.get('etag',''))
        @router.post(prefix+'/import')
        async def imported(scope:str,request:Request,name:str='封面素材'):
            row=covers.assets.import_image(scope,await limited(request,MAX_BYTES),name)
            return covers.assets.update(scope,row['id'],{'category':'封面'},row['etag'])
        @router.post(prefix+'/gallery')
        def gallery(scope:str,body:dict):
            source=body.get('project_id','');asset=body.get('asset_id','')
            if not source.startswith('novel_'):raise ConsoleError('请选择正式作品图库',422)
            path=covers.assets.path(source,asset)
            return covers.assets.import_image(scope,path.read_bytes(),'图库封面素材')
        @router.get(prefix+'/assets/{id}')
        def file(scope:str,id:str,thumbnail:bool=False,download:bool=False):
            path=covers.assets.path(scope,id,thumbnail)
            return FileResponse(path,filename='novel-cover-'+id[6:14]+path.suffix if download else None,headers={'Cache-Control':'no-store'})
        @router.post(prefix+'/workflows')
        def workflow(scope:str,body:dict):return covers.images.put_workflow(scope,body)
        @router.post(prefix+'/workflow-copy')
        def copy_workflow(scope:str,body:dict):
            source=body.get('project_id','')
            if not source.startswith('novel_'):raise ConsoleError('请选择正式作品工作流',422)
            row=copy.deepcopy(covers.images.get(source,'workflows',body.get('id','')));row.pop('id',None)
            return covers.images.put_workflow(scope,row)
        @router.post(prefix+'/jobs')
        def enqueue(scope:str,body:dict):
            if body.get('spoiler_confirmed') is not True and body.get('profile_prompt') is not True:raise ConsoleError('请确认使用公开封面概念，或明确授权自填提示词',409)
            if body.get('spoiler_confirmed') is not True:
                from app.projects.creation import session
                concepts=session(drafts.get(scope))['cover_concepts'] if scope.startswith('draft_') else []
                params=body.get('parameters',{})
                if not any(c['prompt']==params.get('positive') and c['negative']==params.get('negative') for c in concepts):raise ConsoleError('公开概念已变化或提示词被编辑，请重新选择或明确授权',409)
            body={k:v for k,v in body.items() if k not in {'spoiler_confirmed','profile_prompt'}}
            return covers.images.enqueue(scope,body)
        @router.post(prefix+'/jobs/{id}/cancel')
        def cancel(scope:str,id:str):return covers.images.cancel(scope,id)
    register('/api/drafts/{scope}/covers');register('/api/projects/{scope}/covers')
    return router
