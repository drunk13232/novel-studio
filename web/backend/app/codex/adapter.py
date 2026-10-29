"""The sole Codex integration boundary, using official Python SDK public APIs.

One SDK-owned process per active task; cancellation never kills other Codexes.
No browser-controlled commands, executables, environment, cwd or RPC methods.
"""
import json
import os
import re
import subprocess
import threading
import time
import uuid
from urllib.parse import urlsplit
from pathlib import Path
from typing import Any, Callable
from pydantic import BaseModel, ConfigDict
try:
    from openai_codex.client import CodexClient, CodexConfig
    from openai_codex import __version__ as SDK_VERSION
    from app.codex.windows import hide_sdk_console
    hide_sdk_console()
except ImportError:
    CodexClient = CodexConfig = None
    SDK_VERSION = 'unavailable'
from app.errors import CodexUnavailable
from app.codex.instructions import bundle, verify_thread_owner

Emit = Callable[[str, str, dict[str, Any] | None], None]
TEXT_BASE_INSTRUCTIONS='You are a text-only creative assistant. Follow the supplied developer role boundary. Use only selected request data. Do not use tools, read files, browse, delegate, or commit state. Return the requested response schema.'


class RPCResult(BaseModel):
    model_config = ConfigDict(extra='allow')


def redact(text: str) -> str:
    from app.ai.credentials import scrub
    text = scrub(str(text))
    text = re.sub(r'(?i)(Bearer\s+)[^\s"\']+', r'\1[REDACTED]', str(text))
    text = re.sub(r'\bsk-[A-Za-z0-9_-]{12,}\b', '[REDACTED]', text)
    text = re.sub(r'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED]', text)
    text = re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)["\']?\s*[:=]\s*["\']?)[^\s,"\'}]+', r'\1[REDACTED]', text)
    for name, value in os.environ.items():
        if any(k in name.upper() for k in ['API_KEY', 'ACCESS_TOKEN', 'REFRESH_TOKEN', 'SECRET']) and len(value) > 8:
            text = text.replace(value, '[REDACTED]')
    if os.environ.get('NOVEL_DEMO'):
        home=str(Path.home())
        text=text.replace(home,'[本机用户]').replace(home.replace('\\','/'),'[本机用户]')
    return text


def codex_binary() -> Path:
    configured = os.environ.get('NOVEL_CODEX_BIN')
    if configured:
        path = Path(configured)
    else:
        try:
            from codex_cli_bin import bundled_codex_path
            path = bundled_codex_path()
        except (ImportError, FileNotFoundError):
            raise CodexUnavailable('与 Python SDK 配套的 Codex 运行时缺失，请修复现有安装；未自动改用其他全局版本') from None
    if not path.is_file():
        raise CodexUnavailable('指定的 Codex CLI 不存在；请核对显式 NOVEL_CODEX_BIN，或使用 SDK 配套运行时')
    return path.resolve()


def codex_runtime_info() -> dict:
    from importlib.metadata import version, PackageNotFoundError
    try:expected=version('openai-codex-cli-bin')
    except PackageNotFoundError:expected=None
    path=codex_binary()
    return {'source':'EXPLICIT_OVERRIDE' if os.environ.get('NOVEL_CODEX_BIN') else 'SDK_BUNDLED','sdk_version':SDK_VERSION,'expected_cli_version':expected,'version_match':'UNVERIFIED' if os.environ.get('NOVEL_CODEX_BIN') else 'PINNED_PACKAGE','binary_present':path.is_file()}


def codex_environment() -> dict[str, str]:
    """Respect an already-enabled Windows loopback proxy for SDK child only.

    Never changes registry/user config, invents proxy endpoints, or disables TLS.
    Explicit environment settings take priority over registry discovery.
    """
    environment = dict(os.environ)
    if os.name != 'nt' or any(k.upper() == 'HTTPS_PROXY' for k in environment):
        return environment
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            enabled = winreg.QueryValueEx(key, 'ProxyEnable')[0]
            server = winreg.QueryValueEx(key, 'ProxyServer')[0]
        if not enabled or not isinstance(server, str): return environment
        if '=' in server:
            lanes = dict(segment.split('=', 1) for segment in server.split(';') if '=' in segment)
            server = lanes.get('https') or lanes.get('http') or ''
        parsed = urlsplit(server if '://' in server else 'http://' + server)
        if parsed.scheme != 'http' or parsed.hostname not in ['127.0.0.1', 'localhost'] or not parsed.port or parsed.username or parsed.password:
            return environment
        proxy = f'http://{parsed.hostname}:{parsed.port}'
        for name in ['HTTPS_PROXY', 'HTTP_PROXY', 'WSS_PROXY', 'WS_PROXY']:
            environment.setdefault(name, proxy)
        environment.setdefault('NO_PROXY', 'localhost,127.0.0.1,::1')
    except (OSError, ValueError):
        pass
    return environment


class CodexAdapter:
    def __init__(self, workspace: Path, engine: Path | None = None, role: str = 'AUTHOR', *, capsule: bool = False, reasoning_effort: str | None = None, model: str | None = None) -> None:
        self.workspace = workspace.resolve()
        self.capsule = capsule
        if reasoning_effort not in [None,"none","minimal","low","medium","high","xhigh","max","ultra"]:raise ValueError("Invalid reasoning effort")
        self.reasoning_effort = reasoning_effort
        self.model_id = model
        self.selected_ai = {'backend':'codex','provider_id':'codex','provider_name':'Codex 当前登录','model':model or 'CURRENT_LOGIN_MODEL','reasoning_effort':reasoning_effort}
        self.usage = None
        self.first_output_ms = None
        self.engine = (engine or workspace).resolve()
        if role not in ['WRITER', 'AUTHOR', 'CHECKER']: raise ValueError('Invalid context role')
        self.role = role
        self.instruction_evidence = None
        self.actual_model: str | None = None
        self.thread_id: str | None = None
        self.turn_id: str | None = None
        self._client: CodexClient | None = None
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self.request_id: str | None = None
        self.timings: list[dict[str, Any]] = []
        self._started = 0.0

    def _new_client(self) -> CodexClient:
        if CodexClient is None:
            raise CodexUnavailable('官方 openai-codex SDK 未安装，请运行项目安装脚本')
        runtime = self.engine / 'web/.runtime/codex'
        runtime.mkdir(parents=True, exist_ok=True)
        environment = codex_environment()
        # A standalone SDK app-server owns its own workspace/session routing.
        # Inheriting the desktop chat's IPC identity can time out before initialize.
        for key in ['CODEX_TASK_WORKSPACE_VERIFYING_IDENTITY','CODEX_APP_TOOLS_PIPE_PATH',
                    'CODEX_SESSION_ID','CODEX_THREAD_ID','CODEX_INTERNAL_ORIGINATOR_OVERRIDE']:
            environment.pop(key,None)
            # SDK 0.160.1 overlays config.env onto os.environ, rather than
            # replacing it. Removing from the overlay alone restores the
            # inherited desktop IPC identity. This standalone backend owns its
            # process; remove only those routing keys here, never user settings,
            # credentials, or the parent Codex application's environment.
            os.environ.pop(key,None)
        # Start-Process invokes venv Python directly without activating its PATH.
        # Existing Skills invoke `python`; expose only this project's interpreter.
        python_scripts = self.engine / 'web/backend/.venv/Scripts'
        if (python_scripts / 'python.exe').is_file():
            environment['PATH'] = str(python_scripts) + os.pathsep + environment.get('PATH', '')
        config = CodexConfig(codex_bin=str(codex_binary()), cwd=str(self.workspace),
            env=environment,
            client_name='novel_web_console', client_title='Novel Web Console', client_version='0.6.0',
            config_overrides=(f'log_dir={json.dumps(str(runtime))}', 'approval_policy="never"',
                              'sandbox_mode="workspace-write"',
                              'project_doc_max_bytes=0',
                              'shell_environment_policy.inherit="core"',
                              'shell_environment_policy.exclude=["*KEY*","*TOKEN*","*SECRET*"]') + (
                tuple('features.'+name+'=false' for name in ['plugins','apps','hooks','memories','multi_agent','tool_search','image_generation','view_image'])
                if self.capsule or self.role=='WRITER' else ()))
        # SDK's default accepts approval requests. Override explicitly and fail closed.
        return CodexClient(config, approval_handler=lambda method, params: {'decision': 'decline'})

    def health(self) -> dict[str, Any]:
        client: CodexClient | None = None
        timer = None
        authenticated = False
        expired = threading.Event()
        try:
            binary = codex_binary()
            process = subprocess.run([str(binary), '--version'], capture_output=True, text=True, timeout=10,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if process.returncode:
                raise CodexUnavailable('Codex --version 失败')
            client = self._new_client()
            def timeout_probe():
                expired.set();client.close()
            timer=threading.Timer(20,timeout_probe);timer.daemon=True;timer.start()
            client.start(); client.initialize()
            account = client.account_read().model_dump(mode='json')
            authenticated = account.get('account') is not None or not account.get('requiresOpenaiAuth', True)
            skill_result = client.request('skills/list', {'cwds': [str(self.workspace)], 'forceReload': True}, response_model=RPCResult).model_dump()
            skills = [s['name'] for row in skill_result.get('data', []) for s in row.get('skills', [])
                      if (s['name'].startswith('novel-') or s['name'] == 'web-novel-writing-skill') and s.get('enabled')]
            plugin_skills: list[str] = []
            unavailable: list[str] = []
            for market, name in [('sepia', 'sepia'), ('screenwriting-skills', 'screenwriting'), ('research-skill','research-codex'), ('novel-writing-stack','story-skills')]:
                marketplace = Path(os.environ['USERPROFILE']) / '.codex/.tmp/marketplaces' / market / '.agents/plugins/marketplace.json'
                if market=='novel-writing-stack': marketplace=self.engine/'docs/vendor/writing-stack/.agents/plugins/marketplace.json'
                try:
                    plugin = client.request('plugin/read', {'marketplacePath': str(marketplace), 'pluginName': name}, response_model=RPCResult).model_dump()['plugin']
                    if plugin['summary']['installed'] and plugin['summary']['enabled']:
                        plugin_skills += [s['name'] for s in plugin['skills'] if s['enabled']]
                    else:
                        unavailable.append(name)
                except Exception:
                    unavailable.append(name)
            account_type = (account.get('account') or {}).get('type', 'existing-provider')
            return {'codex': authenticated, 'reason': None if authenticated else 'Codex 未登录，请在本机终端执行 codex login',
                    'version': process.stdout.strip(), 'sdk_version': SDK_VERSION, 'runtime':{**codex_runtime_info(),'actual_cli_version':process.stdout.strip(),'version_match':'MATCH' if process.stdout.strip().split()[-1]==codex_runtime_info()['expected_cli_version'] else 'MISMATCH'}, 'integration': 'official-python-sdk / app-server stdio',
                    'authentication': account_type, 'project_skills': skills, 'plugin_skills': plugin_skills,
                    'unavailable_plugins': unavailable}
        except Exception as error:
            routing_failed = 'workspace routing discovery' in str(error).lower()
            return {'codex': authenticated, 'reason': ('Codex 账号工作区路由探测暂不可用；这不证明登录失效。可检查网络后手动重试；实际写作请求仍独立验证现有认证。' if routing_failed else 'Codex 状态探测超时；这不证明登录失效。软件助手会通过实际请求独立验证，可手动重试连接检查。' if expired.is_set() else 'Codex 进程内存不足；手动写作仍可用。请关闭不需要的应用后重试连接。' if 'memory allocation' in str(error).lower() else redact(str(error))[:1000]), 'probe_status':'ROUTING_UNAVAILABLE' if routing_failed else 'TIMEOUT' if expired.is_set() else 'FAILED', 'sdk_version': SDK_VERSION,
                    'project_skills': [], 'plugin_skills': [], 'unavailable_plugins': []}
        finally:
            if timer:timer.cancel()
            if client:
                client.close()

    def models(self):
        """On-demand official catalog; availability is verified only by a Turn."""
        client=self._new_client();expired=threading.Event()
        def stop():expired.set();client.close()
        timer=threading.Timer(25,stop);timer.daemon=True;timer.start()
        try:
            client.start();client.initialize()
            return client.request('model/list',{'limit':200,'includeHidden':False},response_model=RPCResult).model_dump(mode='json',by_alias=True)
        except Exception as error:
            raise CodexUnavailable('模型目录读取超时，可手动重试；现有设置保留' if expired.is_set() else '模型目录读取失败：'+redact(str(error))[:400]) from None
        finally:timer.cancel();client.close()

    def _step(self, phase: str, label: str, emit: Emit, operation):
        """Measure public SDK calls without retaining arguments, prompts or accounts."""
        begin = time.monotonic()
        meta = {'request_id': self.request_id, 'codex_phase': phase}
        emit('status', label, {**meta, 'phase_status': 'started'})
        try:
            value = operation()
        except Exception as error:
            row = {**meta, 'phase_status': 'failed',
                   'duration_ms': round((time.monotonic()-begin)*1000, 1),
                   'elapsed_ms': round((time.monotonic()-self._started)*1000, 1)}
            self.timings.append(row)
            emit('status', label+'失败', row)
            detail = redact(str(error))[:1200]
            if 'memory allocation' in str(error).lower() or 'out of memory' in str(error).lower():
                detail = 'Codex 子进程内存分配失败；已收到的草稿仍保留。请释放内存后从未完成步骤手动继续；这不证明登录失效，未自动重试或切换服务商。'
            elif 'workspace routing discovery' in str(error).lower():
                detail = 'Codex 工作区路由发现失败或超时；登录未被判定失效。请检查网络后手动重试；未自动重试或切换服务商。'
            raise CodexUnavailable(f'Codex {label}失败 [{phase}]：{detail}') from error
        row = {**meta, 'phase_status': 'completed',
               'duration_ms': round((time.monotonic()-begin)*1000, 1),
               'elapsed_ms': round((time.monotonic()-self._started)*1000, 1)}
        self.timings.append(row)
        emit('status', label+'完成', row)
        return value

    def start_task(self, prompt: str, emit: Emit, *, thread_id: str | None = None, read_only: bool = False, output_schema: dict | None = None, allow_web: bool = False) -> dict[str, Any]:
        if getattr(self,'prepare_controlled_prompt',None):prompt=self.prepare_controlled_prompt(prompt,output_schema)
        self.request_id = uuid.uuid4().hex
        self.timings = []
        self._started = time.monotonic()
        instructions, evidence = bundle(self.workspace, self.engine, self.role, self.capsule)
        self.instruction_evidence = evidence
        owners = self.engine / 'web/.runtime/thread-owners-v06'
        owners.mkdir(parents=True, exist_ok=True)
        if thread_id:
            if not re.fullmatch(r'[0-9a-f-]{36}', thread_id): raise ValueError('Invalid thread ID')
            verify_thread_owner(json.loads((owners/(thread_id+'.json')).read_text(encoding='utf8')),
                                self.workspace, self.role, thread_id)
        if self.role == 'WRITER' and thread_id:
            raise CodexUnavailable('Writer 每次使用新线程，不恢复旧上下文')
        client = self._new_client()
        with self._lock:
            self._client = client
        try:
            self._step('process_start', '启动连接', emit, client.start)
            self._step('initialize', '初始化 SDK', emit, client.initialize)
            # account/read also performs workspace-routing discovery in CLI
            # 0.160.0 and can fail before a usable Turn. Like the existing MCP
            # runner, verify authentication on the actual thread/Turn instead
            # of making a redundant network preflight block every writing task.
            # The explicit health probe still reports account/read separately.
            emit('status', '使用现有 Codex 认证；由本次实际请求验证',
                 {'request_id': self.request_id, 'authentication': 'REQUEST_PENDING'})
            mode = 'read-only' if read_only else 'workspace-write'
            params = {'cwd': str(self.workspace), 'sandbox': mode, 'approvalPolicy': 'never',
                      'runtimeWorkspaceRoots': [str(self.workspace)], 'developerInstructions': instructions}
            if self.capsule:
                # Text-only capsules already deliver their own role boundary.
                # Avoid the unrelated default coding-agent prompt and plugins;
                # do not change the normal file/Skills workflow integration.
                params['baseInstructions']=TEXT_BASE_INSTRUCTIONS
            if self.model_id:params['model']=self.model_id
            if self.workspace != self.engine:
                params.pop('sandbox')
                params['permissions'] = 'novel_isolated'
                # Closed read allowlist: no root/user-home grant, no inheritable
                # parent deny that makes AGENTS loading fail before thread creation.
                filesystem = {':minimal':'read', str(self.workspace):'read' if read_only else 'write'}
                if self.role != 'WRITER':
                    filesystem.update({str(self.engine/name):'read' for name in ['.agents','.novelforge','scripts','web/backend/.venv']})
                    shared_docs=['architecture-v0.1.md','workflow-v0.1.md','authoring-guide.md','reviewer-routing.md',
                                 'third-party-routing.md','context-builder-spec.md','plugin-inventory.md','skill-overlap-matrix.md']
                    filesystem.update({str(self.engine/'docs'/name):'read' for name in shared_docs})
                    # Only installed writing resources, never the Codex home/config.
                    from app.integrations.stack import installations
                    filesystem.update({str(p):'read' for p in installations(self.engine).values()})
                    plugin_cache=Path(os.environ['USERPROFILE'])/'.codex/plugins/cache'
                    for relative in ['sepia/sepia/0.12.3','screenwriting-skills/screenwriting/2.0.0']:
                        filesystem[str(plugin_cache/relative)]='read'
                params['config'] = {'project_doc_max_bytes':0, 'permissions': {'novel_isolated': {'filesystem': filesystem,
                    'network': {'enabled': allow_web}}}, 'memories': {'use_memories': False, 'generate_memories': False}}
                if allow_web: params['config']['web_search']='live'
                effective=self._step('config_read', '读取任务配置', emit, lambda: client.request('config/read',{},response_model=RPCResult)).model_dump()['config']
                self.actual_model=self.model_id or effective.get('model')
                servers=effective.get('mcp_servers') or {}
                params['config']['mcp_servers']={name:{'enabled':False} for name in servers}
                params['config']['features']={'apps':False,'js_repl':False,'multi_agent':False,'memories':False,'memory_tool':False}
                if self.reasoning_effort:params['config']['model_reasoning_effort']=self.reasoning_effort
                if self.role == 'WRITER' or self.capsule:
                    params['config']['features'].update(shell_tool=False, apply_patch_freeform=False)
                if self.capsule:params['config']['features'].update(plugins=False,hooks=False,tool_search=False,view_image=False,image_generation=False)
            discovered=self._step('skills_list', '发现项目指令', emit, lambda: client.request('skills/list',{'cwds':[str(self.workspace)],'forceReload':True},response_model=RPCResult)).model_dump()
            available={str(Path(s['path']).resolve()):s for row in discovered.get('data',[]) for s in row.get('skills',[]) if s.get('enabled')}
            required=[s for s in evidence['sources'] if s['kind']=='SKILL']
            missing=[s['path'] for s in required if str(Path(s['path']).resolve()) not in available]
            if missing: raise CodexUnavailable('项目 Skills 未进入 SDK 发现环境：'+', '.join(missing))
            evidence['skills_discovered']=[{'name':available[str(Path(s['path']).resolve())]['name'],**s} for s in required]
            # Deliver the actual selected skill bodies through the SDK request,
            # not merely a path the model may fail to open under Windows ACLs.
            selected=[s for s in required if self.role=='WRITER' or ('$'+Path(s['path']).parent.name) in prompt]
            for s in selected:
                params['developerInstructions']+='\n\n'+Path(s['path']).read_text(encoding='utf-8-sig')
            evidence['skills_delivered']=selected
            if thread_id:
                response = self._step('thread_resume', '恢复隔离线程', emit, lambda: client.request('thread/resume', {'threadId':thread_id,**params}, response_model=RPCResult))
                emit('status', '已恢复本控制台线程', {'resumed': True})
            else:
                response = self._step('thread_start', '创建隔离线程', emit, lambda: client.request('thread/start', params, response_model=RPCResult))
                emit('status', '已创建本控制台线程', {'resumed': False})
            # SDK 0.160.1's typed response drops experimental profile provenance.
            # Use its public request API with an extra-preserving response model.
            observed=response.model_dump(mode='json',by_alias=True)
            self.actual_model=observed.get('model') or self.actual_model
            self.selected_ai.update(request_model=self.model_id or self.actual_model,observed_model=self.actual_model,reasoning_effort=self.reasoning_effort)
            actual_cwd = observed['cwd']
            if Path(actual_cwd).resolve() != self.workspace:
                raise CodexUnavailable('Codex 返回的工作目录不匹配，任务已拒绝')
            active_profile=observed.get('activePermissionProfile')
            if self.workspace != self.engine and (active_profile or {}).get('id') != 'novel_isolated':
                raise CodexUnavailable('Codex 未确认项目隔离权限 profile，任务已拒绝')
            self.thread_id = observed['thread']['id']
            (owners/(self.thread_id+'.json')).write_text(json.dumps({'workspace':str(self.workspace),'role':self.role,'thread_id':self.thread_id}),encoding='utf8')
            evidence.update(thread_id=self.thread_id, actual_cwd=actual_cwd, permission_profile=active_profile,
                            delivery='SDK developerInstructions', accepted_by_app_server=True,
                            rollout_path=observed['thread'].get('path'))
            evidence_path=owners/(self.thread_id+'.instructions.json')
            evidence_path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
            emit('status','项目指令与 Skills 已由 SDK 接收',{'instruction_evidence':str(evidence_path),'role':self.role})
            emit('status', 'Codex 工作目录和线程就绪', {'thread_id': self.thread_id, 'workspace': str(self.workspace), 'sandbox': mode,'permission_profile':active_profile})
            if self._cancel.is_set():
                return {'status': 'interrupted', 'thread_id': self.thread_id}
            policy: dict[str, Any] = {'type': 'readOnly', 'networkAccess': allow_web} if read_only else {
                'type': 'workspaceWrite', 'writableRoots': [str(self.workspace)], 'networkAccess': False,
                'excludeSlashTmp': True, 'excludeTmpdirEnvVar': True}
            turn_params = {'cwd': str(self.workspace),
                'runtimeWorkspaceRoots': [str(self.workspace)], 'approvalPolicy': 'never', 'sandboxPolicy': policy}
            if self.workspace != self.engine:
                turn_params.pop('sandboxPolicy')
                turn_params['permissions'] = 'novel_isolated'
            if output_schema: turn_params['outputSchema'] = output_schema
            if self.model_id:turn_params['model']=self.model_id
            if self.reasoning_effort:turn_params['effort']=self.reasoning_effort
            self.selected_ai['effective_parameters']={k:turn_params[k] for k in ['model','effort'] if k in turn_params}
            emit('ai_request','本轮模型与参数已固定',self.selected_ai)
            turn = self._step('turn_start', '启动模型回合', emit, lambda: client.turn_start(self.thread_id, prompt, turn_params))
            self.turn_id = turn.turn.id
            emit('task_started', 'Codex Turn 已启动', {'thread_id': self.thread_id, 'turn_id': self.turn_id})
            if self._cancel.is_set():
                client.turn_interrupt(self.thread_id, self.turn_id)
            final_text = ''
            partial_text = ''
            while True:
                notification = client.next_turn_notification(self.turn_id)
                method = notification.method
                payload = notification.payload
                data = payload.model_dump(mode='json', by_alias=True) if isinstance(payload, BaseModel) else payload.params
                if getattr(self,'fail_fast_routing',False) and method=='error' and 'workspace routing discovery' in json.dumps(data).lower():
                    self._normalize(method,data,emit)
                    raise CodexUnavailable('Codex 工作区路由发现超时；已停止本次连接，未自动重新发起任务。登录未被判定失效，请稍后手动重试。')
                if method=='item/agentMessage/delta':partial_text+=data.get('delta','')
                if method=='item/agentMessage/delta' and self.first_output_ms is None:self.first_output_ms=round((time.monotonic()-self._started)*1000,1)
                if method=='thread/tokenUsage/updated':self.usage=data.get('tokenUsage')
                self._normalize(method, data, emit)
                if method == 'item/completed' and data.get('item',{}).get('type') == 'agentMessage':
                    final_text = data['item'].get('text','')
                if method == 'turn/completed':
                    result = data['turn']
                    self.selected_ai.update(usage=self.usage,first_output_ms=self.first_output_ms,duration_ms=round((time.monotonic()-self._started)*1000,1),status=result['status'])
                    return {'status': result['status'], 'thread_id': self.thread_id, 'turn_id': self.turn_id,
                            'error': redact((result.get('error') or {}).get('message', '')) or None, 'output': final_text or partial_text, 'model': self.actual_model,
                            'ai_metadata':dict(self.selected_ai)}
        finally:
            with self._lock:
                self._client = None
            client.close()

    @staticmethod
    def _normalize(method: str, data: dict[str, Any], emit: Emit) -> None:
        if method == 'item/agentMessage/delta':
            emit('message', redact(data.get('delta', '')), {'item_id': data.get('itemId')})
        elif method == 'item/reasoning/summaryTextDelta':
            emit('reasoning_summary', redact(data.get('delta', '')), None)
        elif method in ['item/commandExecution/outputDelta', 'item/mcpToolCall/progress']:
            emit('status', redact(data.get('delta') or data.get('message') or '')[:8000], {'stream': True, 'item_id': data.get('itemId')})
        elif method == 'item/started':
            item = data.get('item', {})
            if item.get('type') in ['commandExecution', 'mcpToolCall', 'fileChange', 'webSearch']:
                title = item.get('command') or item.get('tool') or item.get('type') or 'tool'
                emit('tool_call', redact(str(title))[:4000], {'item_type': item.get('type')})
        elif method == 'item/completed':
            item = data.get('item', {})
            if item.get('type') == 'fileChange':
                # Only root-relative workspace paths; never send raw SDK object/diff.
                paths = []
                for change in item.get('changes', []):
                    try:
                        paths.append(str(change['path']))
                    except (KeyError, TypeError):
                        continue
                emit('status', 'Codex 文件变更已完成', {'count': len(paths)})
        elif method == 'error':
            error = data.get('error') or {}
            text = error.get('message', 'Codex 返回错误')
            if error.get('additionalDetails'): text += '\n' + error['additionalDetails']
            emit('warning' if data.get('willRetry') else 'error', redact(text)[:2000], {'retrying': bool(data.get('willRetry'))})
        elif method in ['configWarning', 'deprecationNotice']:
            emit('warning', redact(data.get('message') or data.get('summary') or 'Codex 配置提示')[:1000], None)

    def interrupt(self) -> None:
        self._cancel.set()
        with self._lock:
            client = self._client
            thread_id, turn_id = self.thread_id, self.turn_id
        if client and thread_id and turn_id:
            try:
                client.turn_interrupt(thread_id, turn_id)
            except Exception:
                # SDK close terminates exactly its own child; no process-name kill.
                client.close()

    def steer(self, instruction: str) -> dict:
        """Official turn steering; does not restart a task or change permissions."""
        with self._lock:
            client=self._client;thread_id=self.thread_id;turn_id=self.turn_id
        if not client or not thread_id or not turn_id:raise CodexUnavailable('当前 Codex 回合尚未开始或已经结束；未重新提交任务')
        response=client.turn_steer(thread_id,turn_id,instruction)
        return response.model_dump(mode='json',by_alias=True)

    def close(self) -> None:
        self._cancel.set()
        with self._lock:
            client = self._client
        if client:
            client.close()

    def get_status(self) -> dict[str, Any]:
        try:runtime=codex_runtime_info()
        except CodexUnavailable:runtime={'source':'UNAVAILABLE','binary_present':False}
        return {'thread_id': self.thread_id, 'turn_id': self.turn_id, 'model': self.actual_model,'runtime':runtime}
