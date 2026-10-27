"""Bounded creative delegation over existing Writer contexts, TaskManager and Providers.
Records are project-local candidate metadata, never a story fact or a second task queue.
"""
import json,re,time,threading
from datetime import datetime
from typing import Literal,Annotated
from fastapi import APIRouter
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.library.storage import read,write,uid,now,digest
from app.studio_tools import normalized,text_hash,utf16_slice,utf16_index
from app.models.requests import TaskRequest,TaskOptions
from app.tasks.manager import TERMINAL
from app.projects.foundation import schema
from app.ai.models import Parameters
from app.ai.controls import RequestControls,merge
from .tasks import adapter,metadata
from .director_skills import catalog,load

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Limits(Strict):
    max_calls:int=Field(default=6,ge=1,le=8)
    seconds:int=Field(default=600,ge=30,le=1800)
    output_characters:int=Field(default=16000,ge=100,le=32000)
    output_tokens:int=Field(default=4096,ge=64,le=16000)
    api_budget:float|None=Field(default=None,gt=0,le=1000)
    currency:str=Field(default='USD',pattern=r'^[A-Z]{3}$')
class Step(Strict):
    title:str=Field(min_length=1,max_length=120)
    instruction:str=Field(min_length=1,max_length=2500)
    checks:list[str]=Field(default_factory=list,max_length=8)
    enabled:bool=True
    needs_author:bool=False
    exit_condition:str=Field(default='',max_length=800)
    deferred_outcomes:list[Annotated[str,Field(min_length=1,max_length=400)]]=Field(default_factory=list,max_length=6)

class Plan(Strict):
    summary:str=Field(min_length=1,max_length=1500)
    steps:list[Step]=Field(min_length=1,max_length=4)
    questions:list[str]=Field(default_factory=list,max_length=4)
    methods:list[str]=Field(default_factory=list,max_length=4)
    method_application:list[str]=Field(default_factory=list,max_length=4)
    recommended_executor:str|None=Field(default=None,max_length=300)
    executor_reason:str=Field(default='',max_length=1200)
class Create(Strict):
    request_controls:RequestControls|None=None
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    context_id:str
    goal:str=Field(min_length=1,max_length=2500)
    mode:Literal['quick','director','deep']='director'
    executor:str=Field(max_length=300)
    commander:str=Field(default='codex',max_length=300)
    skills:list[str]=Field(default_factory=lambda:['context','scene','character'],max_length=4)
    start:int=Field(default=0,ge=0)
    end:int=Field(default=0,ge=0)
    quote:str=Field(default='',max_length=16000)
    limits:Limits=Field(default_factory=Limits)
    scene_id:str|None=Field(default=None,pattern=r'^scene_[0-9a-f]{32}$')
    scene_option:int=Field(default=0,ge=0,le=2)
class Patch(Strict):
    etag:str
    goal:str|None=Field(default=None,min_length=1,max_length=2500)
    executor:str|None=Field(default=None,max_length=300)
    commander:str|None=Field(default=None,max_length=300)
    mode:Literal['quick','director','deep']|None=None
    plan:Plan|None=None
    draft:str|None=Field(default=None,max_length=32000)
    instruction:str|None=Field(default=None,max_length=2500)
    limits:Limits|None=None
    context_id:str|None=None
class Control(Strict):
    epoch:int|None=None
    task_id:str|None=None
    etag:str
    action:Literal['plan','run','pause','interrupt','terminate']
    auto_continue:bool=False
    confirm_plan:bool=False
    continue_important:bool=False
class Rewrite(Strict):
    etag:str
    start:int=Field(ge=0)
    end:int=Field(ge=0)
    quote:str=Field(min_length=1,max_length=16000)
    instruction:str=Field(min_length=1,max_length=2500)
class Candidate(Strict):etag:str
class Review(Strict):
    etag:str
    mode:Literal['character','dialogue','pov','causality','pacing']='character'
    model:str='codex'

class Director:
    def __init__(self,writing,reviews):
        self.writing=writing;self.tools=writing.tools;self.center=writing.center
        self.manager=writing.manager;self.reviews=reviews;self.lock=writing.lock;self.buffers={}
    def path(self,p,id):
        if not re.fullmatch(r'director_[0-9a-f]{32}',id or ''):raise ConsoleError('指挥任务不存在',404)
        return self.tools.local(p,'director/'+id+'.json')
    def put(self,p,row):
        row.pop('etag',None);row['updated_at']=now();write(self.path(p,row['id']),row)
    def get(self,p,id):
        with self.lock:
            path=self.path(p,id);row=read(path)
            if not row or row.get('project_id')!=p:raise ConsoleError('指挥任务不属于当前作品',404)
            if row.get('active_task') and row['status'] in {'PLANNING','GENERATING','REVIEWING','CANCELLING','TERMINATED'}:
                task=self.manager(p).tasks.get(row['active_task'])
                if not task or task.status in TERMINAL and task.finished_at:
                    is_review=row['active_task']==row.get('review_task_id')
                    if is_review and task and row.get('review_accounted')!=task.id:
                        elapsed=max(0,(datetime.fromisoformat(task.finished_at)-datetime.fromisoformat(task.started_at)).total_seconds()) if task.started_at else 0
                        row['seconds_used']+=elapsed;row['review_accounted']=task.id
                        row['usage'].append({'backend':'codex','provider':'Codex 定向复核','model':'CURRENT_LOGIN_MODEL','input_tokens':None,'output_tokens':None,'cost':None,'currency':row['limits']['currency'],'seconds':round(elapsed,3)})
                    status='TERMINATED' if row['status']=='TERMINATED' else 'PAUSED' if row['status']=='CANCELLING' else 'REVIEW_READY' if is_review and task and task.status=='SUCCEEDED' else 'INTERRUPTED'
                    row.update(status=status,phase='定向复核报告已保存，供作者决定' if status=='REVIEW_READY' else '远端请求已结束；从本地检查点创建新请求',active_task=None,pause_requested=True)
                    if task and task.error:row['last_error']=task.error
                    self.put(p,row)
            row['etag']=digest(path.read_bytes());return row
    def checked(self,p,id,etag):
        row=self.get(p,id)
        if row['etag']!=etag:raise ConsoleError('指挥台记录已更新，请刷新后重试',409)
        if row['status']=='TERMINATED':raise ConsoleError('任务已终止，草稿仍可查看；请新建任务',409)
        return row
    def context(self,p,row,locked=False):
        return self.writing.use_context(p,row['context_id'],row['path'],row['revision'],locked=locked)
    def safe(self,context,value):
        from knowledge_isolation import assert_no_hidden
        try:assert_no_hidden(value,context['hidden'])
        except ValueError:raise ConsoleError('本次要求或候选未通过 Writer 信息边界检查；请用当前可披露的正向要求重建，不发送隐藏真相',409) from None
        if re.search(r'(不要|不得).{0,30}(暗示|透露|揭露)',json.dumps(value,ensure_ascii=False)):
            raise ConsoleError('请用正向创作要求；禁止性语句也可能携带秘密',409)
    def history(self,p,path=None):
        self.tools.writable(p);rows=[]
        for f in self.tools.local(p,'director').glob('director_*.json'):
            v=self.get(p,f.stem)
            if path and v['path']!=path:continue
            rows.append({k:v.get(k) for k in ['id','goal','path','mode','status','phase','updated_at','executor']})
        return sorted(rows,key=lambda v:v['updated_at'],reverse=True)[:80]
    def model_ref(self,p,group,ref):
        effective=self.center.controls_for(p,group,model=ref).model
        provider,model=self.center.choose(p,group,effective)
        return provider.provider_id+'::'+model.id if provider else effective
    def create(self,p,b):
        self.tools.writable(p);doc=self.tools.doc(p,b.path);text=normalized(doc)
        if doc['etag']!=b.revision:raise ConsoleError('请先保存正文再创建指挥任务',409)
        ctx=self.writing.use_context(p,b.context_id,b.path,b.revision,locked=True);self.safe(ctx,b.goal)
        b.executor=self.model_ref(p,'cowrite',b.executor)
        b.commander=self.model_ref(p,'scene_design',b.commander)
        if b.end<b.start or b.end>utf16_index(text,len(text)) or utf16_slice(text,b.start,b.end)!=b.quote:raise ConsoleError('目标选区已变化',409)
        scene=next(({'id':s['id'],'value':json.loads(s['text']),'basis':'APPROVED_SCENE_PLAN_NOT_FACT'} for s in ctx['packet']['sources'] if s['id'].startswith('scene-plan:')),None)
        if b.scene_id:
            prior=self.writing.get(p,'scene',b.scene_id)
            if prior.get('source_path')!=b.path or prior.get('source_revision')!=b.revision or prior.get('kind')!='options' or b.scene_option>=len(prior['result']['options']):raise ConsoleError('场景方案与当前正文版本不匹配',409)
            scene={'id':b.scene_id,'option':b.scene_option,'value':prior['result']['options'][b.scene_option]};self.safe(ctx,scene)
        skills,proof=load(self.tools.registry.engine,b.skills)
        row={'id':uid('director'),'project_id':p,'path':b.path,'revision':b.revision,'context_id':b.context_id,'context_hash':ctx['context_hash'],
             'goal':b.goal,'mode':b.mode,'executor':b.executor,'commander':b.commander,'scene_reference':scene,'skills':b.skills,'skill_proof':proof,'status':'READY' if b.mode=='quick' else 'DRAFT',
             'phase':'等待作者指令','target':{'start':b.start,'end':b.end,'quote':b.quote},'limits':b.limits.model_dump(),'calls':0,'seconds_used':0,
             'usage':[],'draft':'','partial':'','plan':{'summary':b.goal,'steps':[Step(title='执行作者要求',instruction=b.goal).model_dump()],'questions':[],'methods':[],'method_application':[]},
             'completed':[],'interventions':[],'versions':[],'plan_versions':[],'epoch':0,'active_task':None,'pause_requested':False,'pending_notice':None,'last_error':None,'rewrite':None,'created_at':now(),'updated_at':now()}
        if b.request_controls is not None:row['request_controls']=b.request_controls.model_dump()
        self.put(p,row);return self.get(p,row['id'])
    def patch(self,p,id,b):
        self.tools.writable(p)
        with self.lock:
            row=self.checked(p,id,b.etag)
            if row.get('active_task'):raise ConsoleError('先停止当前请求，或选择只暂停后续调度；已有草稿会保留',409)
            if b.context_id:row['context_id']=b.context_id
            ctx=self.context(p,row,locked=True)
            updates=b.model_dump(exclude={'etag','context_id'},exclude_none=True)
            if b.limits is not None:updates['limits']=b.limits.model_dump()
            self.safe(ctx,updates)
            if b.executor is not None:updates['executor']=self.model_ref(p,'cowrite',b.executor)
            if b.commander is not None:updates['commander']=self.model_ref(p,'scene_design',b.commander)
            if b.draft is not None:row['versions']=(row['versions']+[{'at':now(),'draft':row['draft'],'reason':'before_author_edit'}])[-20:]
            if b.plan is not None:
                old_steps=[Step.model_validate(row['plan']['steps'][i]).model_dump() for i in row['completed'] if i<len(row['plan']['steps'])]
                row['plan_versions']=(row['plan_versions']+[{'at':now(),'plan':row['plan']}])[-20:]
                row['completed']=[i for i,v in enumerate(b.plan.model_dump()['steps']) if v in old_steps]
            instruction=updates.pop('instruction',None)
            row.update(updates)
            if b.draft is not None:
                from .writing_contract import observations
                row['quality_observations']=observations(row['draft'],ctx['packet'])
            if instruction is not None:row['interventions']=(row['interventions']+[{'at':now(),'instruction':instruction}])[-30:]
            row.update(epoch=row['epoch']+1,status='READY',last_error=None)
            self.put(p,row);return self.get(p,id)
    def execution_brief(self,p,id):
        row=self.get(p,id);ctx=self.context(p,row,locked=True)
        index=next((i for i,s in enumerate(row['plan']['steps']) if s['enabled'] and i not in row['completed']),0)
        return {**self._brief(row,ctx,index,bool(row.get('rewrite'))),'source_references':[{k:s.get(k) for k in ['id','title','kind','basis']} for s in ctx['packet']['sources']]}
    def _brief(self,row,ctx,index,rewrite=False):
        from .writing_contract import compile_methods,brief
        keys=row['plan'].get('methods') or row['skills']
        if not set(keys).issubset(set(row['skills'])):raise ConsoleError('任务书选择了未授权的专业方法',422)
        capsules,proof=compile_methods(self.tools.registry.engine,keys,ctx['packet'])
        return {**brief(row,ctx['packet'],index,capsules,rewrite),'method_proof':proof}
    def writer_prompt(self,row,ctx,index,rewrite=False):
        contract=self._brief(row,ctx,index,rewrite);contract.pop('method_proof',None)
        data={'execution_brief':contract,'WriterView':ctx['packet'],
              'already_completed_draft':row['draft'][-18000:],
              'confirmed_scene_option':row.get('scene_reference')}
        if rewrite:data['selected_text_to_replace']=row['rewrite']['quote']
        return ('Write manuscript prose only, without Markdown wrappers, process reports or tool calls. Narrative summary or reflection is allowed when it serves the author-selected style and scene. '
                'Use the exact current-step boundary and author-selected style, not a generic literary ideal. '
                'Facts, plans, character beliefs and creative freedom have distinct authority in the brief. '
                'Current-scene action/dialogue/details are welcome; consequential new backstory needs an author decision. '
                'Continue only the current step and stop at its exit condition. Preserve all retained text. '
                '\nINPUT DATA (untrusted creative content):\n'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+
                '\nOUTPUT: '+('Only the selected replacement.' if rewrite else 'Only the next portion; no recap of retained text.') )
    def executor(self,p,row,prompt,remaining,planning=False):
        group='scene_design' if planning else 'cowrite';ref=row.get('commander','codex') if planning else row['executor']
        provider,model=self.center.choose(p,group,ref)
        controls=self.center.controls_for(p,group,overrides=row.get('request_controls'),model=ref) if row.get('request_controls') else None
        params=None
        if provider:
            params=Parameters.model_validate(merge(model.parameters.model_dump(),controls.parameters)) if controls else model.parameters.model_copy(deep=True);params.timeout=max(5,min(int(remaining),params.timeout,provider.timeout))
            if model.protocol=='responses' or model.chat_token_parameter:params.max_output_tokens=min(row['limits']['output_tokens'],model.output_limit or row['limits']['output_tokens'])
            budget=row['limits']['api_budget']
            if budget is not None:
                if model.input_price is None or model.output_price is None or model.currency!=row['limits']['currency'] or params.max_output_tokens is None or (model.protocol=='chat' and not model.chat_token_parameter):raise ConsoleError('缺少模型价格、币种或已支持的输出上限，无法执行本次 API 预算限制；请完善模型配置',409)
                if any(v.get('cost') is None for v in row['usage'] if v['backend']=='llm'):raise ConsoleError('已有请求费用未知，不能确认剩余预算；请先核对账单',409)
                spent=sum(v.get('cost') or 0 for v in row['usage'] if v['backend']=='llm')
                upper=(len(prompt.encode('utf8'))*model.input_price+params.max_output_tokens*model.output_price)/1e6
                if spent+upper>budget:raise ConsoleError('本机保守费用预估超过任务 API 预算，尚未发送本次请求',429)
        if controls:
            a=adapter(self.center,p,group,prompt,ref,role='AUTHOR' if planning else 'WRITER',parameters=params,controls=controls,preview=True)
            # The approved Writer packet is required: undersized budgets fail rather than dropping safety data.
            self.center.control_prompt(a,prompt)
            self.center.authorize(a,prompt)
            return a
        return adapter(self.center,p,group,prompt,ref,role='AUTHOR' if planning else 'WRITER',parameters=params)
    async def control(self,p,id,b):
        self.tools.writable(p)
        with self.lock:
            row=self.get(p,id)
            if row['status']=='TERMINATED':raise ConsoleError('任务已经终止',409)
            if b.action in {'pause','interrupt','terminate'} and b.epoch is not None:
                if b.epoch!=row['epoch'] or b.task_id!=row.get('active_task'):raise ConsoleError('当前执行已改变，旧指令不能影响新请求',409)
            elif row['etag']!=b.etag:raise ConsoleError('指挥台记录已更新，请刷新后重试',409)
            if b.action=='pause':
                row['pause_requested']=True;row['phase']='当前请求结束后暂停后续调度' if row.get('active_task') else '已暂停';self.put(p,row);return self.get(p,id)
            if b.action in {'interrupt','terminate'}:
                task_id=row.get('active_task');row['epoch']+=1
                # Commit complete received deltas, never discard them on transport cancellation.
                row['partial']=self.buffers.get((p,id,row['epoch']-1),row.get('partial',''))
                if row.get('partial'):
                    if row.get('rewrite'):row['versions']=(row['versions']+[{'draft':row['draft'],'partial_rewrite':row['partial'],'reason':'interrupted_rewrite','at':now()}])[-20:]
                    else:row['draft']+=row['partial']
                row.update(partial='',pause_requested=True,status='TERMINATED' if b.action=='terminate' else 'CANCELLING',phase='正在取消当前请求；上游可能已经计费',last_error=None)
                self.put(p,row)
            else:
                if row.get('active_task'):raise ConsoleError('当前请求尚未结束，请等待取消回执',409)
                ctx=self.context(p,row,locked=True);self.safe(ctx,{'goal':row['goal'],'plan':row['plan'],'draft':row['draft'],'directions':row['interventions']})
                if row['calls']>=row['limits']['max_calls'] or row['seconds_used']>=row['limits']['seconds']:raise ConsoleError('已达到本任务轮次或时间限制；作者可调整上限后再继续',409)
                if b.action=='run' and (not b.confirm_plan):raise ConsoleError('先检查并明确确认当前任务书',409)
                if b.action=='run' and any(row['plan']['steps'][i].get('needs_author') for i in range(len(row['plan']['steps'])) if i not in row['completed']) and not b.continue_important:raise ConsoleError('计划含重要剧情决定；需作者明确确认后继续',409)
                if b.action=='plan' and row['mode']=='quick':raise ConsoleError('快速模式直接使用执行模型，不强制 Codex 规划',409)
                if b.action=='run' and not row['rewrite'] and not any(s['enabled'] for s in row['plan']['steps']):raise ConsoleError('任务书尚无已启用步骤；请先补充必要条件并启用要执行的步骤',409)
                if b.action=='run' and not row['rewrite'] and all(not s['enabled'] or i in row['completed'] for i,s in enumerate(row['plan']['steps'])):raise ConsoleError('当前任务书已完成；可局部重写候选，或编辑并保存后续步骤',409)
                # Run privacy/credential/budget preflight on the exact next payload before queuing.
                next_index=next((i for i,s in enumerate(row['plan']['steps']) if s['enabled'] and i not in row['completed']),0)
                first_executor=self.executor(p,row,self.writer_prompt(row,ctx,next_index,bool(row['rewrite'])),row['limits']['seconds']-row['seconds_used']) if b.action=='run' else None
                return self.start(p,row,b,ctx,first_executor)
        if task_id:
            await self.manager(p).cancel(task_id)
        with self.lock:
            current=self.get(p,id)
            current.update(status='TERMINATED' if b.action=='terminate' else 'CANCELLING' if task_id else 'PAUSED',phase='整项任务已终止；正在收尾当前请求' if b.action=='terminate' else '已请求中断，等待真实结束回执；上游仍可能计费')
            self.put(p,current);return self.get(p,id)
    def start(self,p,row,b,ctx,first_executor=None):
        row.update(epoch=row['epoch']+1,status='PLANNING' if b.action=='plan' else 'GENERATING',phase='Codex 正在制定任务书' if b.action=='plan' else '执行模型正在生成',pause_requested=False,last_error=None,pending_notice=None)
        epoch=row['epoch'];id=row['id'];self.put(p,row);task=None
        def live():
            current=self.get(p,id)
            if current['epoch']!=epoch:raise InterruptedError('本次请求已被新指令或取消取代')
            return current
        def perform(a,prompt,emit,cancelled,output_schema=None,planning=False):
            with self.lock:
                current=live();remaining=current['limits']['seconds']-current['seconds_used']
                if remaining<1 or current['calls']>=current['limits']['max_calls']:raise ConsoleError('已达到时间或调用轮次上限',409)
                current['calls']+=1;self.put(p,current);task.adapter=a
            if cancelled():raise InterruptedError('任务已取消')
            begin=time.monotonic();first_response=None;first_output=None;expired=threading.Event()
            def timeout():expired.set();a.close()
            timer=threading.Timer(min(remaining,90 if planning else max(5,getattr(getattr(a,'params',None),'timeout',120))),timeout);timer.daemon=True;timer.start()
            last_flush=0.;buffer='';usage={'backend':metadata(a).get('backend','codex'),'provider':metadata(a).get('provider_name','Codex'),'model':metadata(a).get('model','UNKNOWN'),'input_tokens':None,'output_tokens':None,'cost':None,'currency':current['limits']['currency']}
            if hasattr(a,'record'):
                original_record=a.record
                def record(provider,model,project,group,status,duration,tokens,error):
                    original_record(provider,model,project,group,status,duration,tokens,error)
                    inp=tokens.get('input_tokens',tokens.get('prompt_tokens'));out=tokens.get('output_tokens',tokens.get('completion_tokens'))
                    usage.update(input_tokens=inp,output_tokens=out,currency=model.currency,cost=(inp*model.input_price+out*model.output_price)/1e6 if inp is not None and out is not None and model.input_price is not None and model.output_price is not None else None)
                a.record=record
            def relay(kind,text,data=None):
                nonlocal buffer,last_flush,first_response,first_output
                if first_response is None and kind in {'message','llm_delta','reasoning_summary'}:first_response=round(time.monotonic()-begin,3)
                if kind in {'llm_delta','message'} and (data or {}).get('delta',text) and first_output is None:first_output=round(time.monotonic()-begin,3)
                with self.lock:
                    current=live()
                    if cancelled():return
                    if not planning and kind in {'llm_delta','message'}:
                        delta=(data or {}).get('delta',text);available=max(0,current['limits']['output_characters']-len(current['draft'])-len(buffer));piece=delta[:available];buffer+=piece
                        self.buffers[(p,id,epoch)]=buffer
                        if len(piece)<len(delta):a.close();raise ConsoleError('候选达到本机字符上限，已保留上限内的内容',413)
                        current['partial']=buffer
                        if time.monotonic()-last_flush>.25:self.put(p,current);last_flush=time.monotonic()
                        emit('director_delta',delta,{'epoch':epoch,'delta':delta,'offset':utf16_index(buffer,len(buffer)-len(delta))})
                    elif kind not in {'message','llm_delta','reasoning_summary'}:emit(kind,text,data)
            try:
                result=a.start_task(prompt,relay,read_only=True,output_schema=output_schema,allow_web=False)
                if expired.is_set():raise ConsoleError('此阶段超时，草稿已保留；上游执行与费用需核对后再手动重试',504)
                if result['status']!='completed':raise ConsoleError(result.get('error') or '请求已停止，已收到的草稿保留',409)
                return result['output']
            finally:
                timer.cancel();a.close();usage.update(model=metadata(a).get('observed_model') or metadata(a).get('model','UNKNOWN'),seconds=round(time.monotonic()-begin,3),first_response_seconds=first_response,first_output_seconds=first_output,phase='PLAN' if planning else 'WRITE')
                with self.lock:
                    current=self.get(p,id);current['usage'].append(usage);current['seconds_used']+=usage['seconds']
                    if current['epoch']==epoch and not planning:current['partial']=buffer
                    self.put(p,current)
                    self.buffers.pop((p,id,epoch),None)
        def execute(emit,cancelled):
            nonlocal ctx,first_executor
            try:
                if b.action=='plan':
                    methods,proof=load(self.tools.registry.engine,row['skills'])
                    settings=self.center.settings();choices=[{'ref':'codex','name':'Codex 当前登录'}]+[{'ref':v.provider_id+'::'+m.id,'name':v.display_name+' / '+(m.display_name or m.id),'capabilities':m.capabilities} for v in settings.providers if v.enabled for m in v.available_models][:39]
                    if not any(v['ref']==row['executor'] for v in choices):choices.append({'ref':row['executor'],'name':row['executor']})
                    prompt=('Act as a bounded scene director. Use the supplied actual professional methods to create an editable task brief, not prose. '
                            'Only supplied Writer-safe facts; no tools or invented established backstory. Allow fresh dialogue, immediate behavior and incidental details. Important new past or persistent setting changes require an author decision. Methods are advisory, not mandatory genre formulas; do not impose hooks or a final moral. Latest author directions outrank earlier plans. '
                            'Plan only the remaining work after the retained draft; preserve manual wording and do not schedule completed material again. '
                            'Choose 1 step for director mode, up to 4 for deep mode. Keep each instruction concise (aim under 600 Chinese characters) and use at most four concise checks. State a goal, changing resistance/tactic, action consequence and exit_condition. An unresolved final conflict still needs meaningful progression before that endpoint. Distinguish actual author locks from optional method advice: do not invent extra prohibitions on incidental present-scene objects, form details or actions. Unknown consequential history stays unknown, but missing trivial detail is not a prerequisite failure. deferred_outcomes are author-requested later outcomes to leave open, not a list of everything the scene could do. '
                            'Mark important plot decisions needs_author=true. Select relevant supplied method IDs and explain their concrete application. Recommend only an available executor; it remains a proposal until the author selects it. Do not infer model quality from names alone. Return schema JSON.\nMETHODS:\n'+methods+'\nDATA:\n'+json.dumps({'goal':row['goal'],'mode':row['mode'],'WriterView':ctx['packet'],'already_completed_draft':row['draft'][-18000:],'previous_plan':row['plan'] if row['plan_versions'] or row['draft'] or row['completed'] else None,'confirmed_scene_option':row.get('scene_reference'),'completed_step_indices':row['completed'],'directions':row['interventions'][-8:],'executor':row['executor'],'available_executors':choices,'available_methods':row['skills']},ensure_ascii=False))
                    a=self.executor(p,row,prompt,row['limits']['seconds']-row['seconds_used'],planning=True);output=perform(a,prompt,emit,cancelled,schema(Plan),True);plan=Plan.model_validate_json(output).model_dump();self.safe(ctx,plan)
                    if not set(plan['methods']).issubset(set(row['skills'])) or (row['skills'] and not plan['methods']) or len(plan['method_application'])<len(plan['methods']):raise ConsoleError('任务书未说明已加载专业方法的实际应用，请检查后手动重试',422)
                    if plan['recommended_executor'] and plan['recommended_executor'] not in {v['ref'] for v in choices}:raise ConsoleError('任务书推荐了未配置的模型，未切换执行者',422)
                    if row['mode']=='director' and len(plan['steps'])!=1:raise ConsoleError('导演模式每次只安排一个场景，请改为深度模式或缩小目标',422)
                    with self.lock:
                        current=live();current['plan_versions']=(current['plan_versions']+[{'at':now(),'plan':current['plan']}])[-20:];current.update(plan=plan,skill_proof=proof,completed=[],status='PLAN_REVIEW',phase='任务书已生成，等待作者检查',active_task=None);self.put(p,current)
                    return {'status':'completed','output':'任务书已生成；尚未生成正文'}
                while True:
                    with self.lock:
                        current=live()
                        pending=[i for i,s in enumerate(current['plan']['steps']) if s['enabled'] and i not in current['completed']]
                        if cancelled():raise InterruptedError('已取消')
                        if not pending and not current['rewrite']:break
                        index=pending[0] if pending else 0;rewrite=bool(current['rewrite']);ctx=self.context(p,current);self.safe(ctx,current['draft']);prompt=self.writer_prompt(current,ctx,index,rewrite)
                    a=first_executor or self.executor(p,current,prompt,current['limits']['seconds']-current['seconds_used']);first_executor=None;emit('director_stage','执行：'+('局部重写' if rewrite else current['plan']['steps'][index]['title']),{'phase':'GENERATING','executor':metadata(a)})
                    receipt=self._brief(current,ctx,index,rewrite)
                    emit('writing_brief','本次执行要求已固定',{'version':receipt['version'],'methods':[m['id'] for m in receipt['selected_methods']]})
                    output=perform(a,prompt,emit,cancelled);self.safe(ctx,output)
                    with self.lock:
                        current=live();current['versions']=(current['versions']+[{'at':now(),'draft':current['draft'],'reason':'before_model_append'}])[-20:]
                        if rewrite:
                            rr=current['rewrite'];text=current['draft'];a16=text.encode('utf-16-le');current['draft']=a16[:rr['start']*2].decode('utf-16-le')+output+a16[rr['end']*2:].decode('utf-16-le');current['rewrite']=None
                        else:current['draft']+=output;current['completed'].append(index)
                        from .writing_contract import observations
                        current['quality_observations']=observations(current['draft'],ctx['packet'])
                        current['execution_receipts']=(current.get('execution_receipts',[])+[{'at':now(),'step':index,'prompt_sha256':text_hash(prompt),'prompt_characters':len(prompt),'context_hash':ctx['context_hash'],'brief':receipt}])[-12:]
                        current['partial']='';self.put(p,current)
                        if rewrite or not b.auto_continue or current['pause_requested']:break
                        if any(s['needs_author'] for i,s in enumerate(current['plan']['steps']) if i not in current['completed']) and not b.continue_important:break
                with self.lock:
                    current=live();current.update(status='CANDIDATE' if all(not s['enabled'] or i in current['completed'] for i,s in enumerate(current['plan']['steps'])) else 'PAUSED',phase='候选已保存，等待作者决定',active_task=None);self.put(p,current)
                return {'status':'completed','output':'候选草稿已保存；未修改正式正文'}
            except Exception as error:
                with self.lock:
                    current=self.get(p,id)
                    if current['epoch']==epoch:
                        if current['partial'] and not current['rewrite']:current['draft']+=current['partial'];current['partial']=''
                        current.update(status='PAUSED' if isinstance(error,InterruptedError) or cancelled() else 'FAILED',active_task=None,last_error=str(error)[:1000],phase='草稿已保留，等待作者处理',pending_notice=getattr(error,'ai_notice',None));self.put(p,current)
                return {'status':'interrupted' if cancelled() else 'failed','error':str(error)[:1000],'output':''}
        req=TaskRequest(type='custom_prompt',prompt='AI 创作指挥台：'+('任务书' if b.action=='plan' else '执行候选'),options=TaskOptions(read_only=True,resume=False,timeout_seconds=row['limits']['seconds']))
        task=self.manager(p).prepared(req,'Project-scoped creative delegation',True,row['id'],execute=execute,provider=row.get('commander','codex')+' / '+row['executor'],skill=', '.join(row['skills']),application_actions=True)
        task.private_text=True
        with self.lock:
            current=self.get(p,id);current['active_task']=task.id;self.put(p,current)
        return {**self.get(p,id),'task':task.public()}
    def rewrite(self,p,id,b):
        self.tools.writable(p)
        with self.lock:
            row=self.checked(p,id,b.etag)
            if row.get('active_task'):raise ConsoleError('先停止当前请求再选择局部重写',409)
            if b.end<=b.start or utf16_slice(row['draft'],b.start,b.end)!=b.quote:raise ConsoleError('候选选区已改变',409)
            ctx=self.context(p,row,locked=True);self.safe(ctx,b.model_dump());row['rewrite']=b.model_dump(exclude={'etag'});row['status']='READY';self.put(p,row);return self.get(p,id)
    def stage(self,p,id,b):
        with self.lock:
            row=self.checked(p,id,b.etag)
            if row.get('active_task') or not row['draft'].strip():raise ConsoleError('先停止生成并保留非空候选',409)
            ctx=self.context(p,row,locked=True);self.safe(ctx,row['draft'])
            target=row['target'];candidate=self.tools.stage_replacement(p,row['path'],row['revision'],target['start'],target['end'],target['quote'],row['draft'],{'kind':'creative-director','record_id':id},allow_insert=True,limit=32000)
            row['candidate_id']=candidate['id'];self.put(p,row);return {'candidate':candidate,'record':self.get(p,id)}


    def review(self,p,id,b):
        from .reviews import Start
        with self.lock:
            row=self.checked(p,id,b.etag)
            if row.get('active_task'):raise ConsoleError('先停止生成，再评审固定候选',409)
            if row['calls']>=row['limits']['max_calls'] or row['limits']['seconds']-row['seconds_used']<30:raise ConsoleError('本任务已达到调用或时间限制',409)
            staged=self.stage(p,id,Candidate(etag=row['etag']));candidate=staged['candidate']
            task=self.reviews.start(p,Start(path=row['path'],candidate_id=candidate['id'],writer_context_id=row['context_id'],mode=b.mode,model=b.model,timeout_seconds=min(300,int(row['limits']['seconds']-row['seconds_used'])),criteria=['只针对候选文本和已授权 Writer View 检查，缺失信息标 UNKNOWN；保留作者声音。','核查疑似新过去、持久关系变化、场景边界与动作后果。没有检索证据不等于情节绝对错误；给出引用、合理解释与待作者确认事项。',json.dumps({'goal':row['goal'],'steps':row['plan']['steps'],'directions':row['interventions'][-4:]},ensure_ascii=False)]))
            current=self.get(p,id);current['calls']+=1;current['review_id']=task['review_id'];current['review_task_id']=task['id'];current.update(active_task=task['id'],status='REVIEWING',phase='现有文学评审正在定向复核候选');self.put(p,current)
            return {**self.get(p,id),'task':task}

def routes(service):
    r=APIRouter(prefix='/api/projects/{p}/creative-director')
    @r.get('/skills')
    def skills(p:str):service.tools.writable(p);return {'skills':catalog(service.tools.registry.engine)}
    @r.get('')
    def history(p:str,path:str|None=None):return {'records':service.history(p,path)}
    @r.post('')
    def create(p:str,b:Create):return service.create(p,b)
    @r.get('/{id}')
    def get(p:str,id:str):return service.get(p,id)
    @r.get('/{id}/brief')
    def brief(p:str,id:str):return service.execution_brief(p,id)
    @r.patch('/{id}')
    def patch(p:str,id:str,b:Patch):return service.patch(p,id,b)
    @r.post('/{id}/control')
    async def control(p:str,id:str,b:Control):return await service.control(p,id,b)
    @r.post('/{id}/rewrite')
    def rewrite(p:str,id:str,b:Rewrite):return service.rewrite(p,id,b)
    @r.post('/{id}/review')
    async def review(p:str,id:str,b:Review):return service.review(p,id,b)
    @r.get('/{id}/review')
    def report(p:str,id:str):
        row=service.get(p,id)
        if not row.get('review_id'):raise ConsoleError('暂无复核报告',404)
        return service.reviews.get(p,row['review_id'])
    @r.post('/{id}/candidate')
    def stage(p:str,id:str,b:Candidate):return service.stage(p,id,b)
    return r
