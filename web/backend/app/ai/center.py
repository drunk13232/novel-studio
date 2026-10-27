"""Text API routing over existing atomic preferences and TaskManager."""
import hashlib,json,threading,time,uuid
from datetime import datetime,timezone
from fastapi import APIRouter
from app.errors import ConsoleError
from app.tasks.storage import atomic_json
from app.library.storage import read
from app.ai.models import Provider,Preferences,SettingsUpdate,Secret,Test,Run,Confirm,TASKS,AGENT_ONLY,PRESETS,TASK_ALIASES
from app.ai.credentials import Credentials
from app.ai.provider import LLMProviderAdapter,normalize_url,endpoint,client,failure
from app.ai.controls import RequestControls,ControlSave,merge,build,item,receipt,estimate
GROUPS={'creation_interview':'interview','story_architect':'brainstorm','story_architect_refine':'brainstorm','world_expand':'world','character_create':'character','character_refine':'character','character_consistency_check':'review','character_difference_check':'review','master_outline_generate':'outline','volume_outline_generate':'outline','volume_outline_refine':'outline','chapter_skeleton_generate':'outline','chapter_cards_deepen':'outline','chapter_plan_refine':'outline','chapter_plan_review':'review'}
class AICenter:
    def __init__(self,root,registry,manager):
        self.root=root;self.registry=registry;self.manager=manager;self.lock=threading.RLock()
        self.credentials=Credentials(hashlib.sha256(str(root).casefold().encode()).hexdigest()[:20]);self.grants=set();self.challenges={}
    def settings(self):return Preferences.model_validate(read(self.root/'ai-settings.json',{}))
    def control_key(self,scope,project='',feature='',session=''):
        return json.dumps([scope,project,feature,session],separators=(',',':'))
    def controls_for(self,project,group,session='',overrides=None,model=None):
        s=self.settings();c=s.controls
        layers=[c.get(self.control_key('global')),c.get(self.control_key('project',project)),
                c.get(self.control_key('feature','',group)),c.get(self.control_key('feature',project,group)),
                c.get(self.control_key('session',project,group,session)) if session else None,
                overrides.model_dump(exclude_unset=True) if isinstance(overrides,RequestControls) else overrides]
        value=merge(*layers)
        if model:value['model']=model
        result=RequestControls.model_validate(value)
        result.model=result.model or self.selection(project,group)
        return result
    def selection(self,project,group,override=None):
        s=self.settings();r=s.projects.get(project,{});alias=TASK_ALIASES.get(group)
        return override or r.get(group) or s.routes.get(group) or (r.get(alias) if alias else None) or (s.routes.get(alias) if alias else None) or r.get('default') or s.default
    def check_control_scope(self,p):
        if p in {'','global'}:return
        if p in self.registry.rows:self.registry.get(p);return
        if p.startswith('draft_') and getattr(self,'drafts',None):self.drafts.get(p);return
        raise ConsoleError('模型控制作用域不属于已有作品或草稿',403)
    def put_controls(self,b):
        self.check_control_scope(b.project)
        if b.scope=='session' and not b.session:raise ConsoleError('会话设置需要稳定会话 ID',422)
        if b.scope=='global' and (b.project or b.session):raise ConsoleError('全局设置不能夹带作品或会话作用域',422)
        value=RequestControls.model_validate(b.value)
        if value.model:self.choose(b.project,b.feature,value.model)
        with self.lock:
            s=self.settings();s.controls[self.control_key(b.scope,b.project,b.feature if b.scope in {'feature','session'} else '',b.session if b.scope=='session' else '')]=b.value;self.save(s)
        return self.controls_for(b.project,b.feature,b.session).model_dump()
    def catalog(self):
        s=self.settings();rows=[]
        for m in s.codex_models:rows.append({**m,'ref':'codex::'+m['id'],'provider_id':'codex','provider_name':'Codex 当前登录','protocol':'codex','access':'CATALOG_NOT_ENTITLEMENT'})
        for p in s.providers:
            if not p.enabled:continue
            for m in p.available_models:rows.append({**m.model_dump(),'ref':p.provider_id+'::'+m.id,'provider_id':p.provider_id,'provider_name':p.display_name,'connection_status':p.connection_status})
        return {'models':rows,'codex_discovery':'ON_DEMAND','provider_defaults':s.default}
    def discover_codex(self):
        from app.codex.adapter import CodexAdapter
        result=CodexAdapter(self.registry.engine).models();rows=[]
        for r in result.get('data',[]):
            rows.append({'id':r.get('model') or r['id'],'display_name':r.get('displayName') or r['id'],
              'reasoning_levels':[v['reasoningEffort'] for v in r.get('supportedReasoningEfforts',[])],
              'default_reasoning_effort':r.get('defaultReasoningEffort'),'context_length':r.get('contextWindow'),
              'output_limit':r.get('maxOutputTokens'),'capabilities':{'reasoning':bool(r.get('supportedReasoningEfforts')),'streaming':True,'vision':'image' in r.get('inputModalities',[])},
              'capability_source':'OFFICIAL_METADATA','is_default':bool(r.get('isDefault')),'favorite':False})
        if not rows:raise ConsoleError('Codex 返回了空模型目录；已保留原有目录和选择，请稍后手动重试',503)
        with self.lock:
            s=self.settings();favorites={r['id'] for r in s.codex_models if r.get('favorite')}
            for row in rows:row['favorite']=row['id'] in favorites
            s.codex_models=rows;self.save(s)
        return self.catalog()
    def configure_codex(self,a,project,group,controls=None,model=None):
        c=self.controls_for(project,group,overrides=controls,model=model)
        if c.model!='codex' and not c.model.startswith('codex::'):raise ConsoleError('当前执行器与选定 Provider 不一致，未跨服务商回退',409)
        selected=c.model.split('::',1)[1] if '::' in c.model else None
        effort=c.parameters.get('reasoning_effort')
        if c.max_cost:raise ConsoleError('Codex 登录用量没有可核对的 API 单价，无法执行参考费用上限；请清除此限制',422)
        row=next((m for m in self.settings().codex_models if m['id']==selected),None)
        if effort and (not row or effort not in row.get('reasoning_levels',[])):raise ConsoleError('请先读取 Codex 模型目录，并选择该模型真实支持的思考档位',422)
        invalid={k:v for k,v in c.parameters.items() if v is not None and k not in {'reasoning_effort','timeout','streaming'}}
        if invalid:raise ConsoleError('Codex SDK 未提供这些普通 API 生成参数：'+', '.join(invalid)+'；未发送伪控制',422)
        a.model_id=selected;a.reasoning_effort=effort
        a.selected_ai={'backend':'codex','provider_id':'codex','provider_name':'Codex 当前登录','model':selected or 'CURRENT_LOGIN_MODEL','reasoning_effort':effort,'task_type':group}
        self.attach_controls(a,c,row)
        return a
    def attach_controls(self,a,c,model=None):
        a.request_controls=c
        a.control_model=model.model_dump() if hasattr(model,'model_dump') else model or {}
        a.prepare_controlled_prompt=lambda prompt,output_schema=None:self.control_prompt(a,prompt,output_schema,getattr(a,'source_items',None))
        return a
    def control_prompt(self,a,prompt,output_schema=None,packet=None):
        c=getattr(a,'request_controls',None)
        if c is None:return prompt
        overhead=estimate(json.dumps(output_schema,ensure_ascii=False)) if output_schema else 0
        if not hasattr(a,'metadata'):
            from app.codex.instructions import bundle
            instructions,evidence=bundle(a.workspace,a.engine,a.role,a.capsule);overhead+=estimate(instructions)
            if a.capsule:
                from app.codex.adapter import TEXT_BASE_INSTRUCTIONS
                overhead+=estimate(TEXT_BASE_INSTRUCTIONS)
            for s in evidence['sources']:
                if s['kind']=='SKILL' and (a.role=='WRITER' or '$'+__import__('pathlib').Path(s['path']).parent.name in prompt):overhead+=estimate(__import__('pathlib').Path(s['path']).read_text(encoding='utf8'))
        output=c.parameters.get('max_output_tokens') or (getattr(a,'params',None).max_output_tokens if getattr(a,'params',None) else None)
        if packet:
            value=build(packet,c.context,a.control_model.get('context_length'),output,overhead)
            prompt=value['prompt']
        else:
            value=build([item('task','task','当前任务与已授权资料',prompt,required=True)],c.context,a.control_model.get('context_length'),output,overhead)
            # Preserve business prompt byte-for-byte for existing parsers/Skills.
            value['prompt']=prompt;value['prompt_sha256']=hashlib.sha256(prompt.encode()).hexdigest()
            value['input_estimate']=estimate(prompt)+overhead
        meta=getattr(a,'metadata',None) or a.selected_ai
        meta.update(controls=c.model_dump(),context=receipt(value))
        a.context_preview=value;a.controlled_prompt=prompt
        return prompt
    def authorize(self,a,prompt):
        if not getattr(a,'metadata',None):return
        c=a.request_controls;p=a.provider;m=a.model
        self.enforce_budget(p,m,prompt,a.params)
        if c.max_cost:
            if m.input_price is None or m.output_price is None or not a.params.max_output_tokens:raise ConsoleError('单次费用上限需要价格与有效输出上限，尚未发送请求',409)
            if (estimate(prompt)*m.input_price+a.params.max_output_tokens*m.output_price)/1000000>c.max_cost:raise ConsoleError('实际准备的上下文参考费用超过本次上限，尚未发送',429)
        a.key=self.key(p);self.notice(p,a.project,a.task_type,prompt,m)
    def observe(self,metadata):
        """Cache only the actual returned window, never infer account entitlement."""
        if not metadata or metadata.get('backend')!='codex':return
        window=(metadata.get('usage') or {}).get('modelContextWindow');model=metadata.get('observed_model')
        if not model or type(window) is not int or not 0<window<=2000000:return
        with self.lock:
            s=self.settings()
            for m in s.codex_models:
                if m['id']==model:m.update(context_length=window,context_source='REQUEST_OBSERVED',context_observed_at=datetime.now(timezone.utc).isoformat())
            self.save(s)
    def save(self,value):atomic_json(self.root/'ai-settings.json',value.model_dump())
    def provider(self,id):
        row=next((p for p in self.settings().providers if p.provider_id==id),None)
        if not row:raise ConsoleError('API 配置不存在',404)
        return row
    def view(self):
        value=self.settings().model_dump()
        for p in value['providers']:
            p['credential_status']=self.credentials.status(p.pop('credential_reference'));p['agent_status']='UNVERIFIED：普通 API 不具备 Codex 文件与 Skills 权限'
        return {**value,'presets':PRESETS,'task_types':TASKS,'credential_available':self.credentials.backend is not None,'codex':{'display_name':'Codex 当前登录','backend':'agent'}}
    def put(self,body):
        with self.lock:
            s=self.settings();old=next((p for p in s.providers if p.provider_id==body.provider_id),None)
            body.base_url=normalize_url(body.base_url);body.credential_reference=old.credential_reference if old else None
            if old and (old.base_url!=body.base_url or old.auth_header!=body.auth_header):
                if old.credential_reference:self.credentials.delete(old.credential_reference)
                body.credential_reference=None
            body.connection_status=old.connection_status if old and old.base_url==body.base_url and old.protocol==body.protocol else 'UNVERIFIED'
            if body.provider_id=='codex':raise ConsoleError('Codex 由原有 Agent 管理，不能覆盖',422)
            if len({m.id for m in body.available_models})!=len(body.available_models) or any('::' in m.id for m in body.available_models):raise ConsoleError('模型 ID 重复或包含不支持的 ::',422)
            if body.default_model and body.default_model not in {m.id for m in body.available_models}:raise ConsoleError('默认模型未配置',422)
            for m in body.available_models:
                if m.capability_source=='UNKNOWN' and (m.reasoning_levels or any(v is not None for v in m.capabilities.values())):m.capability_source='USER'
            s.providers=[p for p in s.providers if p.provider_id!=body.provider_id]+[body];self.save(s)
        return self.view()
    def remove(self,id):
        with self.lock:
            p=self.provider(id)
            if p.credential_reference:self.credentials.delete(p.credential_reference)
            s=self.settings();s.providers=[x for x in s.providers if x.provider_id!=id];prefix=id+'::'
            if s.default.startswith(prefix):s.default='codex'
            s.routes={k:v for k,v in s.routes.items() if not v.startswith(prefix)};s.projects={k:{a:b for a,b in v.items() if not b.startswith(prefix)} for k,v in s.projects.items()};self.save(s)
        return self.view()
    def secret(self,id,body=None):
        with self.lock:
            s=self.settings();p=self.provider(id);ref=p.credential_reference or uuid.uuid4().hex
            if body:self.credentials.put(ref,body.key,body.session_only);p.credential_reference=ref
            elif p.credential_reference:self.credentials.delete(ref);p.credential_reference=None
            p.connection_status='UNVERIFIED';s.providers=[p if x.provider_id==id else x for x in s.providers];self.save(s)
        return self.credentials.status(p.credential_reference)
    def choose(self,project,group,override=None):
        if group not in TASKS:raise ConsoleError('未知写作任务类型',422)
        s=self.settings();r=s.projects.get(project,{})
        alias=TASK_ALIASES.get(group)
        ref=self.selection(project,group,override)
        if group in AGENT_ONLY:
            if ref!='codex' and not ref.startswith('codex::'):raise ConsoleError('文件、State 与复杂章节工作流必须使用 Codex Agent',422)
            return None,None
        if ref=='codex' or ref.startswith('codex::'):return None,None
        try:id,model=ref.split('::',1)
        except ValueError:raise ConsoleError('模型选择格式错误',422) from None
        p=self.provider(id)
        if not p.enabled:raise ConsoleError('服务商已禁用，请手动选择可用模型',409)
        m=next((m for m in p.available_models if m.id==model),None)
        if not m:raise ConsoleError('所选模型已删除或未配置',409)
        return p,m
    def update(self,body):
        with self.lock:
            s=self.settings()
            for k,v in body.model_dump().items():setattr(s,k,v)
            if any(k not in TASKS for k in s.routes):raise ConsoleError('未知任务路由',422)
            for p,r in s.projects.items():
                if p not in self.registry.rows or any(k not in TASKS and k!='default' for k in r):raise ConsoleError('项目路由超出已有小说范围',403)
            allowed={'codex',*['codex::'+m['id'] for m in s.codex_models],*[p.provider_id+'::'+m.id for p in s.providers for m in p.available_models]}
            for r in [s.routes,*s.projects.values(),{'default':s.default}]:
                if any(v not in allowed or k in AGENT_ONLY and not (v=='codex' or v.startswith('codex::')) for k,v in r.items()):raise ConsoleError('模型路由不存在或不支持工程任务',422)
            if any(k not in {'request','day','month'} or v<0 for k,v in s.budgets.items()):raise ConsoleError('预算提醒格式错误',422)
            self.save(s)
        return self.view()
    def key(self,p):
        key=self.credentials.get(p.credential_reference)
        if not key and not endpoint(p.base_url)[3]:raise ConsoleError('远端 API 尚未配置密钥',401)
        return key
    def notice(self,p,project,category,prompt,model):
        if endpoint(p.base_url)[3]:return
        signature=(p.provider_id,p.base_url,project,category);digest=hashlib.sha256(prompt.encode()).hexdigest();binding=(signature,digest);budgets=self.budget_notices()
        if signature in self.grants and not budgets or binding in self.grants:return
        token=uuid.uuid4().hex;self.challenges[token]=(time.monotonic(),signature,binding)
        error=ConsoleError('请确认本次远端资料发送范围与费用提醒',409)
        error.ai_notice={'token':token,'provider':p.display_name,'host':p.base_url,'model':model.id,'project':project,'categories':category,'budget':budgets,'message':'仅发送本次选取的文本和必要角色包；普通 API 无文件权限，生成可能计费。'};raise error
    def confirm(self,token):
        c=self.challenges.pop(token,None)
        if not c or time.monotonic()-c[0]>600:raise ConsoleError('确认已过期，请重新发起',409)
        self.grants.update([c[1],c[2]]);return {'confirmed':True}
    def enforce_budget(self,p,m,prompt,params=None):
        s=self.settings()
        if s.budget_policy!='block':return
        rows=read(self.root/'ai-usage.json',[]);stamp=datetime.now(timezone.utc).isoformat()
        for unit,length in [('day',10),('month',7)]:
            limit=s.budgets.get(unit)
            if not limit:continue
            selected=[r for r in rows if r.get('at','')[:length]==stamp[:length] and r.get('currency')==s.budget_currency]
            if any(r.get('cost_estimate') is None for r in selected):raise ConsoleError('存在未知费用记录，无法核对预算；请检查账单或明确改为提醒模式',409)
            if sum(r['cost_estimate'] for r in selected)>=limit:raise ConsoleError('客户端参考预算已达到限制，本次请求未发送',429)
        limit=s.budgets.get('request')
        if limit:
            parameters=params or m.parameters;maximum=parameters.max_output_tokens
            if m.currency!=s.budget_currency or m.input_price is None or m.output_price is None or maximum is None or (m.protocol=='chat' and m.chat_token_parameter is None):raise ConsoleError('缺少同币种价格或已支持的输出上限，无法预检查单次预算；本次请求未发送',409)
            # Conservative client estimate, not an exact tokenizer or provider bill.
            estimate=(len(prompt.encode('utf8'))*m.input_price+maximum*m.output_price)/1000000
            if estimate>limit:raise ConsoleError('客户端事前估算超过单次预算，本次请求未发送；此估算不能替代官方费用上限',429)

    def adapter(self,project,group,prompt,override=None,params=None,role='AUTHOR',controls=None,preview=False):
        c=self.controls_for(project,group,overrides=controls,model=override)
        p,m=self.choose(project,group,c.model)
        if p is None:return None
        from app.ai.models import Parameters
        from app.ai.parameters import request_arguments
        params=Parameters.model_validate(merge(m.parameters.model_dump(),c.parameters,params.model_dump(exclude_unset=True) if params else None))
        if c.parameters.get('streaming') is True and m.capabilities.get('streaming') is False:raise ConsoleError('所选模型已确认不支持流式输出；请使用非流式或模型默认',422)
        request_arguments(p,m,params)
        if c.max_cost and not preview:
            if m.input_price is None or m.output_price is None or not params.max_output_tokens:raise ConsoleError('单次费用上限需要已配置价格和有效最大输出；请求未发送',409)
            cost=(estimate(prompt)*m.input_price+params.max_output_tokens*m.output_price)/1000000
            if cost>c.max_cost:raise ConsoleError('保守参考费用估算超过本次上限；请求未发送',429)
        if not preview:self.enforce_budget(p,m,prompt,params)
        key=None if preview else self.key(p)
        if not preview:self.notice(p,project,group,prompt,m)
        a=LLMProviderAdapter(p,m,key,self.record,group,project,params,role)
        self.attach_controls(a,c,m)
        return a
    def prepared(self,manager,request,prompt,read_only,schema,adapter,group=None,override=None):
        group=group or GROUPS.get(request.type)
        if not group or not read_only or not schema:return None
        return self.adapter(getattr(manager,'ai_scope',manager.workspace.root.name),group,prompt,override,role=getattr(adapter,'role','AUTHOR'),controls=request.options.ai_controls)
    def record(self,p,m,project,group,status,duration,tokens,error):
        inp=tokens.get('input_tokens',tokens.get('prompt_tokens'));out=tokens.get('output_tokens',tokens.get('completion_tokens'))
        cost=(inp*m.input_price+out*m.output_price)/1000000 if inp is not None and out is not None and m.input_price is not None and m.output_price is not None else None
        row={'id':uuid.uuid4().hex,'at':datetime.now(timezone.utc).isoformat(),'project':project,'task':group,'provider':p.provider_id,'model':m.id,'status':status,'input_tokens':inp,'output_tokens':out,'cost_estimate':cost,'currency':m.currency,'seconds':round(duration,3),'error':error}
        with self.lock:atomic_json(self.root/'ai-usage.json',([row]+read(self.root/'ai-usage.json',[]))[:10000])
    def budget_notices(self):
        s=self.settings();rows=read(self.root/'ai-usage.json',[]);now=datetime.now(timezone.utc).isoformat();alerts=[]
        for unit,length in [('day',10),('month',7)]:
            spent=sum(r.get('cost_estimate') or 0 for r in rows if r.get('at','')[:length]==now[:length] and r.get('currency')==s.budget_currency)
            if s.budgets.get(unit) and spent>=s.budgets[unit]:alerts.append(f'{unit}：参考费用已达 {spent:.4f} {s.budget_currency}，以提供商账单为准。')
        if s.budgets.get('request'):alerts.append('单次提醒阈值 '+str(s.budgets['request'])+' '+s.budget_currency+'；实际费用在 Usage 返回后估算，无法保证服务商扣费上限。')
        return alerts
    def models(self,id):
        p=self.provider(id);c=None
        try:
            c=client(p,self.key(p),min(20,p.timeout));response=c.models.list()
            rows=[]
            from urllib.parse import urlsplit
            trusted=urlsplit(p.base_url).hostname in {'api.deepseek.com','api.openai.com'}
            for m in response.data[:2000]:
                raw=m.model_dump();value={'id':m.id}
                config={'id':m.id,'protocol':p.protocol}
                if isinstance(raw.get('display_name'),str):config['display_name']=raw['display_name'][:120]
                if trusted:
                    for field,source in [('context_length','context_window'),('output_limit','max_output_tokens')]:
                        if type(raw.get(source)) is int and raw[source]>0:config[field]=raw[source]
                    levels=(raw.get('effort') or {}).get('supported_levels',[])
                    if levels and all(v in {'none','minimal','low','medium','high','xhigh','max','ultra'} for v in levels):
                        config['reasoning_levels']=levels;config['capabilities']={'reasoning':True}
                    if len(config)>2:config['capability_source']='OFFICIAL_METADATA'
                value['configuration']=config;rows.append(value)
            return {'status':'MODELS_OK','models':rows}
        except Exception as e:
            status=getattr(e,'status_code',None)
            return {'status':'LIST_UNSUPPORTED' if status in {404,405,501} else 'AUTH_FAILED' if status in {401,403} else 'NETWORK_OR_SERVER_ERROR','message':failure(e),'models':[],'manual_allowed':True}
        finally:
            if c:c.close()
    def test(self,id,body):
        if not body.confirm_cost:raise ConsoleError('实际生成测试可能计费，请先勾选费用提示',422)
        from app.ai.models import Parameters
        from app.ai.provider import failure_kind
        warnings=[]
        try:
            p=self.provider(id);m=next((m for m in p.available_models if m.id==body.model),None)
            if not p.enabled:raise ConsoleError('服务商已禁用，请启用后再测试',422)
            if not m:raise ConsoleError('先填写并保存模型 ID',422)
            # A known cap is small; unknown optional mappings are omitted, never guessed.
            cap=min(16,m.output_limit or 16) if m.protocol=='responses' or m.chat_token_parameter else None
            if cap is None:warnings.append('此 Chat 模型输出上限映射 UNKNOWN，本次省略可选长度参数；服务商可能按默认上限计费。')
            a=LLMProviderAdapter(p,m,self.key(p),self.record,'connection_test','settings',Parameters(streaming=False,timeout=20,max_output_tokens=cap))
            result=a.start_task('Reply only OK.',lambda *args:None)
        except ConsoleError as e:
            result={'status':'failed','error':str(e),'error_category':failure_kind(e),'stage':'configuration'}
        ok=result['status']=='completed';category='TEXT_GENERATION_OK' if ok else result.get('error_category') or 'INVALID_RESPONSE'
        with self.lock:
            s=self.settings()
            for row in s.providers:
                if row.provider_id==id:row.connection_status=category
            self.save(s)
        return {'status':result['status'],'category':category,'stage':result.get('stage','request'),'message':'最小文本请求成功；Agent 能力仍未验证' if ok else result['error'],'warnings':warnings,'agent_status':'UNVERIFIED'}
    def reply_language(self,project):
        from app.studio import Preferences as UIPreferences
        pref=UIPreferences.model_validate(read(self.root/'preferences.json',{}))
        if pref.ai_response_language!='project':return pref.ai_response_language
        if project in self.registry.rows:return self.registry.get(project).get('language','zh-CN')
        return 'zh-CN'

    def run(self,p,body):
        self.registry.get(p)
        if body.task not in TASKS or body.task in AGENT_ONLY:raise ConsoleError('请通过原有 Codex 工作流执行',422)
        from app.models.requests import TaskRequest,TaskOptions
        prompt='你是小说创作文本助手。只提供候选或建议，不执行文件、工具、State 操作。不补造未提供的事实。\n任务：'+TASKS[body.task]+'\n作者要求：'+body.instruction+'\n作者本次明确选取的文本：\n'+body.text
        prompt+='\nUse '+self.reply_language(p)+' for explanations. Keep revision candidates in the language of the selected text. UI language is unrelated; never translate names or references automatically.'
        from app.creative.tasks import adapter
        a=adapter(self,p,body.task,prompt,body.model,parameters=body.parameters,role='CHECKER' if body.task=='review' else 'AUTHOR')
        timeout=a.params.timeout if getattr(a,'params',None) else a.request_controls.parameters.get('timeout',600)
        req=TaskRequest(type='custom_prompt',prompt='只读文本候选',options=TaskOptions(read_only=True,resume=False,timeout_seconds=max(30,timeout)))
        task=self.manager(p).prepared(req,prompt,True,'llm-'+uuid.uuid4().hex,adapter=a,ai_task=body.task,provider=a.provider.display_name if getattr(a,'provider',None) else 'Codex',skill='只读文本候选；不执行文件操作',application_actions=True)
        task.private_text=not self.settings().save_history
        return task.public()

def ai_routes(center):
    r=APIRouter(prefix='/api/ai')
    @r.get('/settings')
    def view():return center.view()
    @r.get('/catalog')
    def catalog():return center.catalog()
    @r.post('/favorite')
    def favorite(body:dict):
        if set(body)!={'model','favorite'} or not isinstance(body['favorite'],bool):raise ConsoleError('收藏参数无效',422)
        with center.lock:
            s=center.settings();found=False
            for m in s.codex_models:
                if body['model']=='codex::'+m['id']:m['favorite']=body['favorite'];found=True
            for p in s.providers:
                for m in p.available_models:
                    if body['model']==p.provider_id+'::'+m.id:m.favorite=body['favorite'];found=True
            if not found:raise ConsoleError('模型不存在',404)
            center.save(s)
        return {'saved':True}
    @r.post('/codex/models')
    def codex_models():return center.discover_codex()
    @r.get('/controls')
    def controls(project:str='',feature:str='brainstorm',session:str=''):
        center.check_control_scope(project)
        return center.controls_for(project,feature,session).model_dump()
    @r.put('/controls')
    def put_controls(body:ControlSave):return center.put_controls(body)
    @r.get('/control-presets')
    def control_presets():return center.settings().control_presets
    @r.put('/control-presets/{name}')
    def preset(name:str,body:RequestControls):
        if not name.strip() or len(name)>100:raise ConsoleError('预设名称需为 1～100 字符',422)
        with center.lock:
            s=center.settings();s.control_presets[name]=body.model_dump(exclude_unset=True);center.save(s)
        return s.control_presets
    @r.put('/settings')
    def settings(body:SettingsUpdate):return center.update(body)
    @r.put('/providers')
    def put(body:Provider):return center.put(body)
    @r.delete('/providers/{id}')
    def remove(id:str):return center.remove(id)
    @r.post('/providers/{id}/clone')
    def clone(id:str):
        p=center.provider(id);p.provider_id='provider_'+uuid.uuid4().hex;p.display_name+=' 副本';p.credential_reference=None;p.connection_status='UNVERIFIED';return center.put(p)
    @r.put('/providers/{id}/credential')
    def secret(id:str,body:Secret):return center.secret(id,body)
    @r.delete('/providers/{id}/credential')
    def delete_key(id:str):return center.secret(id)
    @r.get('/providers/{id}/credential')
    def status(id:str):return center.credentials.status(center.provider(id).credential_reference)
    @r.post('/providers/{id}/models')
    def models(id:str):return center.models(id)
    @r.post('/providers/{id}/test')
    def test(id:str,body:Test):return center.test(id,body)
    @r.post('/confirm')
    def confirm(body:Confirm):return center.confirm(body.token)
    @r.get('/usage')
    def usage():return {'rows':read(center.root/'ai-usage.json',[]),'notices':center.budget_notices(),'estimate_only':True}
    @r.post('/projects/{p}/tasks',status_code=202)
    async def run(p:str,body:Run):return center.run(p,body)
    return r

def backup_settings(value,scope):
    s=Preferences.model_validate(value)
    for p in s.providers:p.credential_reference=None;p.connection_status='UNVERIFIED'
    controls={}
    for key,v in s.controls.items():
        try:kind,project,feature,session=json.loads(key)
        except (ValueError,TypeError):continue
        if project in {'',scope}:controls[key]=v
    s.controls=controls
    s.projects={scope:s.projects[scope]} if scope in s.projects else {};s.save_history=False
    return s.model_dump()
