import io,json,zipfile
from fastapi import APIRouter,UploadFile,File
from fastapi.responses import Response
from pydantic import Field
from app.assistant.models import Start
from app.automation.service import Run
from app.errors import ConsoleError
from .models import Strict,Manifest,Install,Configure,Change
from .service import MAX_ZIP
class Prepare(Strict):revision:str=Field(pattern=r'^[a-f0-9]{64}$')
class Launch(Start):revision:str=Field(pattern=r'^[a-f0-9]{64}$')
def routes(hub):
    r=APIRouter(prefix='/api/plugins')
    @r.get('/examples/{name}')
    def example(name:str):
        from .examples import package
        return Response(package(name),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="'+name+'.novelplugin.zip"','Cache-Control':'no-store'})
    @r.get('')
    def listing():return {'plugins':hub.list(),'api_version':'novel-studio-plugin/1','warning':hub.blocked}
    @r.get('/schema')
    def schema():return {'$schema':'https://json-schema.org/draft/2020-12/schema',**Manifest.model_json_schema()}
    @r.get('/integrations')
    def integrations():
        # Deliberately no SDK login, network probes or model loading on this page.
        return {'integrations':[
          {'id':'ai','name':'AI Provider / OpenAI-compatible','type':'settings','target':'api','state':'CONFIGURABLE'},
          {'id':'models','name':'Model routing / Context controls','type':'settings','target':'models','state':'BUILT_IN'},
          {'id':'codex','name':'Codex Agent / Novel Studio MCP','type':'settings','target':'assistant','state':'ON_DEMAND'},
          {'id':'images','name':'ComfyUI','type':'settings','target':'images','state':'EXTERNAL_SERVICE'},
          {'id':'python','name':'Python API / WASI','type':'page','target':'python','state':'ON_DEMAND'},
          {'id':'world','name':'World Logic / Experiment templates','type':'page','target':'worldlogic','state':'BUILT_IN'},
          {'id':'skills','name':'Installed writing Skills','type':'settings','target':'help','state':'EXTERNAL_DEPENDENCY'}]}
    @r.post('/preview')
    async def preview(file:UploadFile=File(...)):
        try:return hub.preview(await file.read(MAX_ZIP+1))
        finally:await file.close()
    @r.post('/install')
    def install(b:Install):return hub.install(b)
    @r.put('/{id}/enabled')
    def toggle(id:str,b:Change):return hub.toggle(id,b)
    @r.put('/{id}/config')
    def configure(id:str,b:Configure):return hub.configure(id,b)
    @r.post('/{id}/uninstall')
    def uninstall(id:str,b:Prepare):return hub.uninstall(id,b.revision)
    @r.get('/{id}/export')
    def export(id:str):return Response(hub.export(id),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="novel-plugin.zip"','Cache-Control':'no-store'})
    @r.get('/{id}/resources/{resource}')
    def resource(id:str,resource:str):
        row=hub.get(id,enabled=True);files=hub.contents(row)
        item=next((v for v in row['manifest']['resources'] if v['id']==resource),None)
        if not item:raise ConsoleError('插件资源不存在',404)
        return Response(files[item['file']],media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="'+item['file'].split('/')[-1]+'"','Cache-Control':'no-store'})
    @r.post('/{id}/commands/{command}/preview')
    def preview_command(id:str,command:str,b:Prepare):return hub.prepare(id,command,b.revision)
    @r.post('/{id}/commands/{command}/run',status_code=202)
    async def launch(id:str,command:str,b:Launch):
        prepared=hub.prepare(id,command,b.revision)
        if prepared['kind']=='entry':return prepared
        if not b.context.project:raise ConsoleError('请先打开作品再运行插件操作',422)
        body=b.model_dump(exclude={'revision'});body.update(code=prepared['code'],title=prepared['title'],timeout=90)
        result=hub.app.state.automation.start(Run(**body),plugin=prepared)
        return {**result,'code':prepared['code'],'title':prepared['title'],'plugin':prepared['source']}
    return r
