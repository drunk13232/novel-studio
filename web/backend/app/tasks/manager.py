import asyncio
import json
import uuid
import re
import os
from contextlib import nullcontext
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from app.codex.adapter import CodexAdapter, redact
from app.errors import ConsoleError
from app.models.requests import TaskRequest
from app.tasks.router import TaskRouter
from app.workspace.service import WorkspaceService
from app.tasks.storage import TaskStore,process_alive

TERMINAL = {'SUCCEEDED', 'FAILED', 'CANCELLED', 'INTERRUPTED'}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: str
    request: TaskRequest
    scope: str
    status: str = 'QUEUED'
    created_at: str = field(default_factory=now)
    started_at: str | None = None
    finished_at: str | None = None
    codex_thread_id: str | None = None
    turn_id: str | None = None
    error: str | None = None
    cancel_requested: bool = False
    files_changed: list[dict[str, str]] = field(default_factory=list)
    events: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=10000))
    event_sequence: int = 0
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    adapter: CodexAdapter | None = None
    runner: asyncio.Task[None] | None = None
    result: dict | None = None
    workspace: Any = None
    target: str | None = None
    reason: str | None = None
    provider: str | None = None
    skill: str | None = None
    private_text: bool = False
    ai_metadata: dict | None = None

    def public(self) -> dict[str, Any]:
        return {'id': self.id, 'type': self.request.type, 'chapter': self.request.chapter,
                'prompt': redact(self.request.prompt or ''), 'scope': self.scope, 'status': 'RUNNING' if self.status in TERMINAL and self.finished_at is None else self.status,
                'created_at': self.created_at, 'started_at': self.started_at, 'finished_at': self.finished_at,
                'codex_thread_id': self.codex_thread_id, 'turn_id': self.turn_id, 'error': self.error,
                'cancel_requested': self.cancel_requested, 'files_changed': self.files_changed, 'result': self.result,
                'project_id': self.workspace.name if self.workspace else None, 'target': self.target, 'reason': self.reason,
                'result_summary': str(self.result or '')[:500], 'provider': self.provider, 'skill': self.skill, 'ai_metadata':self.ai_metadata, 'private_text':self.private_text}


class TaskManager:
    def __init__(self, workspace: WorkspaceService, router: TaskRouter, engine=None, serial=None) -> None:
        self.workspace = workspace
        self.engine = engine or workspace.root
        self.router = router
        self.tasks: dict[str, Task] = {}
        self.threads: dict[str, str] = {}
        self._thread_file = workspace.root / 'web/.runtime/threads.json'
        if engine: self._thread_file = engine / 'web/.runtime/threads' / (workspace.root.name+'.json')
        try:
            stored = json.loads(self._thread_file.read_text(encoding='utf-8'))
            if stored.get('workspace') == str(workspace.root):
                self.threads = {scope: thread for scope, thread in stored.get('threads', {}).items()
                                if re.fullmatch(r'project-main|chapter-\d{3,5}(?:-[a-z_]+)?', scope)
                                and isinstance(thread, str) and re.fullmatch(r'[0-9a-f-]{36}', thread)}
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        self._serial = serial or asyncio.Semaphore(1)
        self._closed = False
        self.store = TaskStore(self.engine)
        for row in self.store.rows(workspace.root):
            if row['status'] not in TERMINAL and (row.get('owner_pid') is None or process_alive(row.get('owner_pid'))):continue
            if row.get('private_text') and row['request']['type']=='custom_prompt' and not row['request'].get('prompt'):row['request']['prompt']='普通 API 文本建议（未保存输入）'
            task=Task(row['id'],TaskRequest.model_validate(row['request']),row['scope'])
            for key in ['status','created_at','started_at','finished_at','codex_thread_id','turn_id','error','cancel_requested','files_changed','result','event_sequence','target','reason','provider','skill','private_text','ai_metadata']:
                if key in row: setattr(task,key,row[key])
            task.workspace=workspace.root
            task.events.extend(self.store.page(task.id,limit=200)['events']);self.tasks[task.id]=task

    def get(self, task_id: str) -> Task:
        if task_id not in self.tasks:
            raise ConsoleError('任务不存在或不属于此项目', 404)
        return self.tasks[task_id]

    def emit(self, task: Task, type_: str, message: str, data: dict[str, Any] | None = None) -> None:
        if task.cancel_requested and type_=='llm_delta':return
        task.event_sequence += 1
        safe_message = redact(message)
        event={'id': task.event_sequence, 'task_id': task.id, 'type': type_, 'timestamp': now(),
               'message': safe_message, 'data': json.loads(redact(json.dumps(data or {},ensure_ascii=False)))}
        task.events.append(event)
        if data and data.get('thread_id'):
            task.codex_thread_id = data['thread_id']
        if data and data.get('turn_id'):
            task.turn_id = data['turn_id']
        self.store.append(task,event)
        self.store.save(task)
        task.changed.set()

    def start(self, request: TaskRequest) -> Task:
        if self._closed:
            raise ConsoleError('服务正在停止', 503)
        from app.tasks.writer import WRITER_TASKS, prepare
        if request.type in WRITER_TASKS:
            try:return prepare(self,request)
            except (ValueError,OSError) as error:raise ConsoleError(str(error),409) from error
        prompt, read_only, scope = self.router.build(request)
        from app.tasks.reviews import REVIEW_TASKS, prepare as prepare_review
        if request.type in REVIEW_TASKS:
            return prepare_review(self,request,prompt,scope)
        return self.prepared(request,prompt,read_only,scope)

    def prepared(self, request, prompt, read_only, scope, output_schema=None, complete=None, target=None, *, execute=None, allow_web=False, provider=None, skill=None, adapter=None, ai_task=None, ai_model=None, application_actions=False, finished=None,orchestrator=False):
        if self._closed:
            raise ConsoleError('服务正在停止', 503)
        from app.tasks.writer import WRITER_TASKS
        if request.type in WRITER_TASKS and (adapter is None or adapter.role!='WRITER'):
            raise ConsoleError('Writer 任务必须经过安全包与独立执行环境',409)
        center=getattr(self,'ai_center',None)
        if center and not execute and not getattr(adapter,'metadata',None) and not getattr(adapter,'bound_ai_selection',False):
            llm=center.prepared(self,request,prompt,read_only,output_schema,adapter,ai_task,ai_model)
            if llm:adapter=llm;provider=llm.provider.display_name;skill='普通 LLM 文本；不执行 Skills'
        if getattr(adapter,'metadata',None):provider=adapter.provider.display_name;skill='普通 LLM 文本；不执行 Skills'
        if center and not execute:
            if adapter is None:adapter=CodexAdapter(self.workspace.root,self.engine,role='CHECKER' if any(v in request.type for v in ['review','check']) else 'AUTHOR')
            if not getattr(adapter,'request_controls',None):
                from app.ai.center import GROUPS
                group=ai_task or GROUPS.get(request.type) or 'workflow'
                if not getattr(adapter,'metadata',None):center.configure_codex(adapter,getattr(self,'ai_scope',self.workspace.root.name),group,request.options.ai_controls,ai_model)
        task = Task(uuid.uuid4().hex, request, scope)
        if getattr(adapter,'metadata',None):
            task.ai_metadata=adapter.metadata
            task.private_text=not center.settings().save_history if center else True
        elif getattr(adapter,'selected_ai',None):task.ai_metadata=adapter.selected_ai
        task.workspace=self.workspace.root;task.target=target;task.provider=provider;task.skill=skill
        task.adapter=adapter
        task.completion_notice=finished
        self.tasks[task.id] = task
        self.emit(task, 'status', '已排队；本地工作区任务按顺序执行，避免并发覆盖', {'status': task.status})
        if orchestrator and (not read_only or not application_actions):raise ConsoleError('仅受控只读编排可以等待子任务',403)
        task.runner = asyncio.create_task(self._run(task, prompt, read_only, output_schema, complete, execute, allow_web, application_actions,orchestrator))
        return task

    async def _run(self, task: Task, prompt: str, read_only: bool, output_schema=None, complete=None, execute=None, allow_web=False, application_actions=False,orchestrator=False) -> None:
        # Read-only orchestration may wait for children without holding their
        # queue; each domain write still uses the existing Action/file leases.
        async with (nullcontext() if orchestrator else self._serial):
            if task.status == 'CANCELLED':
                return
            if self._closed:
                await self.cancel(task.id)
                return
            loop = asyncio.get_running_loop()
            task.status = 'RUNNING'; task.started_at = now()
            self.emit(task, 'status', '正在运行：'+(task.provider or '本机 Codex'), {'status': task.status, 'provider': task.provider, 'skill': task.skill})
            role = 'CHECKER' if any(word in task.request.type for word in ['review','check','validate']) else 'AUTHOR'
            task.adapter = None if execute else task.adapter or CodexAdapter(self.workspace.root, self.engine,role=role)
            before = {}
            def emit(kind: str, message: str, data: dict[str, Any] | None) -> None:
                loop.call_soon_threadsafe(self.emit, task, kind, message, data)
            operation = None
            lease = None
            data_lease = None
            try:
                from app.tasks.lease import acquire
                lease = None if application_actions else acquire(self.engine)
                # Controlled app actions lock each domain mutation, not the UI acknowledgement wait.
                if not application_actions:
                    for attempt in range(40):
                        try:data_lease=acquire(self.engine,'studio-data.lock');break
                        except Exception:
                            if attempt==39:raise
                            await asyncio.sleep(.1)
                if not read_only and self.workspace.root.parent.name=='projects':
                    from app.library.storage import checkpoint
                    for row in self.workspace.list_files():
                        if row['path'].startswith(('chapters/','characters/','bible/','settings/','outlines/')):
                            await asyncio.to_thread(checkpoint,self.workspace.root,row['path'],'PRE_AI',task.id)
                before = {} if application_actions else await asyncio.to_thread(self.workspace.snapshot)
                # V0.6 starts fresh for every stage. Legacy and author/checker
                # histories must never become Writer history via a resume flag.
                kwargs = {'thread_id':None,'read_only':read_only}
                if output_schema: kwargs['output_schema']=output_schema
                if allow_web: kwargs['allow_web']=True
                operation = asyncio.create_task(asyncio.to_thread(execute,emit,lambda:task.cancel_requested)) if execute else asyncio.create_task(asyncio.to_thread(task.adapter.start_task, prompt, emit, **kwargs))
                result = await asyncio.wait_for(asyncio.shield(operation), task.request.options.timeout_seconds)
                task.ai_metadata=result.get('ai_metadata') or getattr(task.adapter,'metadata',None) or getattr(task.adapter,'selected_ai',None) or task.ai_metadata
                if getattr(self,'ai_center',None):
                    try:self.ai_center.observe(task.ai_metadata)
                    except Exception:self.emit(task,'warning','模型窗口信息无法缓存；本次真实结果仍保留，模型上限继续显示未知')
                if result.get('output') and (task.cancel_requested or result.get('status')!='completed'):
                    task.result={'partial_output':result['output'],'applied':False}
                if result.get('thread_id'):
                    task.codex_thread_id = result['thread_id']
                    self.threads[task.scope] = result['thread_id']
                    try:
                        self._thread_file.parent.mkdir(parents=True, exist_ok=True)
                        temporary = self._thread_file.with_suffix('.tmp')
                        temporary.write_text(json.dumps({'workspace': str(self.workspace.root), 'threads': self.threads}), encoding='utf-8')
                        os.replace(temporary, self._thread_file)
                    except OSError:
                        self.emit(task, 'warning', '线程映射无法保存，当前服务内仍可恢复；重启后需要新线程')
                task.turn_id = result.get('turn_id')
                if task.cancel_requested:
                    task.status='CANCELLED'
                elif result['status'] == 'completed':
                    task.result = await asyncio.to_thread(complete,result.get('output','')) if complete else {'output':result.get('output','')}
                    task.status = 'SUCCEEDED'
                elif result['status'] == 'interrupted':
                    task.status = 'CANCELLED'
                else:
                    task.status = 'FAILED'; task.error = result.get('error') or 'Codex Turn 未成功完成'
            except asyncio.TimeoutError:
                task.status = 'FAILED'; task.error = 'AI 任务超时，已中断对应执行；上游执行结果未知，请检查后手动重试'
                if task.adapter: await asyncio.to_thread(task.adapter.close)
                try: await asyncio.wait_for(operation, 10)
                except Exception: pass
            except Exception as error:
                task.status = 'CANCELLED' if task.cancel_requested else 'FAILED'
                task.error = None if task.cancel_requested else redact(str(error))[:2000]
            finally:
                if operation and not operation.done():
                    if task.adapter: await asyncio.to_thread(task.adapter.close)
                    try: await asyncio.wait_for(operation, 10)
                    except Exception: pass
                try:
                    task.files_changed = await asyncio.to_thread(self.workspace.changes, before) if before else []
                except Exception as error:
                    self.emit(task, 'warning', '文件变化检查失败：' + str(error))
                for change in task.files_changed:
                    self.emit(task, 'file_changed', change['path'], change)
                from app.tasks.lease import release
                release(lease)
                release(data_lease)
                task.finished_at = now()
                if self._closed:
                    task.status='INTERRUPTED';task.reason='backend_restart';task.error='后端关闭中断执行，需作者重新运行'
                if task.error: self.emit(task, 'error', task.error)
                if getattr(task,'completion_notice',None):
                    try:await asyncio.to_thread(task.completion_notice,task)
                    except Exception as error:self.emit(task,'warning','生成记录保存失败；已保留当前任务结果：'+redact(str(error))[:300])
                self.emit(task, 'task_cancelled' if task.status == 'CANCELLED' else 'task_completed',
                          '任务结束：' + task.status, {'status': task.status, 'files_changed': task.files_changed})

    async def cancel(self, task_id: str) -> Task:
        task = self.get(task_id)
        if task.status in TERMINAL:
            return task
        task.cancel_requested = True
        if task.status == 'QUEUED':
            task.status = 'CANCELLED'; task.finished_at = now()
            self.emit(task, 'task_cancelled', '排队任务已取消', {'status': task.status})
        elif task.adapter:
            self.emit(task, 'status', '正在请求中断当前 Task 的 Turn', None)
            try:
                await asyncio.wait_for(asyncio.to_thread(task.adapter.interrupt), 10)
            except asyncio.TimeoutError:
                await asyncio.to_thread(task.adapter.close)
                self.emit(task, 'warning', '中断确认超时，已关闭此 Task 的专属 Codex 进程')
        return task

    async def events(self, task_id: str, after: int) -> AsyncIterator[str]:
        task = self.get(task_id)
        while True:
            task.changed.clear()
            available = [event for event in task.events if event['id'] > after]
            if available and available[0]['id'] > after + 1:
                yield 'data: ' + json.dumps({'type': 'warning', 'message': '较旧事件已超过 10000 条保留上限'}, ensure_ascii=False) + '\n\n'
            for event in available:
                after = event['id']
                yield f'id: {after}\ndata: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
            if task.status in TERMINAL:
                break
            try:
                await asyncio.wait_for(task.changed.wait(), 12)
            except asyncio.TimeoutError:
                yield ': heartbeat\n\n'

    def stop_accepting(self) -> None:
        """Close admission immediately; close() still drains owned runners."""
        self._closed = True

    async def close(self) -> None:
        self.stop_accepting()
        tasks = list(self.tasks.values())
        errors = []
        # Cancel queued work before yielding to active interrupts. Releasing an
        # active task must not let queued work start while shutdown is draining.
        ordered = [t for t in tasks if t.status == 'QUEUED'] + [t for t in tasks if t.status != 'QUEUED']
        for task in ordered:
            if task.status in TERMINAL:
                continue
            try:
                await self.cancel(task.id)
            except BaseException as error:
                errors.append(error)
                # Same task-owned fallback as an interrupt timeout; never close
                # by process name or touch a different adapter/manager.
                if task.adapter:
                    try:
                        await asyncio.to_thread(task.adapter.close)
                    except BaseException as close_error:
                        errors.append(close_error)

        results = await asyncio.gather(*(t.runner for t in tasks if t.runner), return_exceptions=True)
        errors.extend(result for result in results
                      if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError))
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise BaseExceptionGroup('Owned task shutdown failed', errors)
