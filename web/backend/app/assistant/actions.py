"""Bounded application actions over the existing domain services. No arbitrary IO."""
import copy,uuid,yaml,re
from dataclasses import dataclass
from app.errors import ConsoleError
from app.assistant import models as m
from app.roleplay.models import Create as RoleplayCreate
from app.creative.reviews import Start as LiteraryStart
from app.domain.characters import CharacterCanon
from app.author_workbench import Entry
from app.library.bible import Entity
from app.library.knowledge import LinkRequest
from app.library.storage import safe
@dataclass
class Tool:
    description:str
    schema:type
    level:int=1
    scope:str='project'
TOOLS={}
def tool(name,description,schema=m.Empty,level=1,scope='project'):
    TOOLS[name]=Tool(description,schema,level,scope)
for n,d in [('list_projects','只返回书架名称与 ID，不读取其他小说内容'),('get_active_project','查看当前小说'),('get_available_models','查看已配置模型，不读凭据')]:tool(n,d,scope='application')
for n in ['get_project_status','get_backup_status','show_project_storage']:tool(n,'查看当前小说的状态摘要')
for n,d in [('search_chapters','查找当前小说章节'),('search_characters','查找当前小说人物与草稿'),('search_world_bible','查找当前小说世界设定'),('search_references','按现有资料库索引检索明确授权的文献'),('search_entities','按现有知识中心查找实体')]:tool(n,d,m.Query)
tool('open_project','打开指定书架小说；切换项目须用户确认',m.Target,3,'application')
tool('navigate_to_page','跳转软件现有页面',m.Page)
tool('open_chapter','按全书章号打开真实正文；不存在或歧义时不能猜测',m.Chapter)
for n,d in [('open_character','打开当前小说人物卡或人物候选'),('open_entity','打开当前小说设定卡'),('open_document','打开当前小说文献')]:tool(n,d,m.Target)
tool('show_character_reference','将人物资料放入当前正文参考分栏',m.Target)
tool('create_character_draft','创建人物 Proposal 草稿，不提交 Canon/State',m.CharacterDraft,2)
tool('create_chapter_draft','创建空白章节草稿；不能覆盖已有正文',m.ChapterDraft,2)
tool('get_approved_writing_context','查询指定章节已经由作者确认且仍有效的 Writer 参考包ID；不自动创建或审批，不返回秘密与原始参考内容。',m.Chapter)
tool('start_creative_writing','调用现有创作指挥台 Quick Writer 生成单章候选，可提供最多4段明确场景要求；必须先有作者确认的同章参考包，沿用当前模型参数，需固定操作人工确认。只排队，不等待模型，不改正文。',m.CreativeWritingStart,3)
tool('read_creative_writing','查看现有创作任务真实状态、流式已收到草稿和错误；不返回 Writer 私有参考包，不把生成等同已采用。',m.CreativeWritingRead)
tool('stage_creative_writing','将已结束的创作任务保存为原有 Diff 候选，必须提供最新 etag；不自动采用，不修改正文、Canon 或 State。',m.CreativeWritingStage,2)
tool('resume_creative_writing','按最新 etag 继续现有指挥任务的未完成步骤；沿用作者当前明确模型/上下文参数，固定操作需确认，不重跑已完成步骤、不自动增加调用上限。',m.CreativeWritingStage,3)
tool('stop_creative_writing','中断指定作品创作任务，保留真实已收到的草稿；不结束其他任务，不自动重试。',m.CreativeWritingStage)
tool('stage_chapter_draft','把真实正文保存为现有 Diff 候选；长章可逐段保存：首段无 parent_id，后续 content 只填新增片段并传上次回执 parent_id；可用 insert_before 指定父候选中唯一精确原文锚点，插入前保留后文。生成新候选且保留旧版。必须提供当前原文 revision，不覆盖草稿或 Final，不提交 Canon/State。返回真实候选 ID 与字数；作者审阅后采用。',m.ChapterDraftCandidate,2)
tool('read_chapter_candidate','按明确的候选 ID 分段重开当前作品的正文候选和创作摘要；需正文权限，不代表已经采用或正式事实。',m.ChapterCandidateRead)
tool('create_world_entry_draft','创建 PENDING 世界设定候选',m.WorldDraft,2)
for n in ['create_inspiration_note','create_chapter_todo']:tool(n,'保存可恢复灵感或当前章节待办；不是 Canon',m.Note,2)
tool('propose_character_edit','产生人物修改 Proposal，绝不直接覆盖人物 Canon',m.CharacterEdit,2)
tool('propose_world_edit','另存 PENDING 设定候选，保留原设定',m.WorldEdit,2)
tool('propose_entity_link','创建 AI_PROPOSED 关联，不视为作者确认事实',m.Link,2)
tool('propose_chapter_revision','当前选段调用既有润色与 Monaco Diff；Final 始终人工确认',m.Revision,2)
tool('set_theme','修改文学主题',m.Theme,scope='application')
tool('set_editor_font_size','修改正文字号',m.Font,scope='application')
tool('set_editor_line_height','修改正文行距',m.Leading,scope='application')
tool('toggle_focus_mode','切换正文专注显示',scope='application')
tool('open_settings_section','打开指定设置分类',m.Section,scope='application')
tool('start_existing_ai_task','提交现有只读 Codex 审查工作流，不接受 Shell/State Commit',m.AITask,3)
for n in ['get_task_status','cancel_task']:tool(n,'查看或停止当前项目的任务',m.Target)
tool('create_project_backup','通过 Data Center 创建新备份，不覆盖旧备份',m.Backup,2)
tool('list_world_experiments','查看当前小说实验和模板摘要，不读取私人报告全文')
tool('create_experiment_draft','复制可运行模板为实验草稿；不确认验收，不改 Canon',m.ExperimentTemplate,2)
tool('check_experiment_configuration','校验现有实验的 Schema 和受限表达式，不运行、不改设定',m.ExperimentTarget)
tool('request_experiment_design','通过现有 AI 路由提出变量、验收或对抗方案；仅 Proposal，需作者接受',m.ExperimentDesign,2)
tool('request_experiment_run','仅请求运行已有作者确认版本；指纹不一致时拒绝',m.ExperimentRun,3)
tool('open_experiment_report','打开当前小说真实实验报告；不存在则失败',m.ExperimentReport)
tool('list_roleplay_sessions','只列当前小说角色扮演会话摘要，不读取私人对话')
tool('create_roleplay_session','用当前小说已确认人物创建模拟会话；不写 Canon，打开角色扮演页',RoleplayCreate,2)
tool('start_literary_review','复用原校审中心：proofread 中文错字病句、chapter_logic 章节逻辑、cross_chapter 检索两章原文（指定 related_paths 或 queries）、其余十二维文学评审；engine=local 只支持标点，ai 使用所选模型。只读报告，不改正文',LiteraryStart,2)
from app.automation.actions import EXTRA_ACTIONS,execute as execute_control
for name,(description,schema,level,scope) in EXTRA_ACTIONS.items():tool(name,description,schema,level,scope)
class Actions:
    def __init__(self,app,characters,character_tasks,changes,planning,manager):
        self.app=app;self.registry=app.state.registry;self.characters=characters;self.character_tasks=character_tasks;self.changes=changes;self.planning=planning;self.manager=manager
    def definitions(self):
        return [{'name':n,'description':t.description,'parameters':t.schema.model_json_schema(),'level':t.level,'scope':t.scope,'permission':['browse','draft','confirmation'][t.level-1],
                 'workbench':('automation' if n in EXTRA_ACTIONS else 'existing_application'),
                 'requires_project':t.scope=='project','read_only':n.startswith(('get_','list_','search_','read_','check_','wait_')),'modifies_draft':t.level==2,
                 'requires_confirmation':t.level==3,'undo':'existing_proposal_revision_or_trash' if t.level==2 else None,
                 'cancellable':n in {'run_python_plan','start_text_task','start_existing_ai_task','start_literary_review','request_experiment_run','request_experiment_design','wait_controlled_task'},'availability':'CONFIG_DEPENDENT' if n.startswith(('start_','request_')) else 'AVAILABLE','result_schema':{'type':'object','properties':{'ok':{'type':'boolean'},'result':{'type':'object'},'error':{'type':'object'}}}} for n,t in TOOLS.items()]
    def chapters(self,p):return self.registry.studio_workspace(p)['chapters']
    def character_summaries(self,p):
        rows=[{'id':c['canonical']['id'],'name':c['canonical']['name'],'role':c['canonical']['role'],'status':'FORMAL'} for c in self.characters.list(p)]
        ws=self.registry.workspace(p)
        for f in safe(ws.root,'metadata/domain-proposals').glob('change_*.yaml'):
            v=self.changes.get(p,f.stem)
            if v.get('status')!='PROPOSED' or v.get('kind') not in {'character_create','character_refine'}:continue
            for op in v['operations']:
                c=yaml.safe_load(op['content']);rows.append({'id':c['id'],'name':c.get('name'),'role':c.get('role'),'status':'PROPOSED','proposal_id':v['id']})
        return rows
    def stage_character(self,p,card,previous=None):
        ws=self.characters.writable(p);path=self.characters.path(card['id']);value=self.changes.stage(p,'character_refine' if previous else 'character_create',[{'path':path,'action':'write','content':yaml.safe_dump(card,allow_unicode=True,sort_keys=False)}],'AI 助手候选；需作者在既有候选审阅中接受，不自动提交。',[],{path:previous['etag'] if previous else None},lambda ops:self.character_tasks.validate(p,ops))
        return {'id':card['id'],'name':card['name'],'proposal_id':value['id'],'status':'PROPOSED','recovery':'可在候选审阅放弃','canon_changed':False,'state_changed':False}
    def execute(self,s,name,args):
        if name not in TOOLS:raise ConsoleError('操作未注册',403)
        b=TOOLS[name].schema.model_validate(args);p=s.project;t=TOOLS[name]
        if name in EXTRA_ACTIONS:
            if t.scope=='project':self.registry.get(p)
            return execute_control(self,s,name,b)
        if name in ['list_world_experiments','create_experiment_draft','check_experiment_configuration','request_experiment_design','request_experiment_run','open_experiment_report']:
            self.registry.get(p);lab=self.app.state.world_logic
            if name=='list_world_experiments':return {'experiments':[{'id':v['id'],'name':v['definition']['name'],'status':v['status'],'latest_version':v['latest_version']} for v in lab.list(p)],'templates':[{'id':v['experiment_id'],'name':v['name']} for v in lab.templates()]}
            if name=='create_experiment_draft':
                definition=next((copy.deepcopy(v) for v in lab.templates() if v['experiment_id']==b.template_id),None)
                if not definition:raise ConsoleError('实验模板不存在',404)
                definition['experiment_id']='exp_'+uuid.uuid4().hex
                if b.name:definition['name']=b.name
                row=lab.save(p,definition);return {'id':row['id'],'status':'DRAFT','canon_changed':False,'recovery':'实验草稿与 Canon 分离，可修改或保留为模板'}
            if name=='check_experiment_configuration':
                from app.world_logic.models import validate
                row=lab.get(p,b.id);validate(row['definition'])
                frozen=lab.version(p,b.id,row['latest_version']) if row['latest_version'] else None
                return {'id':b.id,'valid':True,'status':row['status'],'latest_version':row['latest_version'],'frozen_latest':{'version':frozen['version'],'fingerprint':frozen['fingerprint'],'acceptance_fingerprint':frozen['acceptance_fingerprint']} if frozen else None,'note':'配置通过不等于数学验收通过；草稿有更新时必须作者再次确认，不能猜测执行指纹。'}
            if name=='request_experiment_run':
                row=lab.version(p,b.id,b.version)
                if row['fingerprint']!=b.fingerprint:raise ConsoleError('确认版本已变化',409)
                return s.front(name,b.model_dump())
            if name=='request_experiment_design':return s.front(name,b.model_dump())
            lab.report(p,b.id);return s.front(name,b.model_dump())
        if t.scope=='project':
            if not p:raise ConsoleError('请先选择小说',422)
            self.registry.get(p)
        if name=='list_projects':
            # The bookshelf status API uses project_id and loads full book stats.
            # A software tool needs only the existing registry manifest catalog.
            with self.registry.lock:
                self.registry.scan()
                return {'projects':[{'id':id,'title':v['title']} for id,v in sorted(self.registry.rows.items()) if v['status']['phase']!='ARCHIVED']}
        if name=='list_roleplay_sessions':return {'sessions':self.app.state.roleplay.list(p)}
        if name=='create_roleplay_session':
            row=self.app.state.roleplay.create(p,b)
            receipt=s.front('navigate_to_page',{'page':'roleplay'})
            return {'session_id':row['id'],'simulation_not_canon':True,'navigation_receipt':receipt}
        if name=='start_literary_review':
            cfg=s.center.settings(s.persona,s.project)
            if b.selection and not cfg.selection:raise ConsoleError('助手未获选区访问权限',403)
            if (b.include_canon or b.character_ids) and not cfg.setting_context:raise ConsoleError('助手未获小说设定访问权限；可仅核对指定正文',403)
            if b.reference_ids and not cfg.references:raise ConsoleError('助手未获文献访问权限',403)
            if b.profile_ids and not cfg.style:raise ConsoleError('助手未获文风档案访问权限',403)
            args=b.model_dump()
            # Never let a tool silently choose a different remote provider.
            selected=s.request_model or s.settings.model
            args['model']='codex' if selected in {'codex','codex-software'} else selected
            return s.front(name,args)
        if name=='get_active_project':return {'id':p,'page':s.context.page}
        if name=='get_available_models':return self.app.state.ai_center.catalog()
        if name=='get_project_status':return {'project':p,'title':self.registry.get(p)['title'],'chapters':len(self.chapters(p)),'volumes':[{'id':v['id'],'title':v.get('title'),'number':v.get('number')} for v in self.planning.rows(p,'volume')]}
        if name=='open_project':self.registry.get(b.id);return s.front(name,{'id':b.id})
        if name=='navigate_to_page':
            if b.report_id:
                if b.page!='literary':raise ConsoleError('报告只能在原文学评审页打开',422)
                self.app.state.literary_review.get(p,b.report_id)
            return s.front(name,b.model_dump())
        if name=='open_chapter':
            rows=[c for c in self.chapters(p) if c['number']==b.number]
            if len(rows)!=1 or rows[0].get('ambiguous') or not rows[0].get('path'):raise ConsoleError('章节不存在、尚无正文或章号有歧义',409)
            return s.front(name,{'path':rows[0]['path'],'number':b.number,'project':p})
        if name in {'open_character','show_character_reference'}:
            rows=[c for c in self.character_summaries(p) if c['id']==b.id]
            if not rows:raise ConsoleError('人物不属于当前项目',404)
            return s.front(name,rows[0])
        if name=='open_entity':self.app.state.studio_tools.bible.get(p,b.id);return s.front(name,b.model_dump())
        if name=='open_document':
            self.app.state.references.get(p,'documents',b.id)
            return s.front(name,{'id':b.id,'project':p})
        if name=='search_chapters':return {'chapters':[{k:c.get(k) for k in ['number','title','path','card_id','status']} for c in self.chapters(p) if b.query.casefold() in (str(c['number'])+' '+c['title']).casefold()][:40]}
        if name=='search_characters':
            rows=[v for v in self.character_summaries(p) if b.query.casefold() in ((v['name'] or '')+' '+v['id']).casefold()][:30]
            if s.settings.setting_context:
                for v in rows:
                    if v['status']=='FORMAL':v['identity']=self.characters.get(p,v['id'])['canonical']['identity']
            return {'characters':rows,'context':'姓名与角色；身份摘要仅在明确开启当前小说设定权限时提供'}
        if name=='search_world_bible':return {'entities':[{k:v[k] for k in ['id','name','category','status']} | ({'summary':v['summary'][:1000]} if s.settings.setting_context and v['category']!='secret' else {}) for v in self.app.state.studio_tools.bible.list(p) if b.query.casefold() in (v['name']+' '+' '.join(v['aliases'])).casefold()][:30]}
        if name=='search_entities':return {'entities':[{k:v.get(k) for k in ['id','name','type','status']} for v in self.app.state.knowledge.view(p,q=b.query)['entities']][:30]}
        if name=='search_references':
            if not s.settings.references:raise ConsoleError('未授权文献内容；请在助手权限中开启后再请求',403)
            return {'results':self.app.state.references.search(p,b.query)[:10]}
        if name=='create_character_draft':
            card=CharacterCanon(id='character_'+uuid.uuid4().hex,name=b.name,identity={'summary':b.summary,'occupation':b.occupation,'age_at_start':b.age}).model_dump()
            return self.stage_character(p,card)
        if name=='propose_character_edit':
            id=b.id or s.context.character
            if not id:raise ConsoleError('当前人物不唯一，请指定人物',422)
            old=self.characters.get(p,id);card=copy.deepcopy(old['canonical'])
            for k,target in [('age','age_at_start'),('occupation','occupation'),('summary','summary')]:
                if getattr(b,k) is not None:card['identity'][target]=getattr(b,k)
            if b.name is not None:card['name']=b.name
            return self.stage_character(p,card,old)
        if name=='create_chapter_draft':
            from app.studio import DraftRequest
            value=self.registry.studio_draft(p,DraftRequest(**b.model_dump()))
            return {'path':value['path'],'recovery':'可通过现有版本/草稿管理保留与撤销','final_changed':False}
        if name=='get_approved_writing_context':
            if not s.settings.manuscript:raise ConsoleError('请先授权指定章节正文访问',403)
            rows=[c for c in self.chapters(p) if c['number']==b.number]
            if len(rows)!=1 or not rows[0].get('path') or rows[0].get('ambiguous'):raise ConsoleError('章节不存在或不唯一',409)
            writing=self.app.state.writing_assist;doc=self.app.state.studio_tools.doc(p,rows[0]['path']);results=[]
            files=sorted(self.app.state.studio_tools.local(p,'writing/context').glob('*.json'),key=lambda f:f.stat().st_mtime,reverse=True)[:30]
            for file in files:
                row=writing.get(p,'context',file.stem)
                if row.get('status')!='APPROVED' or row.get('choice',{}).get('path')!=doc['path'] or row.get('choice',{}).get('revision')!=doc['etag']:continue
                try:writing.use_context(p,row['id'],doc['path'],doc['etag'],locked=True)
                except ConsoleError:continue
                results.append({'id':row['id'],'path':doc['path'],'revision':doc['etag'],'status':'AUTHOR_APPROVED_CURRENT'})
                if len(results)>=3:break
            return {'contexts':results,'searched_recent_contexts':len(files),'exhaustive':False,'needs_author_review':not results,'next_step':'请在正文工作台的上下文预览中检查并确认本章参考包；助手不能代为审批。' if not results else None}
        if name in {'start_creative_writing','read_creative_writing','stage_creative_writing','resume_creative_writing','stop_creative_writing'}:
            if not s.settings.manuscript:raise ConsoleError('请先授权当前作品的正文与候选访问',403)
            from app.creative.director import Create,Control,Candidate,Limits,Patch,Plan,Step
            from app.studio import body_counts
            director=self.app.state.creative_director
            if name=='start_creative_writing':
                rows=[c for c in self.chapters(p) if c['number']==b.number]
                if len(rows)!=1 or rows[0].get('ambiguous') or not rows[0].get('path'):raise ConsoleError('请先明确唯一章节草稿',409)
                doc=self.app.state.studio_tools.doc(p,rows[0]['path'])
                if not doc['editable']:raise ConsoleError('正式稿请使用原有受保护修订入口',409)
                # use_context revalidates author approval, source revision and
                # knowledge filtering before any model or Director record.
                director.writing.use_context(p,b.context_id,doc['path'],doc['etag'],locked=True)
                selected=s.ai_controls.model
                controls=s.ai_controls.model_copy(deep=True);controls.parameters['timeout']=b.timeout
                from app.studio_tools import normalized,utf16_index
                original=normalized(doc);heading=re.match(r'^第[一二三四五六七八九十百千零〇0-9]+章[^\r\n]*(?:\r?\n){1,2}',original)
                prefix=len(heading.group(0)) if heading else 0;quote=original[prefix:]
                if len(quote)>16000:raise ConsoleError('当前章超过此入口的整章安全范围，请使用现有选区修订或分场景工作台',422)
                value=director.create(p,Create(path=doc['path'],revision=doc['etag'],context_id=b.context_id,goal=b.goal,goal_han=b.goal_han,mode='quick',executor=selected,commander=selected,start=utf16_index(original,prefix),end=utf16_index(original,len(original)),quote=quote,skills=['context','scene','character'],request_controls=controls,limits=Limits(max_calls=max(1,len(b.steps)),seconds=b.timeout,output_characters=b.output_characters,output_tokens=16000)))
                if b.steps or b.entry_state or b.exit_state:
                    value=director.patch(p,value['id'],Patch(etag=value['etag'],plan=Plan(summary=b.goal if len(b.goal)<=1500 else b.goal[:1499]+"…",steps=[Step(title='场景 '+str(i+1),instruction=text,scene={'entry_state':b.entry_state if i==0 else '', 'exit_state':b.exit_state if i==len(b.steps or [b.goal])-1 else ''}) for i,text in enumerate(b.steps or [b.goal])])))
                import asyncio
                future=asyncio.run_coroutine_threadsafe(director.control(p,value['id'],Control(etag=value['etag'],action='run',confirm_plan=True,auto_continue=bool(b.steps))),self.app.state.automation.loop)
                try:started=future.result(20)
                except TimeoutError:
                    future.cancel()
                    raise ConsoleError('创作启动回执超时；记录 '+value['id']+' 已保留，请先查看状态，不重复启动。',504)
                task_id=started['task']['id']
                if not hasattr(s,'controlled_tasks'):s.controlled_tasks=set()
                if not hasattr(s,'spawned_tasks'):s.spawned_tasks=set()
                s.controlled_tasks.add(task_id);s.spawned_tasks.add(task_id)
                self.app.state.automation.remember_task(s,task_id,selected)
                return {'id':started['id'],'record_id':started['id'],'task_id':started['task']['id'],'path':started['path'],'status':started['status'],'model':selected,'candidate_only':True,'manuscript_changed':False,'canon_changed':False,'state_changed':False}
            value=director.get(p,b.id)
            if name in {'resume_creative_writing','stop_creative_writing'}:
                if value['etag']!=b.etag:raise ConsoleError('创作任务版本已变化，请先查看真实状态',409)
                import asyncio
                if name=='resume_creative_writing':
                    selected=s.ai_controls.model
                    value=director.patch(p,b.id,Patch(etag=b.etag,executor=selected,request_controls=s.ai_controls))
                action='run' if name=='resume_creative_writing' else 'interrupt'
                future=asyncio.run_coroutine_threadsafe(director.control(p,b.id,Control(etag=value['etag'],action=action,confirm_plan=True,auto_continue=True)),self.app.state.automation.loop)
                try:result=future.result(20)
                except TimeoutError:
                    future.cancel();raise ConsoleError('任务控制回执超时；请先查看 '+b.id+' 的实际状态，不重复启动。',504)
                if name=='resume_creative_writing':
                    task_id=result['task']['id']
                    if not hasattr(s,'controlled_tasks'):s.controlled_tasks=set()
                    if not hasattr(s,'spawned_tasks'):s.spawned_tasks=set()
                    s.controlled_tasks.add(task_id);s.spawned_tasks.add(task_id);self.app.state.automation.remember_task(s,task_id,selected)
                return {'id':b.id,'record_id':b.id,'path':result['path'],'status':result['status'],'task_id':result.get('active_task'),'completed_steps':result['completed'],'preserved_characters':len(result.get('draft',''))+len(result.get('partial','')),'candidate_only':True,'manuscript_changed':False}
            if name=='stage_creative_writing':
                staged=director.stage(p,b.id,Candidate(etag=b.etag));row=staged['candidate']
                return {'id':row['id'],'candidate_id':row['id'],'record_id':b.id,'path':row['path'],'status':'PROPOSED','counts':body_counts(row['candidate']),'requires_author_acceptance':True,'manuscript_changed':False,'canon_changed':False,'state_changed':False}
            activity=None;task_status=None
            if value.get('active_task'):
                task=self.manager(p).get(value['active_task']);task_status=task.status
                for event in reversed(list(task.events)):
                    data=event.get('data') or {}
                    if data.get('codex_phase'):
                        activity={key:data[key] for key in ('codex_phase','phase_status','duration_ms','elapsed_ms') if key in data};break
            text=value.get('draft','')+value.get('partial','');start=min(len(text),b.start);end=min(len(text),start+b.limit)
            return {'id':b.id,'record_id':b.id,'etag':value['etag'],'path':value['path'],'status':value['status'],'task_id':value.get('active_task'),'phase':value['phase'],'task_status':task_status,'request_phase':activity,'text':text[start:end],'start':start,'end':end,'total':len(text),'partial':start!=0 or end<len(text),'counts':body_counts(text),'error':value.get('last_error'),'delivery':value.get('delivery'),'recovery':value.get('recovery'),'usage':value.get('usage',[]),'candidate_only':True,'manuscript_changed':False}
        if name=='read_chapter_candidate':
            if not s.settings.manuscript:raise ConsoleError('请先授权当前作品的正文候选读取',403)
            tools=self.app.state.studio_tools;row=tools.candidate(p,b.id)
            if row.get('project_id')!=p:raise ConsoleError('候选不属于当前作品',403)
            text=row.get('accepted_text',row.get('candidate',''));start=min(len(text),b.start);end=min(len(text),start+b.limit)
            doc=tools.doc(p,row['path'])
            return {'id':b.id,'path':row['path'],'status':row['status'],'document_revision':row['document_revision'],'source_current':doc['etag']==row['document_revision'],'text':text[start:end],'start':start,'end':end,'total':len(text),'partial':start!=0 or end<len(text),'note':row.get('review_origin',{}).get('note',''),'not_canon':True}
        if name=='stage_chapter_draft':
            if not s.settings.manuscript:raise ConsoleError('请先授权当前作品正文范围；保存候选不会自动采用',403)
            rows=[c for c in self.chapters(p) if c['number']==b.number]
            if len(rows)!=1 or rows[0].get('ambiguous') or not rows[0].get('path'):raise ConsoleError('章节不存在或章号不唯一',409)
            tools=self.app.state.studio_tools;path=rows[0]['path'];doc=tools.doc(p,path)
            if not doc['editable']:raise ConsoleError('正式稿或已提交章节不能通过草稿入口改动；请使用原有受保护修订流程',409)
            from app.studio_tools import normalized,utf16_index,utf16_slice,text_hash
            from app.studio import body_counts
            if not b.content.strip():raise ConsoleError('正文候选不能为空白',422)
            original=normalized(doc);content=b.content
            if b.parent_id:
                parent=tools.candidate(p,b.parent_id)
                if parent.get('project_id')!=p or parent.get('path')!=path or parent.get('document_revision')!=b.revision:raise ConsoleError('追加来源不属于当前章节版本',409)
                if parent.get('status')!='PROPOSED' or parent.get('author_draft'):raise ConsoleError('来源已由作者处理或编辑；请先审阅，不自动追加覆盖',409)
                if parent.get('review_origin',{}).get('kind') not in {'mcp-chapter-draft','creative-director'}:raise ConsoleError('只能延续明确的整章创作候选；局部校对候选不能当作全章',409)
                prefix_text=utf16_slice(original,0,parent['start']);suffix_text=utf16_slice(original,parent['end'],utf16_index(original,len(original)))
                if parent.get('review_origin',{}).get('kind')=='creative-director' and parent['start']==parent['end']==0 and body_counts(original)['characters']==0:
                    parent_text=original+parent['candidate']
                else:
                    if body_counts(prefix_text)['characters'] or body_counts(suffix_text,strip_header=False)['characters']:raise ConsoleError('父候选未覆盖整章正文，请使用原有选区 Diff',409)
                    parent_text=prefix_text+parent['candidate']+suffix_text
                if b.insert_before:
                    if not b.insert_before.strip() or parent_text.count(b.insert_before)!=1:raise ConsoleError('插入锚点必须在父候选中唯一精确匹配；未猜测位置',409)
                    index=parent_text.index(b.insert_before);content=parent_text[:index]+b.content+'\n\n'+parent_text[index:]
                else:content=parent_text+'\n\n'+b.content
            elif b.insert_before:raise ConsoleError('插入位置必须绑定一个明确的父候选',422)
            candidate=tools.stage_replacement(p,path,b.revision,0,utf16_index(original,len(original)),original,content,{'kind':'mcp-chapter-draft','note':b.note,'session_id':s.id,'parent_candidate_id':b.parent_id},allow_insert=True,limit=32000)
            return {'id':candidate['id'],'candidate_id':candidate['id'],'number':b.number,'path':path,'status':'PROPOSED','document_revision':candidate['document_revision'],'content_sha256':text_hash(content),'counts':body_counts(content),'requires_author_acceptance':True,'manuscript_changed':False,'canon_changed':False,'state_changed':False,'recovery':'现有候选 Diff 可重开、编辑或放弃；未覆盖正文'}
        if name in {'create_world_entry_draft','propose_world_edit'}:
            bible=self.app.state.studio_tools.bible
            if name=='propose_world_edit':
                old=bible.get(p,b.id);value={k:v for k,v in old.items() if k not in {'etag','id','version','created_at','updated_at'}};value.update(name=old['name']+' · 修改候选',summary=b.summary,source='AI_PROPOSED',status='PENDING',canon_level='REFERENCE',locked_fields=[])
            else:value={**b.model_dump(),'source':'AI_PROPOSED','status':'PENDING','canon_level':'REFERENCE'}
            v=bible.save(p,Entity(**value).model_dump());return {'id':v['id'],'name':v['name'],'status':v['status'],'original_unchanged':True,'recovery':'候选可在设定库归档'}
        if name in {'create_inspiration_note','create_chapter_todo'}:
            wb=self.app.state.workbench;row=wb.entries(p)
            if name=='create_chapter_todo' and not s.context.path:raise ConsoleError('请先打开待办所属章节',422)
            result=wb.save_entry(p,Entry(etag=row['etag'],kind='todo' if name.endswith('todo') else 'inspiration',text=b.text,path=s.context.path if name.endswith('todo') else '',source='AI_PROPOSED'))
            key='todos' if name.endswith('todo') else 'notes';v=result[key][-1];return {'id':v['id'],'canon':False,'recovery':'便笺/待办可归档或删除，已有版本检查点'}
        if name=='propose_entity_link':
            k=self.app.state.knowledge;v=k.link(p,LinkRequest(**b.model_dump(),relation_type='助手关联候选',status='AI_PROPOSED',etag=k.associations(p)['etag']))
            return {'id':v['id'],'status':'AI_PROPOSED','recovery':'关联中心可删除候选；保留原版本','canon_changed':False}
        if name=='propose_chapter_revision':
            if not s.settings.selection or not s.context.selection:raise ConsoleError('请明确授权并选择正文；不会自动发送整章',422)
            return s.front(name,{'instruction':b.instruction,'ai_model':('codex' if (s.request_model or s.settings.model) in {'codex','codex-software'} else s.request_model or s.settings.model) if s.provider.provider_id=='local-action' else s.provider.provider_id+'::'+s.model.id,'style':'default' if s.settings.style else 'none'})
        if name in {'set_theme','set_editor_font_size','set_editor_line_height','toggle_focus_mode','open_settings_section'}:return s.front(name,b.model_dump())
        if name=='start_existing_ai_task':return s.front(name,b.model_dump())
        if name in {'get_task_status','cancel_task'}:
            self.manager(p).get(b.id)
            return s.front(name,{'id':b.id})
        if name=='create_project_backup':
            v=self.app.state.data_center.backup(p,True,b.note);return {'id':v['id'],'status':v['status'],'sha256':v['sha256'],'recovery':'新建独立备份；没有覆盖旧备份'}
        if name in {'get_backup_status','show_project_storage'}:
            v=self.app.state.data_center.stats(p);return {'file_count':v['file_count'],'bytes':v['bytes'],'backups':[{'id':x['id'],'status':x['status'],'created_at':x['created_at']} for x in v['backups'][:10]]}
        raise ConsoleError('该操作暂不可用',422)
