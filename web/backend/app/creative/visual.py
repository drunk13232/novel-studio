"""Optional trusted Blender CLI and selected-text briefs, reusing tools, tasks and assets."""
import re,time,subprocess,threading,hashlib
from pathlib import Path
from typing import Literal
from pydantic import Field
from fastapi import APIRouter
from app.errors import ConsoleError
from app.studio_tools import Strict
from app.creative.materials import Origin
from app.library.storage import uid,now,digest,write,safe,read
from app.models.requests import TaskRequest,TaskOptions

class Config(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    executable:str=Field(default='',max_length=600)
    template:str=Field(default='',max_length=600)
    confirm_trusted:Literal[True]
class Brief(Strict):
    origin:Origin
    scene:str=Field(default='',max_length=6000)
    camera:str=Field(default='',max_length=2000)
    characters:str=Field(default='',max_length=2000)
    dialogue:str=Field(default='',max_length=4000)
class Launch(Strict):
    brief_id:str=Field(pattern=r'^brief_[0-9a-f]{32}$')
    confirm:Literal[True]

def fingerprint(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

class Visual:
    def __init__(self,tools,materials,assets):self.tools=tools;self.materials=materials;self.assets=assets;self.lock=threading.RLock();self.active={}
    def config(self,p):return self.tools.preference(p,'visual/blender')
    def file(self,value,kind):
        path=Path(value)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():raise ConsoleError('请选择存在的本地文件，不接受链接或相对路径',422)
        path=path.resolve()
        if (kind=='program' and path.name.lower() not in {'blender.exe','blender'}) or (kind=='template' and path.suffix.lower()!='.blend'):raise ConsoleError('请选择 Blender 程序或 .blend 工程',422)
        if path.stat().st_size>512*1024*1024:raise ConsoleError('辅助接口仅支持 512 MiB 以内的程序或模板',413)
        return path
    def configure(self,p,b):
        with self.lock:
            value={}
            for key,kind in [('executable','program'),('template','template')]:
                v=getattr(b,key)
                if v:
                    f=self.file(v,kind);value[key]=str(f);value[key+'_sha256']=fingerprint(f)
            return self.tools.put_pref(p,'visual/blender',value,b.etag)
    def checked(self,p):
        v=self.config(p)['value']
        if not v.get('executable') or not v.get('template'):raise ConsoleError('先选择并确认可信的 Blender 程序与工程模板；未安装时仍可导出场景资料',409)
        files=[]
        for key,kind in [('executable','program'),('template','template')]:
            f=self.file(v[key],kind)
            if fingerprint(f)!=v[key+'_sha256']:raise ConsoleError('Blender 程序或模板已变化，请重新检查并确认',409)
            files.append(f)
        return files
    def probe(self,p):
        v=self.config(p)['value']
        if not v.get('executable'):return {'available':False,'reason':'未配置 Blender；场景资料导出仍可使用'}
        f=self.file(v['executable'],'program')
        if fingerprint(f)!=v['executable_sha256']:raise ConsoleError('程序已变化，请重新确认',409)
        try:
            r=subprocess.run([str(f),'--factory-startup','--disable-autoexec','--version'],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            text=r.stdout.decode('utf8','replace')[:500];match=re.search(r'Blender \d+\.\d+[^\r\n]*',text)
            return {'available':r.returncode==0 and bool(match),'version':match[0] if match else None,'reason':'' if r.returncode==0 else '程序检查失败'}
        except (OSError,subprocess.TimeoutExpired):raise ConsoleError('Blender 程序无法启动或检查超时，请检查所选文件',503) from None
    def brief(self,p,b):
        self.tools.writable(p);self.materials.origin(p,b.origin);id=uid('brief')
        row={'schema_version':'1','id':id,'project_id':p,'created_at':now(),'origin':b.origin.model_dump(),'scene':b.scene,'camera':b.camera,'characters':b.characters,'dialogue':b.dialogue,'authority':'AUTHOR_SELECTED_REFERENCE_NOT_CANON','template_contract':'JSON sidecar for manual reference; no template scripts are executed or injected'}
        write(self.tools.local(p,'visual/briefs/'+id+'.json'),row);return row
    def get_brief(self,p,id):
        if not re.fullmatch(r'brief_[0-9a-f]{32}',id):raise ConsoleError('场景资料不存在',404)
        row=read(self.tools.local(p,'visual/briefs/'+id+'.json'))
        if not row or row.get('project_id')!=p:raise ConsoleError('场景资料不属于当前作品',404)
        return row
    def launch(self,p,b):
        brief=self.get_brief(p,b.brief_id);self.materials.origin(p,Origin(**brief['origin']));exe,template=self.checked(p)
        try:proc=subprocess.Popen([str(exe),'--factory-startup','--disable-autoexec',str(template)],cwd=str(template.parent),close_fds=True)
        except OSError:raise ConsoleError('Blender 启动失败',503) from None
        return {'status':'LAUNCHED','preview_rendered':False,'brief_id':brief['id'],'reference_file':str(self.tools.local(p,'visual/briefs/'+brief['id']+'.json')),'pid':proc.pid,'notice':'可信模板已交给 Blender；场景资料是单独 JSON 参考，不会自动修改工程。'}
    async def render(self,p,b):
        self.tools.writable(p);brief=self.get_brief(p,b.brief_id);self.materials.origin(p,Origin(**brief['origin']));exe,template=self.checked(p);manager=self.tools.manager(p)
        with self.lock:
            old=self.active.get(p)
            if old and manager.get(old).status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:raise ConsoleError('本作品已有 Blender 预览任务',409)
            id=uid('render');out=self.tools.local(p,'visual/renders/'+id);out.mkdir(parents=True,exist_ok=True)
            def work(emit,cancel):
                if cancel():return {'status':'interrupted'}
                command=[str(exe),'--background','--factory-startup','--disable-autoexec',str(template),'--threads','2','--render-format','PNG','--render-output',str(out/'preview_'),'--render-frame','1']
                started=time.monotonic();proc=None
                try:
                    with (out/'render.log').open('wb') as log:
                        proc=subprocess.Popen(command,cwd=str(template.parent),stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                        while proc.poll() is None:
                            if cancel():return {'status':'interrupted'}
                            if time.monotonic()-started>110:raise ConsoleError('Blender 单帧预览超时，任务已停止',504)
                            if (out/'render.log').stat().st_size>4*1024*1024:raise ConsoleError('渲染输出过大，任务已停止',413)
                            time.sleep(.15)
                    if cancel():return {'status':'interrupted'}
                    images=list(out.glob('preview_*.png'))
                    if proc.returncode!=0 or len(images)!=1:raise ConsoleError('模板未产生单帧 PNG 预览；请在 Blender 检查相机、场景及外部资源',422)
                    if images[0].stat().st_size>24*1024*1024:raise ConsoleError('预览超过 24 MiB，请缩小模板分辨率',413)
                    asset=self.assets.import_image(p,images[0].read_bytes(),'Blender 场景预览',generated={'backend':'Blender','brief_id':brief['id'],'template_sha256':fingerprint(template)})
                    return {'status':'completed','asset_id':asset['id'],'brief_id':brief['id'],'notice':'预览已加入现有图片资料库；模板本身未修改。'}
                finally:
                    if proc and proc.poll() is None:
                        proc.terminate()
                        try:proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
            t=manager.prepared(TaskRequest(type='custom_prompt',prompt='已确认的可信 Blender 模板单帧预览',options=TaskOptions(timeout_seconds=120)),'',True,'visual:'+id,execute=work,provider='本机 Blender',skill='受控官方 CLI 单帧渲染')
            self.active[p]=t.id;return t.public()

def routes(s):
    r=APIRouter(prefix='/api/projects/{p}/visual')
    @r.get('/blender')
    def config(p:str):return s.config(p)
    @r.put('/blender')
    def configure(p:str,b:Config):return s.configure(p,b)
    @r.post('/blender/probe')
    def probe(p:str):return s.probe(p)
    @r.post('/briefs')
    def brief(p:str,b:Brief):return s.brief(p,b)
    @r.get('/briefs/{id}')
    def get(p:str,id:str):return s.get_brief(p,id)
    @r.post('/blender/open')
    def launch(p:str,b:Launch):return s.launch(p,b)
    @r.post('/blender/render')
    async def render(p:str,b:Launch):return await s.render(p,b)
    return r
