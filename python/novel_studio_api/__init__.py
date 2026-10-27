"""Typed, capability-scoped Novel Studio client. No database or filesystem API."""
from __future__ import annotations
import json, os, sys, time, urllib.error, urllib.request, uuid
from typing import Any

# Multiple Studio.connect() objects in one interpreter share the same stdio
# connection. Their request IDs must remain unique for the lifetime of it.
_rpc_sequence=0

class StudioError(RuntimeError):
    def __init__(self, result):
        self.result=result
        super().__init__(str(result.get('error',result.get('message','应用操作未完成'))))

class Studio:
    """Connect inside the isolated runner, or with an explicit author-issued grant."""
    def __init__(self, url='', token='', nonce=''):
        self.url=url.rstrip('/');self.token=token;self.nonce=nonce;self.sequence=0
        self.client_id=uuid.uuid4().hex if sys.platform!='wasi' else ''
        self.projects=Projects(self);self.chapters=Chapters(self);self.characters=Characters(self)
        self.world=World(self);self.ui=UI(self);self.ai=AI(self);self.tasks=Tasks(self);self.notes=Notes(self)
    @classmethod
    def connect(cls, url: str|None=None, token: str|None=None, nonce: str|None=None) -> Studio:
        if sys.platform=='wasi':return cls()
        url=url or os.environ.get('NOVEL_STUDIO_URL','')
        token=token or os.environ.get('NOVEL_STUDIO_CONTROL_TOKEN','')
        nonce=nonce or os.environ.get('NOVEL_STUDIO_NONCE','')
        from urllib.parse import urlsplit
        parsed=urlsplit(url)
        if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.path or not token or not nonce:
            raise StudioError({'error':'请在软件 Python Control 中创建临时授权，并显式提供本机 URL、token 与 nonce。不会扫描凭据。'})
        return cls(url,token,nonce)
    def call(self, action: str, **arguments: Any) -> dict:
        self.sequence+=1
        if sys.platform=='wasi':
            global _rpc_sequence
            _rpc_sequence+=1
            print('__NOVEL_RPC__'+json.dumps({'id':_rpc_sequence,'action':action,'arguments':arguments},ensure_ascii=False),flush=True)
            line=sys.stdin.readline(1000000)
            if not line:raise StudioError({'error':'受控连接已关闭'})
            response=json.loads(line)
        else:
            body=json.dumps({'action':action,'arguments':arguments,'call_id':self.client_id+':'+str(self.sequence)}).encode()
            request=urllib.request.Request(self.url+'/api/control/call',body,headers={'Content-Type':'application/json','X-Novel-Control':self.token,'X-Novel-Request':self.nonce})
            # Never send a grant to a redirected host or honor proxy environment.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self,*a,**k):return None
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            try:
                with opener.open(request,timeout=40) as result:receipt=json.load(result)
            except urllib.error.HTTPError as error:
                raise StudioError({'error':'受控 API 拒绝操作（HTTP '+str(error.code)+'）；请查看原任务或重新创建本机授权。'}) from None
            until=time.monotonic()+180
            while time.monotonic()<until:
                query=urllib.request.Request(self.url+'/api/control/calls/'+receipt['task_id'],headers={'X-Novel-Control':self.token})
                with opener.open(query,timeout=40) as result:state=json.load(result)
                if state['status'] in ('SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'):
                    response=state.get('result') or {'ok':False,'error':state.get('error') or state['status']};break
                time.sleep(.25)
            else:raise StudioError({'error':'操作等待超时；未自动重试。请查看原任务。','task_id':receipt['task_id']})
        if response.get('pending_confirmation'):
            raise StudioError(response)
        if not response.get('ok'):raise StudioError(response)
        return response.get('result',{})
    def actions(self) -> dict:return self.call('list_application_actions')

class Namespace:
    def __init__(self, studio: Studio):self.studio=studio
class Projects(Namespace):
    def current(self) -> dict:return self.studio.call('get_active_project')
    def list(self) -> dict:return self.studio.call('list_projects')
    def status(self) -> dict:return self.studio.call('get_project_status')
class Chapters(Namespace):
    def list(self, offset: int=0, limit: int=100) -> dict:return self.studio.call('list_chapters',offset=offset,limit=limit)
    def search(self, query: str) -> dict:return self.studio.call('search_chapters',query=query)
    def open(self, number: int) -> dict:return self.studio.call('open_chapter',number=number)
    def read(self, number: int, start: int=0, limit: int=8000) -> dict:return self.studio.call('read_chapter',number=number,start=start,limit=limit)
class Characters(Namespace):
    def search(self, query: str='') -> dict:return self.studio.call('search_characters',query=query)
    def get(self, id: str) -> dict:return self.studio.call('get_character_details',id=id)
    def create_draft(self, name: str, summary: str='') -> dict:return self.studio.call('create_character_draft',name=name,summary=summary)
class World(Namespace):
    def search(self, query: str='') -> dict:return self.studio.call('search_world_bible',query=query)
    def get(self, id: str) -> dict:return self.studio.call('get_world_details',id=id)
class UI(Namespace):
    def state(self) -> dict:return self.studio.call('get_editor_state')
    def open_chapter(self, number: int) -> dict:return self.studio.call('open_chapter',number=number)
    def open_reference(self, kind: str, number: int|None=None, id: str|None=None) -> dict:
        return self.studio.call('open_reference',kind=kind,number=number,id=id)
    def layout(self, preset: str) -> dict:return self.studio.call('set_workspace_layout',preset=preset)
    def navigate(self, page: str) -> dict:return self.studio.call('navigate_to_page',page=page)
class AI(Namespace):
    def models(self) -> dict:return self.studio.call('get_available_models')
    def start(self, instruction: str, chapters: list[int]|None=None, controls: dict|None=None) -> dict:
        return self.studio.call('start_text_task',instruction=instruction,chapters=chapters or [],controls=controls)
class Tasks(Namespace):
    def shared(self) -> dict:return self.studio.call('list_shared_results')
    def share(self, id: str, persona: str, note: str='') -> dict:return self.studio.call('share_task_result',id=id,persona=persona,note=note)
    def get(self, id: str) -> dict:return self.studio.call('read_task_result',id=id)
    def cancel(self, id: str) -> dict:return self.studio.call('stop_controlled_task',id=id)
    def steer(self, id: str, instruction: str) -> dict:return self.studio.call('steer_controlled_task',id=id,instruction=instruction)
    def wait(self, id: str, timeout: float=90) -> dict:
        return self.studio.call('wait_controlled_task',id=id,timeout=min(150,max(1,int(timeout))))
    def events(self,id: str,after: int=0) -> dict:return self.studio.call('read_task_events',id=id,after=after)
class Notes(Namespace):
    def create(self, text: str) -> dict:return self.studio.call('create_inspiration_note',text=text)
    def list(self, kind: str='inspiration') -> dict:return self.studio.call('list_author_entries',kind=kind)
    def todo(self, text: str) -> dict:return self.studio.call('create_chapter_todo',text=text)
