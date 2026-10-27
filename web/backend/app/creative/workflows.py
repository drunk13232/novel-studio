"""User-owned step recipes over existing domain services, not an Agent runtime.
Templates contain configuration only. Every AI step is an existing TaskManager task.
"""
from __future__ import annotations
import asyncio,copy,json,re,threading
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from fastapi import APIRouter,Request
from app.errors import ConsoleError
from app.library.storage import read,write,uid,now,digest
from app.ai.controls import RequestControls
from app.models.requests import TaskRequest,TaskOptions
from app.projects.foundation import schema
from app.tasks.manager import TERMINAL
from app.studio_tools import normalized,utf16_index
from app.creative.tasks import adapter,metadata

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
KINDS=('world_overview','world_rules','world_review','chapter_write','chapter_review','local_proofread','manual')
class Step(Strict):
    id:str=Field(default_factory=lambda:uid('step'),pattern=r'^step_[a-z0-9_-]{1,64}$')
    kind:Literal['world_overview','world_rules','world_review','chapter_write','chapter_review','local_proofread','manual']
    title:str=Field(min_length=1,max_length=100)
    instruction:str=Field(default='',max_length=3000)
    enabled:bool=True
    pause_after:bool=True
    input_mode:Literal['goal','previous']='goal'
    use_sources:bool=False
    use_blueprint:bool=False
    model:str=Field(default='codex',max_length=300)
    controls:RequestControls=Field(default_factory=RequestControls)
    review_mode:Literal['character','dialogue','causality','pacing','style']='character'
    stop_on_findings:bool=True
    expected_output:str=Field(default='',max_length=800)
class Definition(Strict):
    format:Literal['novel-studio-workflow/1']='novel-studio-workflow/1'
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=2000)
    scope:Literal['world','chapter']
    steps:list[Step]=Field(min_length=1,max_length=12)
    @model_validator(mode='after')
    def valid(self):
        if len({s.id for s in self.steps})!=len(self.steps):raise ValueError('步骤 ID 重复 / Duplicate step IDs')
        for s in self.steps:
            if s.kind!='manual' and (s.kind.startswith('world_'))!=(self.scope=='world'):raise ValueError('步骤不属于此流程类型 / Step outside workflow scope')
            if s.controls.model and s.controls.model!=s.model:raise ValueError('步骤模型与参数模型不一致 / Conflicting model selections')
        if len(self.model_dump_json().encode('utf8'))>96000:raise ValueError('流程模板最多 96 KB / Template exceeds 96 KB')
        return self
class Save(Strict):
    etag:str=''
    definition:Definition
class RunCreate(Strict):
    template_id:str
    template_etag:str
    goal:str=Field(min_length=1,max_length=3000)
    path:str=Field(default='',max_length=300)
    revision:str=Field(default='',max_length=64)
    context_id:str=Field(default='',max_length=100)
    entity_ids:list[str]=Field(default_factory=list,max_length=8)
    note_ids:list[str]=Field(default_factory=list,max_length=6)
class Control(Strict):
    etag:str
    action:Literal['run','pause','stop','skip']
    confirm_send:bool=False
    auto_continue:bool=False
class Edit(Strict):
    etag:str
    step_id:str
    step:Step
    handoff:str=Field(default='',max_length=6000)
class Design(Strict):
    goal:str=Field(min_length=1,max_length=3000)
    scope:Literal['world','chapter']
    controls:RequestControls=Field(default_factory=RequestControls)
    confirm_send:Literal[True]

def skip_disabled(row):
    while row['index']<len(row['snapshot']['steps']) and not row['snapshot']['steps'][row['index']]['enabled']:
        step=row['snapshot']['steps'][row['index']];row['steps'][step['id']]={'status':'SKIPPED'};row['index']+=1

def builtins():
    return [Definition(name='世界观开局 / World first',scope='world',description='不要求人物、剧情或文学主题。World proposals only; no cast or plot prerequisite.',steps=[Step(id='step_overview',kind='world_overview',title='世界概览 / World overview'),Step(id='step_rules',kind='world_rules',title='自然与能力规则 / World rules',input_mode='previous'),Step(id='step_check',kind='world_review',title='条件与矛盾复核 / Challenge assumptions',input_mode='previous')]).model_dump(),Definition(name='轻量章节创作 / Chapter draft',scope='chapter',description='使用已批准 Writer 上下文，仅产候选与独立报告。Approved Writer context, candidate and separate review.',steps=[Step(id='step_draft',kind='chapter_write',title='生成正文候选 / Draft candidate'),Step(id='step_review',kind='chapter_review',title='人物与逻辑复核 / Review candidate',input_mode='previous',controls=RequestControls(context={'budget':131072}))]).model_dump()]

class Workflows:
    def __init__(self,director,world):
        self.director=director;self.world=world;self.tools=director.tools;self.center=director.center
        self.manager=director.manager;self.lock=threading.RLock();self.followers={}
    def path(self,p,id,kind):
        self.tools.writable(p)
        if not re.fullmatch(('flow_' if kind=='templates' else 'flowrun_')+r'[0-9a-f]{32}',id or ''):raise ConsoleError('流程记录不存在 / Workflow record not found',404)
        return self.tools.local(p,'workflows/'+kind+'/'+id+'.json')
    def _read(self,p,id,kind):
        f=self.path(p,id,kind);v=read(f)
        if not v or v.get('project_id')!=p:raise ConsoleError('流程不属于当前作品 / Workflow belongs to another project',404)
        return {**v,'etag':digest(f.read_bytes())}
    def put(self,p,row,kind):
        row=copy.deepcopy(row);row.pop('etag',None);row['updated_at']=now();write(self.path(p,row['id'],kind),row)
        return self._read(p,row['id'],kind)
    def template(self,p,id):return self._read(p,id,'templates')
    def save(self,p,b,id=None):
        with self.lock:
            if id:
                row=self.template(p,id)
                if row['etag']!=b.etag:raise ConsoleError('流程模板已更新，请重新读取 / Template changed',409)
                row['versions']=(row.get('versions',[])+[{'at':now(),'definition':row['definition']}])[-12:]
            else:row={'id':uid('flow'),'project_id':p,'created_at':now(),'version':0,'versions':[],'archived':False}
            row.update(definition=b.definition.model_dump(),version=row['version']+1,archived=False)
            return self.put(p,row,'templates')
    def archive(self,p,id,etag):
        with self.lock:
            row=self.template(p,id)
            if row['etag']!=etag:raise ConsoleError('流程模板已更新 / Template changed',409)
            row['archived']=True;return self.put(p,row,'templates')
    def listing(self,p):
        self.tools.writable(p)
        templates=[self.template(p,f.stem) for f in self.tools.local(p,'workflows/templates').glob('flow_*.json')]
        runs=[self.get(p,f.stem) for f in self.tools.local(p,'workflows/runs').glob('flowrun_*.json')]
        return {'presets':builtins(),'templates':[r for r in templates if not r.get('archived')],'runs':[{k:v for k,v in r.items() if k in {'id','goal','status','updated_at','template_name','scope','index','last_error'}} for r in sorted(runs,key=lambda r:r['updated_at'],reverse=True)[:80]],'kinds':KINDS}
    def get(self,p,id):
        with self.lock:
            row=self._read(p,id,'runs')
            if row.get('active_task') and (p,id) not in self.followers:
                task=self.manager(p).tasks.get(row['active_task'])
                if not task or task.status in TERMINAL and task.finished_at:
                    if task and task.status=='SUCCEEDED':
                        try:return self._settle(p,row,task,False)
                        except Exception:pass
                    if row['index']<len(row['snapshot']['steps']):
                        entry=row['steps'].get(row['snapshot']['steps'][row['index']]['id'])
                        if entry and entry.get('status')=='RUNNING':entry.update(status='INTERRUPTED',finished_at=now())
                    row.update(active_task=None,status='PAUSED',auto_continue=False,last_error='服务重启或任务中断；结果保留，请检查后继续。Interrupted; inspect retained results before resuming.')
                    return self.put(p,row,'runs')
            return row
    def create(self,p,b):
        with self.lock:
            template=self.template(p,b.template_id)
            if template['etag']!=b.template_etag or template.get('archived'):raise ConsoleError('流程模板已变化 / Template changed',409)
            d=Definition.model_validate(template['definition'])
            # Validate references now; only explicitly selected sources may enter a step.
            for id in b.entity_ids:self.world.bible.get(p,id)
            for id in b.note_ids:self.world.writing.references.get(p,'notes',id)
            if d.scope=='chapter':
                doc=self.tools.doc(p,b.path)
                if doc['etag']!=b.revision:raise ConsoleError('正文已变化，请保存并重新创建流程 / Manuscript changed',409)
                if any(s.enabled and s.kind in {'chapter_write','chapter_review'} for s in d.steps):self.director.writing.use_context(p,b.context_id,b.path,b.revision,locked=True)
            row={'id':uid('flowrun'),'project_id':p,'template_id':template['id'],'template_version':template['version'],'template_name':d.name,'scope':d.scope,'snapshot':d.model_dump(),'snapshot_versions':[],'goal':b.goal,'path':b.path,'revision':b.revision,'context_id':b.context_id,'entity_ids':b.entity_ids,'note_ids':b.note_ids,'index':0,'steps':{},'status':'READY','epoch':0,'calls':0,'active_task':None,'active_operation':None,'auto_continue':False,'pause_requested':False,'last_error':None,'pending_notice':None,'handoff':'','created_at':now()}
            return self.put(p,row,'runs')
    def edit(self,p,id,b):
        with self.lock:
            row=self.get(p,id)
            if row['etag']!=b.etag or row.get('active_task'):raise ConsoleError('先等待或停止当前步骤，并重新读取 / Stop the active step before editing',409)
            steps=row['snapshot']['steps'];i=next((i for i,s in enumerate(steps) if s['id']==b.step_id),-1)
            if i<row['index'] or b.step.id!=b.step_id:raise ConsoleError('已完成步骤不可覆盖；请复制为新流程 / Completed steps are immutable',409)
            replacement=copy.deepcopy(row['snapshot']);replacement['steps'][i]=b.step.model_dump();Definition.model_validate(replacement)
            row['snapshot_versions']=(row['snapshot_versions']+[{'at':now(),'snapshot':row['snapshot'],'reason':'AUTHOR_EDIT_PENDING_STEP'}])[-12:]
            row.update(snapshot=replacement,handoff=b.handoff,status='READY',auto_continue=False,last_error=None,pending_notice=None)
            return self.put(p,row,'runs')
    def previous(self,p,row):
        for step in reversed(row['snapshot']['steps'][:row['index']]):
            value=row['steps'].get(step['id'],{})
            if value.get('status')=='SUCCEEDED':return value.get('result')
        return None
    def _settle(self,p,row,task,normal=True,local_ai=None):
        s=row['snapshot']['steps'][row['index']];op=row['active_operation'];saved=row['steps'].setdefault(s['id'],{})
        if task is not None and task.status!='SUCCEEDED':
            saved.update(status='CANCELLED' if task.status in {'CANCELLED','INTERRUPTED'} else 'FAILED',finished_at=now())
            row.update(status='CANCELLED' if task.status=='CANCELLED' else 'FAILED',active_task=None,auto_continue=False,last_error=task.error or '本步骤未完成 / Step did not complete')
            return self.put(p,row,'runs')
        if op['kind']=='world':
            v=self.world.refresh(p,op['id'])
            if v['batches'][0]['status']!='DONE':raise ConsoleError('世界设计未产生完成回执 / No completed design receipt',409)
            data=v['result'];text=json.dumps(data,ensure_ascii=False);target='WORLD_PROPOSAL'
        elif op['kind']=='director':
            v=self.director.get(p,op['id'])
            if v['status']!='CANDIDATE' or not v['draft']:raise ConsoleError('正文候选未完成 / Candidate incomplete',409)
            data={'draft':v['draft']};text=v['draft'];target='MANUSCRIPT_CANDIDATE'
        else:
            v=self.director.reviews.get(p,op['id']);data={'report':v['report'],'anchors':v.get('anchors',[])};text=json.dumps(v['report'],ensure_ascii=False);target='REVIEW_NOT_WRITER_CONTEXT'
        result={'kind':op['kind'],'id':op['id'],'revision':v['etag'],'text':text,'data':data,'basis':target,'ai':task.ai_metadata if task is not None else local_ai}
        if len(json.dumps(result,ensure_ascii=False))>100000:raise ConsoleError('步骤结果过大；请在原工具查看 / Result too large for workflow handoff',413)
        saved.update(status='SUCCEEDED',result=result,finished_at=now());row['index']+=1
        while row['index']<len(row['snapshot']['steps']) and not row['snapshot']['steps'][row['index']]['enabled']:
            skipped=row['snapshot']['steps'][row['index']];row['steps'][skipped['id']]={'status':'SKIPPED'};row['index']+=1
        findings=op['kind']=='review' and s['stop_on_findings'] and any(x.get('priority')=='MUST FIX' or x.get('severity') in {'ERROR','FAIL'} for x in data['report'].get('issues',[]))
        row.update(active_task=None,active_operation=None,status='WAITING' if s['pause_after'] or findings or row['pause_requested'] or not normal else 'READY',pending_notice=None,last_error=None)
        if row['index']>=len(row['snapshot']['steps']):row['status']='COMPLETED'
        return self.put(p,row,'runs')
    async def _follow(self,p,id,epoch,task):
        try:
            await task.runner
            with self.lock:
                row=self._read(p,id,'runs')
                if row['epoch']!=epoch or row.get('active_task')!=task.id:return
                try:row=self._settle(p,row,task)
                except Exception as e:
                    row.update(active_task=None,status='FAILED',auto_continue=False,last_error=str(e)[:1000]);row=self.put(p,row,'runs')
                more=row['status']=='READY' and row['auto_continue']
            if more:
                try:await self._advance(p,row)
                except Exception as e:self._failed(p,id,e)
        finally:
            if self.followers.get((p,id)) is asyncio.current_task():self.followers.pop((p,id),None)
    def _failed(self,p,id,e):
        with self.lock:
            row=self._read(p,id,'runs');row.update(status='FAILED',auto_continue=False,last_error=str(e)[:1000],pending_notice=getattr(e,'ai_notice',None));return self.put(p,row,'runs')
    async def _advance(self,p,row,lease=None):
        from app.library.world_studio import Design as WorldDesign,Start as WorldStart
        from app.creative.director import Create as DirectorCreate,Control as DirectorControl,Patch as DirectorPatch,Limits
        from app.creative.reviews import Start as ReviewStart
        with self.lock:
            if row.get('active_task'):raise ConsoleError('已有步骤运行中 / A step is running',409)
            for f in self.tools.local(p,'workflows/runs').glob('flowrun_*.json'):
                other=self._read(p,f.stem,'runs')
                if other['id']!=row['id'] and other.get('active_task'):raise ConsoleError('当前作品已有流程运行中 / Another workflow is active',409)
            if row['calls']>=24:raise ConsoleError('本流程已达 24 次调用上限，请复制新版本 / Call limit reached',409)
            while row['index']<len(row['snapshot']['steps']) and not row['snapshot']['steps'][row['index']]['enabled']:
                s=row['snapshot']['steps'][row['index']];row['steps'][s['id']]={'status':'SKIPPED'};row['index']+=1
            row=self.put(p,row,'runs')  # Persist skipped positions even if the following preflight fails.
            if row['index']>=len(row['snapshot']['steps']):row['status']='COMPLETED';return self.put(p,row,'runs')
            step=Step.model_validate(row['snapshot']['steps'][row['index']]);prev=self.previous(p,row)
            attempt=row['steps'].get(step.id,{})
            if attempt.get('attempts',0)>=3:raise ConsoleError('本步骤已尝试三次，请检查并编辑或复制流程 / Step retry limit reached',409)
            if step.kind=='manual':
                row['steps'][step.id]={'status':'SUCCEEDED','result':{'kind':'manual','text':row['handoff'] or step.instruction,'basis':'AUTHOR_INPUT'},'finished_at':now()};row.update(index=row['index']+1,status='WAITING',handoff='')
                skip_disabled(row)
                if row['index']>=len(row['snapshot']['steps']):row['status']='COMPLETED'
                return self.put(p,row,'runs')
            if row['scope']=='chapter' and step.kind in {'chapter_write','chapter_review'}:
                self.director.writing.use_context(p,row['context_id'],row['path'],row['revision'],locked=True)
            controls=step.controls.model_copy(deep=True);controls.model=step.model
            goal=row['goal']+'\n当前步骤 / Current step: '+step.title+'\n'+step.instruction+'\n作者检查的期望输出（不是数学证明） / Expected output for author review: '+step.expected_output
            if row['handoff']:goal+='\n作者本次补充 / Author handoff: '+row['handoff']
            transferred=''
            if step.input_mode=='previous':
                if not prev:raise ConsoleError('前序步骤没有可用输出；选择仅用目标或先运行前序步骤 / Missing prior output',409)
                if row['scope']=='chapter' and prev.get('basis')=='REVIEW_NOT_WRITER_CONTEXT' and step.kind=='chapter_write':raise ConsoleError('评审报告不能自动进入 Writer；请手动提炼为正向要求 / Review is not Writer context',409)
                transferred=prev.get('text','')
                if len(transferred)>12000:raise ConsoleError('前序输出超过 12000 字，请缩小范围或改为仅用目标 / Prior output too large',413)
            operation=None;task=None
            if step.kind.startswith('world_'):
                mode,category={'world_overview':('starter','overview'),'world_rules':('design','nature'),'world_review':('challenge','overview')}[step.kind]
                if len(goal)>6000:raise ConsoleError('步骤要求过长 / Step goal too large',413)
                answers='Previous step is an unconfirmed proposal, never Canon.\n'+transferred if transferred else ''
                if len(answers)>6000:raise ConsoleError('前序世界稿超过 6000 字，请缩小范围 / World handoff too large',413)
                d=self.world.create(p,WorldDesign(goal=goal,mode=mode,depth='brief',categories=[category],entity_ids=row['entity_ids'] if step.use_sources else [],note_ids=row['note_ids'] if step.use_sources else [],use_blueprint=step.use_blueprint,answers=answers))
                public=self.world.start(p,d['id'],WorldStart(etag=d['etag'],batch=0,model=step.model,ai_controls=controls,confirm_send=True),_lease=lease)
                operation={'kind':'world','id':d['id']};task=self.manager(p).get(public['id'])
            elif step.kind=='chapter_write':
                # The approved Writer packet remains authoritative; no report or raw Bible is injected.
                self.director.safe(self.director.writing.use_context(p,row['context_id'],row['path'],row['revision'],locked=True),goal)
                doc=self.tools.doc(p,row['path']);end=utf16_index(normalized(doc),len(normalized(doc)))
                if len(goal)>2500:raise ConsoleError('正文步骤要求最多 2500 字 / Writer instruction too large',413)
                d=self.director.create(p,DirectorCreate(path=row['path'],revision=row['revision'],context_id=row['context_id'],goal=goal,mode='quick',executor=step.model,skills=['context'],start=end,end=end,request_controls=controls,limits=Limits(max_calls=2,seconds=300,output_characters=32000,output_tokens=controls.parameters.get('max_output_tokens') or 4096)))
                retained=attempt.get('result',{})
                if retained.get('partial') and retained.get('basis')=='MANUSCRIPT_CANDIDATE':
                    transferred=retained['text'];prev=retained
                if transferred and prev.get('basis')=='AUTHOR_INPUT':
                    d=self.director.patch(p,d['id'],DirectorPatch(etag=d['etag'],instruction=transferred));transferred=''
                if transferred:
                    if prev.get('basis')!='MANUSCRIPT_CANDIDATE':raise ConsoleError('续写只接受前序正文候选 / Writer handoff must be a candidate',409)
                    d=self.director.patch(p,d['id'],DirectorPatch(etag=d['etag'],draft=transferred))
                d=await self.director.control(p,d['id'],DirectorControl(etag=d['etag'],action='run',confirm_plan=True))
                operation={'kind':'director','id':d['id']};task=self.manager(p).get(d['active_task'])
            else:
                if step.kind=='local_proofread':
                    public=self.director.reviews.start(p,ReviewStart(path=row['path'],source_revision=row['revision'],mode='proofread',engine='local'))
                    row['steps'][step.id]={'status':'RUNNING','attempts':attempt.get('attempts',0)+1,'started_at':now(),'operation':{'kind':'review','id':public['review_id']}}
                    row.update(active_operation={'kind':'review','id':public['review_id']},calls=row['calls']+1)
                    settled=self._settle(p,row,None,local_ai={'backend':'local','model':'PUNCTUATION_ONLY'})
                    if settled['status']=='READY' and settled['auto_continue']:return await self._advance(p,settled,lease)
                    return settled
                else:
                    prior=next((row['steps'].get(s['id'],{}).get('result') for s in reversed(row['snapshot']['steps'][:row['index']]) if row['steps'].get(s['id'],{}).get('result',{}).get('kind')=='director'),None)
                    if not prior:raise ConsoleError('候选评审需要前序正文候选 / Review needs a prior candidate',409)
                    d=self.director.get(p,prior['id']);staged=self.director.stage(p,d['id'],__import__('app.creative.director',fromlist=['Candidate']).Candidate(etag=d['etag']))
                    public=self.director.reviews.start(p,ReviewStart(path=row['path'],candidate_id=staged['candidate']['id'],writer_context_id=row['context_id'],mode=step.review_mode,model=step.model,criteria=[goal],ai_controls=controls))
                operation={'kind':'review','id':public['review_id']};task=self.manager(p).get(public['id'])
            row['steps'][step.id]={'attempt_history':(attempt.get('attempt_history',[])+([{k:v for k,v in attempt.items() if k!='attempt_history'}] if attempt else []))[-3:],'status':'RUNNING','attempts':attempt.get('attempts',0)+1,'task_id':task.id,'operation':operation,'started_at':now()}
            row.update(status='RUNNING',active_task=task.id,active_operation=operation,calls=row['calls']+1,last_error=None,pending_notice=None,handoff='')
            saved=self.put(p,row,'runs');self.followers[(p,row['id'])]=asyncio.create_task(self._follow(p,row['id'],row['epoch'],task));return saved
    async def control(self,p,id,b,lease=None):
        with self.lock:
            row=self.get(p,id)
            if row['etag']!=b.etag:raise ConsoleError('流程已更新，请刷新后重试 / Workflow changed',409)
            if b.action=='pause':row.update(pause_requested=True,auto_continue=False);return self.put(p,row,'runs')
            if b.action=='stop':
                row.update(epoch=row['epoch']+1,auto_continue=False,pause_requested=True,status='CANCELLED')
                task_id=row.get('active_task');op=row.get('active_operation');saved=self.put(p,row,'runs')
            else:
                if row.get('active_task'):raise ConsoleError('请等待当前步骤完成或取消回执 / Step is still running',409)
                if row['index']>=len(row['snapshot']['steps']):raise ConsoleError('流程已完成，请复制新运行 / Workflow already completed',409)
                if b.action=='skip':
                    s=row['snapshot']['steps'][row['index']];row['steps'][s['id']]={'status':'SKIPPED','by':'AUTHOR','at':now()};row['index']+=1;skip_disabled(row);row['status']='COMPLETED' if row['index']>=len(row['snapshot']['steps']) else 'WAITING';return self.put(p,row,'runs')
                if not b.confirm_send:raise ConsoleError('请核对步骤、模型与资料范围后确认 / Confirm models and source scope',422)
                row.update(auto_continue=b.auto_continue,pause_requested=False,status='READY',epoch=row['epoch']+1)
                self.put(p,row,'runs')
                try:return await self._advance(p,row,lease)
                except Exception as e:self._failed(p,id,e);raise
        if task_id:
            if op and op['kind']=='world':await self.world.stop(p,op['id'],_lease=lease)
            else:await self.manager(p).cancel(task_id)
            task=self.manager(p).get(task_id)
            # Keep the task reference until cancellation actually finishes; no ghost replay.
            async def clear():
                await task.runner
                with self.lock:
                    v=self._read(p,id,'runs')
                    if v['epoch']==saved['epoch'] and v.get('active_task')==task_id:
                        step=v['snapshot']['steps'][v['index']];entry=v['steps'].setdefault(step['id'],{})
                        entry.update(status='CANCELLED',finished_at=now())
                        if op and op['kind']=='director':
                            retained=self.director.get(p,op['id'])
                            if retained.get('draft'):entry['result']={'kind':'director','id':op['id'],'revision':retained['etag'],'text':retained['draft'],'data':{'draft':retained['draft']},'basis':'MANUSCRIPT_CANDIDATE','partial':True,'ai':task.ai_metadata}
                        v.update(active_task=None,active_operation=None,status='CANCELLED');self.put(p,v,'runs')
                    if self.followers.get((p,id)) is asyncio.current_task():self.followers.pop((p,id),None)
            self.followers[(p,id)]=asyncio.create_task(clear())
        return self.get(p,id)
    def design(self,p,b):
        goal=b.goal
        prompt=('Design an editable Novel Studio workflow template only. No tools, code, files or execution. Use supplied step kinds and valid schema. World scope never needs characters or literary analysis. Every AI step defaults to model codex with no custom parameters; author will choose actual models. Source selection and approvals cannot be expanded. Prefer 2-5 bounded steps; pause_after=true, use_sources=false, use_blueprint=false. Never promise work already executed. User data: '+json.dumps({'goal':goal,'scope':b.scope,'kinds':KINDS},ensure_ascii=False))
        a=adapter(self.center,p,'scene_design',prompt,b.controls.model,role='AUTHOR',controls=b.controls,preview=True)
        self.center.control_prompt(a,prompt,schema(Definition));self.center.authorize(a,prompt)
        def complete(text):
            value=Definition.model_validate_json(text)
            if value.scope!=b.scope:raise ConsoleError('流程设计超出了所选范围 / Wrong workflow scope',422)
            for s in value.steps:
                s.pause_after=True;s.use_sources=False;s.use_blueprint=False;s.controls=RequestControls();s.model='codex'
            saved=self.save(p,Save(definition=value));return {'template_id':saved['id'],'executed':False}
        task=self.manager(p).prepared(TaskRequest(type='custom_prompt',prompt='设计流程草案（不执行）',options=TaskOptions(read_only=True,resume=False,timeout_seconds=180)),prompt,True,'workflow-design',schema(Definition),complete,adapter=a,ai_task='scene_design',application_actions=True)
        task.private_text=True;return task.public()

def routes(service):
    r=APIRouter(prefix='/api/projects/{p}/workflows')
    @r.get('')
    def listing(p:str):return service.listing(p)
    @r.post('/templates')
    def create(p:str,b:Save):return service.save(p,b)
    @r.put('/templates/{id}')
    def save(p:str,id:str,b:Save):return service.save(p,b,id)
    @r.post('/templates/{id}/archive')
    def archive(p:str,id:str,b:Control):return service.archive(p,id,b.etag)
    @r.get('/templates/{id}/export')
    def export(p:str,id:str):return Definition.model_validate(service.template(p,id)['definition']).model_dump()
    @r.post('/design')
    async def design(p:str,b:Design):return service.design(p,b)
    @r.post('/runs')
    def create_run(p:str,b:RunCreate):return service.create(p,b)
    @r.get('/runs/{id}')
    def get(p:str,id:str):return service.get(p,id)
    @r.patch('/runs/{id}')
    def edit(p:str,id:str,b:Edit):return service.edit(p,id,b)
    @r.post('/runs/{id}/control')
    async def control(p:str,id:str,b:Control,request:Request):return await service.control(p,id,b,getattr(request.state,'data_lease',None))
    return r
