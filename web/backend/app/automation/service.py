"""Bounded Python orchestration over existing assistant sessions and tasks."""
import asyncio,hashlib,json,os,queue,secrets,subprocess,sys,threading,time,uuid
from pathlib import Path
from types import SimpleNamespace
from fastapi import APIRouter,Request
from fastapi.responses import StreamingResponse
from pydantic import Field
from app.assistant.models import Start,PythonPlan,Strict,Persona,Reply
from app.assistant.service import Session
from app.errors import ConsoleError
from app.tasks.storage import atomic_json
from app.library.storage import read,now
from app.models.requests import TaskRequest,TaskOptions
from app.ai.credentials import scrub

class DirectorHandoff(Strict):
    id:str=Field(pattern=r'^director_[0-9a-f]{32}$')
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
class Run(Start):
    director_handoff:DirectorHandoff|None=None
    code:str=Field(min_length=1,max_length=64000)
    title:str=Field(default='Python Control',max_length=120)
    timeout:int=Field(default=90,ge=10,le=180)
class Script(Strict):
    project:str;persona:Persona='assistant'
    id:str=Field(default='',pattern=r'^(?:script_[0-9a-f]{32})?$')
    name:str=Field(min_length=1,max_length=120)
    code:str=Field(min_length=1,max_length=64000)
class DirectorNote(Strict):
    project:str
    persona:Persona='assistant'
    record_id:str=Field(pattern=r'^director_[0-9a-f]{32}$')
    run_id:str=Field(pattern=r'^py_[0-9a-f]{32}$')
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    comment:str=Field(default='',max_length=2000)

class Grant(Start):pass
class Call(Strict):
    action:str=Field(min_length=1,max_length=80)
    arguments:dict=Field(default_factory=dict)
    call_id:str=Field(min_length=1,max_length=80)

class Control:
    def __init__(self,center):
        self.center=center;self.root=center.root/'python-control';self.lock=threading.RLock();self.processes={};self.runs={};self.owned=set();self.listeners=set();self.loop=None;self.closed=False;self.grants={};self.active_project=None
    def folder(self,p,persona):
        self.center.settings(persona,p)
        # Existing project backup/restore already includes metadata files.
        return self.center.app.state.registry.workspace(p).root/'metadata/python-control'/persona
    def notify(self):
        if self.loop and not self.closed:
            for listener in tuple(self.listeners):
                def send(q=listener):
                    if not q.full():q.put_nowait(True)
                self.loop.call_soon_threadsafe(send)
    def task_access(self,p,persona):
        return read(self.folder(p,persona)/'task-access.json',[])
    def remember_task(self,s,task_id,model):
        with self.lock:
            rows=[r for r in self.task_access(s.project,s.persona) if r.get('id')!=task_id]
            rows.append({'id':task_id,'model':model,'source_session':s.id,'created_at':now(),'access':'own'})
            atomic_json(self.folder(s.project,s.persona)/'task-access.json',rows[-100:])
    def remember_task_result(self,s,task):
        if self.center.settings(s.persona,s.project).save_conversation:
            result=dict(task.result or {})
            for key in ('output','partial_output'):
                if isinstance(result.get(key),str) and len(result[key])>128000:result[key]=result[key][:128000];result['output_truncated']=True
            row={'id':task.id,'project':s.project,'persona':s.persona,'status':task.status,'result':result,'error':task.error,'ai_metadata':task.ai_metadata,'finished_at':task.finished_at,'source_session':s.id}
            atomic_json(self.folder(s.project,s.persona)/('ai_'+task.id+'.json'),row)
        self.notify()
    def task_result(self,s,id):
        # Only called after the Action layer has verified ownership or a fixed
        # author-approved read-only handoff. Never scan other personas' chats.
        who=s.persona
        if id not in getattr(s,'controlled_tasks',set()):
            shared=read(self.folder(s.project,s.persona)/'shared-results.json',[])
            source=next((r for r in shared if r['id']==id),None)
            if not source:return None
            who=source['from_persona']
        return read(self.folder(s.project,who)/('ai_'+id+'.json'),None)
    def share_task(self,s,b):
        if b.id not in getattr(s,'controlled_tasks',set()):raise ConsoleError('只能交接当前角色实际创建的任务结果',403)
        if b.persona==s.persona:raise ConsoleError('请选择另一位助手',422)
        task=s.manager.get(b.id)
        if task.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:raise ConsoleError('请等待任务完成或停止后再交接固定结果',409)
        with self.lock:
            path=self.folder(s.project,b.persona)/'shared-results.json';rows=read(path,[])
            row={'id':b.id,'from_persona':s.persona,'to_persona':b.persona,'project':s.project,'note':b.note,'created_at':now(),'status':task.status,'source_session':s.id,'access':'read-only'}
            rows=[v for v in rows if not (v['id']==b.id and v['from_persona']==s.persona)]+[row]
            atomic_json(path,rows[-100:])
        return {**row,'shared':True,'includes_other_conversations':False,'canon_changed':False}
    def save(self,row):
        # User-visible private run history; not global diagnostics or public assets.
        with self.lock:
            folder=self.folder(row['project'],row['persona']);atomic_json(folder/(row['id']+'.json'),row)
        self.notify()
    def get(self,p,id,persona=None):
        if not id.startswith('py_') or len(id)!=35 or any(c not in '0123456789abcdef' for c in id[3:]):raise ConsoleError('运行 ID 无效',422)
        for who in ([persona] if persona else ['assistant','yoshino','rem','haru']):
            row=read(self.folder(p,who)/(id+'.json'),None)
            if row:return self.with_confirmation(row)
        raise ConsoleError('运行记录不属于当前作品/角色',404)
    def with_confirmation(self,row):
        result=dict(row)
        if row.get('confirmation_id'):
            confirmation=self.center.confirmations.rows.get(row['confirmation_id'],{})
            result['confirmation_status']=confirmation.get('status','UNKNOWN')
            result['continuation']='Python 在确认点已经停止；审批只执行固定动作，不自动重放脚本。'
        return result
    def history(self,p,persona):
        folder=self.folder(p,persona)
        rows=[]
        for path in sorted(folder.glob('py_*.json'),key=lambda f:f.stat().st_mtime,reverse=True)[:30]:
            row=read(path,{})
            if row.get('status')=='RUNNING' and row.get('id') not in self.runs:
                row.update(status='INTERRUPTED',error='软件已重启；没有自动重放脚本或写入操作。');atomic_json(path,row)
            rows.append(self.with_confirmation(row))
        return rows
    def session(self,b):
        self.center.app.state.registry.get(b.context.project)
        cfg=self.center.settings(b.persona,b.context.project)
        if not cfg.selection:b.context.selection=''
        s=Session(self.center,b,cfg);s.manager=self.center.manager(s.project)
        s.provider=SimpleNamespace(provider_id='local-action',display_name='Python / 受控应用接口')
        s.model=SimpleNamespace(id='CPython WASI',capabilities={'tools':True})
        s.ai_controls=b.ai_controls;s.deadline=time.monotonic()+b.timeout+30
        s.controlled_tasks={r['id'] for r in self.task_access(s.project,s.persona) if r.get('access')=='own'}
        if b.previous_session:
            old=self.center.sessions.get(b.previous_session)
            if not old or old.project!=s.project or old.persona!=s.persona:raise ConsoleError('续接来源不属于当前作品与角色',403)
            s.controlled_tasks.update(getattr(old,'controlled_tasks',set()))
        # Register only after scope validation. Keep finished in-memory controllers
        # bounded; durable history remains in the project metadata directory.
        for id in tuple(self.owned):
            old=self.center.sessions.get(id)
            if old is None:self.owned.discard(id)
            elif len(self.owned)>=100 and old.ended and not old.pending:
                self.center.sessions.pop(id,None);self.owned.discard(id)
        self.center.sessions[s.id]=s;self.owned.add(s.id)
        return s
    def start(self,b,parent=None,plugin=None):
        if self.closed:raise ConsoleError('软件正在退出',503)
        self.loop=asyncio.get_running_loop()
        if any(not s.ended and s.project==b.context.project and s.id in self.owned and (not getattr(s,'external_python',False) or s.pending or s.task and s.task.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}) for s in self.center.sessions.values()):raise ConsoleError('当前作品已有 Python 操作，请先停止或等待',409)
        # Validate explicit source scope before creating a session or task. A
        # handoff grants only this frozen candidate, never a directory or model.
        snapshot=self.center.app.state.creative_director.snapshot(b.context.project,b.director_handoff.id,b.director_handoff.etag) if b.director_handoff else None
        s=self.session(b)
        if snapshot:s.director_result=snapshot
        if plugin:
            s.plugin_source=dict(plugin['source']);s.plugin_actions=frozenset(plugin['actions'])
        run_id='py_'+uuid.uuid4().hex
        s.python_run_id=run_id
        if snapshot:s.python_director_source={k:snapshot[k] for k in ('record_id','etag','draft_sha256','source_path')}
        if parent:
            parent.check();s.control_parent=parent
            if not hasattr(parent,'control_children'):parent.control_children=set()
            parent.control_children.add(s.id)
        req=TaskRequest(type='custom_prompt',prompt='作者启动 Python Control（源码仅显式保存时保留）',options=TaskOptions(read_only=True,resume=False,timeout_seconds=b.timeout+30))
        def execute(emit,cancel):
            result=self.run(s,PythonPlan(code=b.code,title=b.title,timeout=b.timeout),cancel,run_id)
            return {'status':'interrupted' if s.cancelled else 'completed' if result['status'] in {'SUCCEEDED','WAITING_CONFIRMATION'} else 'failed','output':result['output'],'error':result.get('error')}
        s.task=s.manager.prepared(req,'',True,'python-'+s.id,execute=lambda emit,cancel:self.center.finish(s,lambda:execute(emit,cancel)),provider='CPython 3.14.7 / WASI',skill='同一 Action Registry；无主机文件/网络',application_actions=True,orchestrator=True,finished=lambda task:self.notify())
        s.task.private_text=True;self.notify()
        return {**s.view(),'run_id':run_id}
    def grant(self,b):
        self.loop=asyncio.get_running_loop()
        self.grants={k:v for k,v in self.grants.items() if time.monotonic()<v['expires'] and not v['session'].cancelled}
        if len(self.grants)>=20:raise ConsoleError('临时授权过多，请先撤销旧授权',429)
        self.active_project=b.context.project
        run=Run(**b.model_dump(),code='# External Python grant; no code execution',timeout=180)
        s=self.session(run);s.external_python=True;s.deadline=time.monotonic()+900
        token=secrets.token_urlsafe(32)
        self.grants[token]={'session':s,'expires':s.deadline,'calls':{}}
        self.notify()
        return {'token':token,'session_id':s.id,'expires_seconds':900,'project':s.project,'persona':s.persona,'permissions':s.settings.model_dump(),'notice':'仅当前软件进程有效；项目切换、取消、退出或15分钟后失效；重要操作仍需确认。'}
    def authorized(self,request):
        token=request.headers.get('x-novel-control','')
        if request.headers.get('origin'):raise ConsoleError('外部控制接口不接受网页 Origin',403)
        grant=next((v for k,v in self.grants.items() if secrets.compare_digest(k,token)),None)
        if not grant or self.closed or time.monotonic()>=grant['expires']:raise ConsoleError('临时授权无效或过期',403)
        s=grant['session']
        if self.active_project!=s.project or s.cancelled:raise ConsoleError('作品已切换或授权取消',409)
        return grant
    def submit_call(self,grant,b):
        s=grant['session'];s.check()
        signature=hashlib.sha256(json.dumps([b.action,b.arguments],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self.lock:
            previous=grant['calls'].get(b.call_id)
            if previous:
                if previous[0]!=signature:raise ConsoleError('幂等调用 ID 被用于不同操作',409)
                return {'task_id':previous[1]}
            if s.pending or s.task and s.task.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:raise ConsoleError('请等待当前调用或处理确认后再继续',409)
            from app.assistant.actions import TOOLS
            if b.action not in TOOLS:raise ConsoleError('动作不存在',403)
            TOOLS[b.action].schema.model_validate(b.arguments)
            request=TaskRequest(type='custom_prompt',prompt='作者临时授权的 Python API 操作',options=TaskOptions(read_only=True,resume=False,timeout_seconds=180))
            def execute(emit,cancel):
                if cancel():s.stop()
                result=s.call(b.action,b.arguments);s.output='外部 Python 操作回执：'+json.dumps(result,ensure_ascii=False)[:16000];self.center.remember(s);self.notify()
                return {'status':'completed','output':json.dumps(result,ensure_ascii=False)}
            task=s.manager.prepared(request,'',True,'python-api-'+uuid.uuid4().hex,execute=execute,complete=lambda output:{'control_result':json.loads(output)},provider='受控 Python SDK',skill='临时项目授权；原有 Action 风险与确认',application_actions=True,orchestrator=True,finished=lambda task:self.notify())
            task.private_text=True;s.task=task;grant['calls'][b.call_id]=(signature,task.id);self.notify()
            return {'task_id':task.id}
    def start_nested(self,s,b):
        if getattr(s,'inside_python',False):raise ConsoleError('Python 运行不可递归启动自身',403)
        # This call is still Level 2 and remains subject to the original author
        # confirmation. New child sessions inherit exactly the same scoped mode.
        s.front('show_python_control',{})
        body=Run(persona=s.persona,instruction='执行作者已批准的 Python 操作计划',context=s.context.model_copy(deep=True),model=s.request_model or s.settings.model,ai_controls=getattr(s,'ai_controls',None),code=b.code,title=b.title,timeout=b.timeout)
        async def schedule():return self.start(body,parent=s)
        value=asyncio.run_coroutine_threadsafe(schedule(),self.loop).result(15)
        return {'id':value['run_id'],'session_id':value['id'],'task_id':value['task']['id'],'status':'QUEUED','note':'Python 已排队，尚未完成。每项操作继续执行原有权限与确认。'}
    def run(self,s,b,cancel,run_id=None):
        if self.closed:raise ConsoleError('软件正在退出',503)
        if getattr(s,'inside_python',False):raise ConsoleError('禁止递归执行',403)
        s.inside_python=True
        id=run_id or 'py_'+uuid.uuid4().hex
        row={'id':id,'project':s.project,'persona':s.persona,'title':b.title,'session_id':s.id,'created_at':now(),'status':'RUNNING','output':'','error':None,'code_sha256':hashlib.sha256(b.code.encode()).hexdigest(),'runtime':'CPython 3.14.7 / Wasmtime 49.0.0','actions':[]}
        if getattr(s,'director_result',None):row['director_source']={k:s.director_result[k] for k in ('record_id','etag','draft_sha256','source_path')}
        self.runs={k:v for k,v in self.runs.items() if k in self.processes or v.get('status')=='RUNNING'}
        self.runs[id]=row;self.save(row)
        frozen=getattr(sys,'frozen',False)
        # Windows venv python.exe is a redirector which starts another process.
        # Use its trusted base interpreter directly to retain the one-process Job.
        executable=sys.executable if frozen else getattr(sys,'_base_executable',sys.executable)
        command=[executable]+(['--python-control-worker'] if frozen else ['-m','app.automation.worker'])
        env={k:v for k,v in os.environ.items() if k in {'SystemRoot','WINDIR','TEMP','TMP','PATH','PROCESSOR_ARCHITECTURE','PROCESSOR_ARCHITEW6432','PROCESSOR_IDENTIFIER','NUMBER_OF_PROCESSORS'}}
        if not frozen:env['PYTHONPATH']=os.pathsep.join([str(Path(__file__).resolve().parents[2]),str(Path(sys.prefix)/'Lib/site-packages')])
        process=None;job=None;started=time.monotonic();chunks=queue.Queue(maxsize=200);seen=set();count=0
        try:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,cwd=str(Path(__file__).resolve().parent),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            if os.name=='nt':
                import win32job,win32api
                job=win32job.CreateJobObject(None,'')
                limits=win32job.QueryInformationJobObject(job,win32job.JobObjectExtendedLimitInformation)
                limits['BasicLimitInformation']['LimitFlags']=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE|win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY|win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                limits['BasicLimitInformation']['ActiveProcessLimit']=1
                limits['ProcessMemoryLimit']=1024*1024*1024
                win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,limits)
                handle=win32api.OpenProcess(0x0100|0x0001,False,process.pid)
                try:win32job.AssignProcessToJobObject(job,handle)
                finally:handle.Close()
            self.processes[id]=process
            process.stdin.write((json.dumps({'code':b.code},ensure_ascii=False)+'\n').encode());process.stdin.flush()
            def reader():
                try:
                    while line:=process.stdout.readline(1000001):chunks.put(line)
                finally:chunks.put(None)
            threading.Thread(target=reader,name='PythonControlOutput',daemon=True).start()
            while True:
                if cancel():s.stop();raise ConsoleError('用户停止 Python；未执行动作已撤销',409)
                if self.closed:raise ConsoleError('软件正在退出，Python 已停止',409)
                s.check()
                if time.monotonic()-started>b.timeout:raise ConsoleError('Python 达到运行时限；没有自动重试，已保留输出与已执行回执',408)
                try:line=chunks.get(timeout=.1)
                except queue.Empty:continue
                if line is None:break
                text=line.decode('utf-8',errors='replace')
                if text.startswith('__NOVEL_RPC__'):
                    request=json.loads(text[len('__NOVEL_RPC__'):]);cid=request['id'];name=request['action'];args=request['arguments']
                    if set(request)!={'id','action','arguments'} or type(cid)!=int or cid in seen or len(line)>80000 or name=='run_python_plan':raise ConsoleError('脚本操作请求无效、重复或递归',403)
                    seen.add(cid);count+=1
                    if count>100:raise ConsoleError('脚本达到 100 次接口调用上限',429)
                    current=s.center.settings(s.persona,s.project)
                    if any(getattr(s.settings,k) and not getattr(current,k) for k in ('page','selection','setting_context','manuscript','references','style')):raise ConsoleError('上下文授权已收回；脚本已停止',403)
                    result=s.call(name,args);row['actions'].append({'action':name,'ok':bool(result.get('ok')),'pending_confirmation':bool(result.get('pending_confirmation'))})
                    process.stdin.write((json.dumps(result,ensure_ascii=False)+'\n').encode());process.stdin.flush()
                else:
                    row['output']+=scrub(text)
                    if len(row['output'])>128000:raise ConsoleError('Python 输出达到 128000 字符限制，已停止',413)
                    s.output=row['output']
                self.save(row)
            code=process.wait(timeout=3)
            row['status']='WAITING_CONFIRMATION' if s.pending and s.pending['kind']=='confirm' else 'SUCCEEDED' if code==0 else 'FAILED'
            if row['status']=='WAITING_CONFIRMATION':row['confirmation_id']=s.pending['token']
            if code and row['status']!='WAITING_CONFIRMATION':row['error']='Python 运行失败；请查看实际错误输出。'
        except Exception as error:
            row['status']='CANCELLED' if s.cancelled or cancel() else 'FAILED';row['error']=scrub(str(error))[:1000]
        finally:
            if process:
                if process.poll() is None:process.kill()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:pass
                for stream in (process.stdin,process.stdout):
                    if stream:stream.close()
            self.processes.pop(id,None);s.inside_python=False
            if job:job.Close()
            if self.closed:row.update(status='INTERRUPTED',error='软件退出，Python 已停止；不会自动重放。')
            row['duration_ms']=round((time.monotonic()-started)*1000,1);row['finished_at']=now();self.save(row)
            s.output=row['output'] or row.get('error') or 'Python 已完成；实际操作以下方回执为准。'
        return row
    def close(self):
        self.closed=True
        self.grants.clear()
        for process in tuple(self.processes.values()):
            if process.poll() is None:process.kill()
        self.processes.clear()
    def cancel_children(self,s):
        for id in tuple(getattr(s,'spawned_tasks',())):
            if self.loop:asyncio.run_coroutine_threadsafe(s.manager.cancel(id),self.loop)
        for id in tuple(getattr(s,'control_children',())):
            child=self.center.sessions.get(id)
            if child and not child.cancelled:
                child.stop()
                if self.loop and child.task:asyncio.run_coroutine_threadsafe(child.manager.cancel(child.task.id),self.loop)

def routes(control):
    r=APIRouter(prefix='/api/control')
    @r.post('/run',status_code=202)
    async def run(b:Run):return control.start(b)
    @r.post('/director-note')
    def director_note(b:DirectorNote):
        run=control.get(b.project,b.run_id,b.persona)
        return control.center.app.state.creative_director.attach_analysis(b.project,b.record_id,b.etag,run,b.comment)
    @r.post('/grants',status_code=201)
    async def grant(b:Grant):return control.grant(b)
    @r.post('/call',status_code=202)
    async def call(request:Request,b:Call):return control.submit_call(control.authorized(request),b)
    @r.get('/calls/{id}')
    def call_result(request:Request,id:str):
        grant=control.authorized(request)
        if id not in {value[1] for value in grant['calls'].values()}:raise ConsoleError('调用不属于此授权',403)
        task=grant['session'].manager.get(id)
        return {'status':task.status,'result':(task.result or {}).get('control_result'),'error':task.error}
    @r.post('/revoke')
    def revoke(b:Reply):
        for token,grant in tuple(control.grants.items()):
            if grant['session'].id==b.token:grant['session'].stop();control.grants.pop(token,None)
        return {'revoked':True}
    @r.get('/history')
    def history(project:str,persona:Persona='assistant'):return {'runs':control.history(project,persona)}
    @r.get('/scripts')
    def scripts(project:str,persona:Persona='assistant'):
        return {'scripts':read(control.folder(project,persona)/'scripts.json',[])}
    @r.post('/scripts')
    def save(b:Script):
        path=control.folder(b.project,b.persona)/'scripts.json'
        with control.lock:
            rows=read(path,[]);id=b.id or 'script_'+uuid.uuid4().hex
            if b.id and not any(x['id']==b.id for x in rows):raise ConsoleError('脚本不属于当前角色和作品',404)
            row={**b.model_dump(),'id':id,'updated_at':now()};rows=[x for x in rows if x['id']!=id]+[row]
            if len(rows)>100:raise ConsoleError('每角色/作品最多保存 100 份脚本',422)
            atomic_json(path,rows)
        return row
    @r.get('/events')
    async def events(request:Request,project:str):
        control.center.app.state.registry.get(project)
        control.active_project=project
        control.loop=asyncio.get_running_loop();listener=asyncio.Queue(maxsize=1);control.listeners.add(listener)
        async def stream():
            try:
                while not control.closed and not await request.is_disconnected():
                    rows=[s.view() for s in tuple(control.center.sessions.values()) if s.id in control.owned and s.project==project and (not s.ended or s.pending)]
                    yield 'data: '+json.dumps({'sessions':rows},ensure_ascii=False)+'\n\n'
                    for _ in range(15):
                        try:await asyncio.wait_for(listener.get(),1);break
                        except asyncio.TimeoutError:
                            if control.closed or await request.is_disconnected():return
                    else:yield ': keepalive\n\n'
            finally:control.listeners.discard(listener)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-store'})
    return r
