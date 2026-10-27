"""Conversation/profile adapter for DraftStore and the existing Codex task manager."""
import copy
import hashlib
import json
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.errors import ConsoleError
from app.models.requests import TaskRequest, TaskOptions
from app.projects.models import Idea, Proposal
from app.projects.foundation import schema
from app.projects.service import now, write_yaml
from app.library.storage import write, safe
from app.ai.controls import RequestControls,item,receipt
from app.ai.world_start import WORLD_START_FIELDS, WORLD_START_POLICY

GROUPS = {
    '基本信息': [('title','书名'),('positioning','作品定位'),('genre','题材'),('attractions','吸引你的地方')],
    '故事核心': [('premise','核心创意'),('conflict','核心冲突'),('story_engine','故事动力'),('relationships','核心关系')],
    '人物': [('protagonist_name','主角名字'),('protagonist','主角身份'),('goal','主角目标'),('personality','性格'),('appearance','公开外貌'),('characters','主要人物')],
    '世界': [('world','世界观'),('era','时代与地点'),('power_system','世界规则'),('factions','势力'),('economy','经济体系'),('politics','政治制度')],
    '风格': [('tone','整体气质'),('pacing','节奏'),('narrative','叙事视角'),('romance','感情线'),('style','语言风格'),('themes','主题'),('visual_motifs','公开视觉意象')],
    '大纲方向': [('opening','故事开端'),('long_direction','长期方向'),('ending','结局'),('secrets','作者秘密'),('total_words','预计字数'),('estimated_chapters','预计章数'),('estimated_volumes','预计卷数')]
}
CATALOG = [{'field_id':k,'label':n,'group':g} for g,items in GROUPS.items() for k,n in items]
IDS = {r['field_id'] for r in CATALOG}
COVER_FIELDS = {'title','genre','tone','era','world','appearance','visual_motifs','style'}
CONFIRMED = {'USER_CONFIRMED','LOCKED'}

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Choice(Strict):
    label: str = Field(max_length=120)
    answer: str = Field(max_length=3000)

class Question(Strict):
    field_id: str = Field(max_length=64)
    prompt: str = Field(max_length=1500)
    options: list[Choice] = Field(default_factory=list,max_length=4)

class Suggestion(Strict):
    field_id: str = Field(max_length=64)
    value: str = Field(max_length=10000)
    source: Literal['USER','AI_INFERRED','AI_SUGGESTED']
    source_quote: str = Field(default='',max_length=10000)
    related_message_id: str = Field(default='',max_length=80)

class Concept(Strict):
    name: str = Field(max_length=120)
    description: str = Field(max_length=2000)
    prompt: str = Field(max_length=6000)
    negative: str = Field(max_length=2000)

class InterviewOutput(Strict):
    message: str = Field(min_length=1,max_length=12000)
    layer: Literal['方向','核心','世界与人物','叙事设计','世界观']
    question: Question | None = None
    suggestions: list[Suggestion] = Field(default_factory=list,max_length=34)
    issues: list[str] = Field(default_factory=list,max_length=20)
    cover_concepts: list[Concept] = Field(default_factory=list,max_length=4)

class CreationEdit(Strict):
    version: int
    action: Literal['focus','language','writing','references','description','stage','field','accept','ignore','lock','unlock','public','edit_message','proposal','buffer','clear_buffer','ai_controls','summary','memory','reply_buffer']
    writing: dict | None = None
    references: dict = Field(default_factory=dict)
    field_id: str | None = None
    value: str = Field(default='',max_length=40000)
    message_id: str | None = None
    public: bool = True
    ai_controls:RequestControls|None=None
    source_message_ids:list[str]=Field(default_factory=list,max_length=1000)

class InterviewRequest(Strict):
    version: int
    mode: Literal['interview','analyze','answer','options','reask','skip','summarize','refine','simplify','redesign','check','cover_concepts','cover_prompt'] = 'interview'
    message: str = Field(default='',max_length=12000)
    field_id: str | None = None
    choice: int | None = Field(default=None,ge=0,le=3)
    allow_spoilers: bool = False
    ai_controls:RequestControls|None=None
    preview_sha256:str|None=Field(default=None,max_length=64)

def field(k,value='',source='USER',status='EMPTY',message=''):
    return dict(field_id=k,value=value,status=status,source=source,locked=status=='LOCKED',public=k in {'title','genre','tone','era','appearance','visual_motifs','style'},updated_at=now(),related_message_id=message,suggestion=None,structured=None,edit_buffer=None)

def session(row):
    if row.get('creation'): return copy.deepcopy(row['creation'])
    fields={k:field(k) for k in IDS}
    for k,v in row['input'].items():
        if k in fields and isinstance(v,str) and v and not (k=='genre' and v=='其他'): fields[k]=field(k,v,status='USER_CONFIRMED')
    for k,v in row['input'].get('locked_constraints',{}).items():
        if k in fields and v:fields[k]=field(k,v,status='LOCKED')
    if row['input'].get('attractions'):fields['attractions']=field('attractions','\n'.join(row['input']['attractions']),status='USER_CONFIRMED')
    result=dict(focus='story',description=row['input'].get('idea',''),messages=[],stage='idea',layer='方向',fields=fields,question=None,issues=[],changes=[],cover_concepts=[],active_task=None,extraction_error=None,proposal_imported=False,skipped_fields=[],legacy_input=copy.deepcopy(row['input']))
    if row.get('proposal'):
        proposal_suggestions(result,row['proposal']);result['proposal_snapshot']=copy.deepcopy(row['proposal']);result['proposal_imported']=True
    # A never-opened draft has no persisted creation section yet. Its initial
    # source revisions must stay stable between local preview and actual send.
    for f in result['fields'].values():f['updated_at']=row.get('updated_at','')
    return result

def confirmed(s):
    return {k:f['value'] for k,f in s['fields'].items() if f['status'] in CONFIRMED and f['value']}

def project_idea(s):
    values=confirmed(s)
    if s.get('focus')=='world':values={k:v for k,v in values.items() if k in WORLD_START_FIELDS}
    old=Idea(title=values.get('title') or '未命名作品',language=s.get('writing_language') or s.get('legacy_input',{}).get('language','zh-CN')).model_dump()
    limits={'title':180,'premise':3000,'tone':1500,'romance':400,'style':4000,'total_words':120,'estimated_chapters':120,'estimated_volumes':120}
    for k in old:
        if k in values and isinstance(old[k],str):old[k]=values[k][:limits.get(k,8000)]
    old['genre']=values.get('genre','其他')[:40]
    old['pacing']=values.get('pacing','')[:40];old['narrative']=values.get('narrative','')[:40]
    old['idea']=s['description'][:8000]
    old['attractions']=[values['attractions']] if values.get('attractions') else []
    old['secondary']=copy.deepcopy(s.get('legacy_input',{}).get('secondary',[]))
    old['fanfiction']=copy.deepcopy(s.get('legacy_input',{}).get('fanfiction',{}))
    old['locked_constraints']={k:f['value'] for k,f in s['fields'].items() if k in ({'era'} if s.get('focus')=='world' else {'protagonist','era','ending'}) and f['locked'] and f['value']}
    old['writing']=s.get('writing') or s.get('legacy_input',{}).get('writing')
    return Idea.model_validate(old).model_dump()

def log(s,action,k='',before='',after=''):
    s['changes'].append(dict(at=now(),action=action,field_id=k,before=before,after=after))

class Creation:
    def __init__(self,drafts,foundation):self.drafts=drafts;self.foundation=foundation

    def view(self,id):
        row=self.drafts.get(id)
        s=session(row)
        from .writing_config import writing
        cfg=writing({'writing':s.get('writing') or row['input'].get('writing')})
        s['writing']=cfg
        compact={'title','genre','premise','protagonist_name','protagonist','goal','relationships','conflict','opening','ending','tone','style','narrative','visual_motifs','total_words'}
        return {**row,'creation':s,'catalog':[r for r in CATALOG if r['field_id'] in WORLD_START_FIELDS] if s.get('focus')=='world' else CATALOG if cfg['form']=='novel' else [r for r in CATALOG if r['field_id'] in compact or cfg['form']=='novella' and r['field_id'] in {'long_direction','characters','personality','era'}]}

    def save(self,id,row,s):
        # Preserve an already generated proposal when only UI/suggestions change.
        idea=project_idea(s)
        if idea!=row['input'] and (row.get('proposal') or s.get('proposal_snapshot')):s['proposal_stale']=True
        return self.drafts.update(id,row['version'],creation=s,**({'input':idea} if idea!=row['input'] else {}))

    def branch(self,id,version):
        """Fork visible creative discussion, never a provider-native thread or grant."""
        with self.drafts.lock:
            row=self.drafts.get(id)
            if row['version']!=version:raise ConsoleError('会话已更新，请刷新后创建分支',409)
            value=session(row);value['active_task']=None;value['extraction_error']=None
            value['branch_of']={'draft_id':id,'version':version,'at':now()}
            new=self.drafts.create(Idea.model_validate(row['input']))
            self.save(new['id'],new,value)
            return self.view(new['id'])

    def edit(self,id,request):
        with self.drafts.lock:
            row=self.drafts.get(id)
            # UI stage and next-request controls do not modify creative content.
            # Merge these two explicit metadata writes into the latest locked
            # draft; every content/acceptance/focus edit still requires its version.
            safe_metadata=request.action in {'stage','ai_controls'} and 0<=request.version<=row['version']
            if request.version!=row['version'] and not safe_metadata:raise ConsoleError('草稿已更新，请刷新后重试',409)
            s=session(row);k=request.field_id;action=request.action
            if action=='focus':
                if request.value not in {'story','world'}:raise ConsoleError('未知构思方式',422)
                if s.get('active_task'):raise ConsoleError('请先停止当前 AI 请求，再切换构思方式',409)
                if request.value!=s.get('focus','story'):
                    previous=s.get('focus','story');s.setdefault('reply_buffers',{})[previous]=s.get('reply_buffer','')
                    s['reply_buffer']=s['reply_buffers'].get(request.value,'')
                    s['focus']=request.value;s['question']=None;s['issues']=[];s['extraction_error']=None
                    s['layer']='世界观' if request.value=='world' else '方向'
            elif action=='ai_controls':
                if request.ai_controls is None:raise ConsoleError('缺少模型控制配置',422)
                s['ai_controls']=request.ai_controls.model_dump(exclude_unset=True)
            elif action=='reply_buffer':s['reply_buffer']=request.value[:12000]
            elif action in {'summary','memory'}:
                if not request.value.strip():raise ConsoleError('摘要或记忆候选不能为空',422)
                ids={m['id'] for m in s['messages']}
                if not request.source_message_ids or not set(request.source_message_ids)<=ids:raise ConsoleError('摘要来源必须属于当前会话',403)
                s.setdefault('summaries' if action=='summary' else 'memory_candidates',[]).append({'id':'summary_'+uuid.uuid4().hex,'version':len(s.get('summaries',[]))+1,'content':request.value,'source_message_ids':request.source_message_ids,'model':'AUTHOR_EDITED','at':now(),'canon':False,'focus':s.get('focus','story')})
            elif action=='language':
                from pydantic import TypeAdapter
                from app.studio import UiLocale
                s['writing_language']=TypeAdapter(UiLocale).validate_python(request.value)
            elif action=='writing':
                from .writing_config import WritingConfig
                cfg=WritingConfig.model_validate(request.writing).model_dump();cfg['body_id']=None;s['writing']=cfg
            elif action=='description':s['description']=request.value
            elif action=='references':
                library=self.references
                references={kind:list(dict.fromkeys(request.references.get(kind,[]))) for kind in ['documents','profiles']}
                if any(len(rows)>20 for rows in references.values()):raise ConsoleError('最多选择 20 项参考',422)
                for kind,rows in references.items():
                    for reference_id in rows:
                        reference=library.get('public',kind,reference_id)
                        if reference.get('trashed') or (kind=='profiles' and reference.get('status')!='USER_CONFIRMED'):raise ConsoleError('参考资料已回收或文风未确认',409)
                s['references']=references
            elif action=='stage':
                if request.value not in {'idea','interview','profile','cover','create'}:raise ConsoleError('未知创作阶段',422)
                s['stage']=request.value
            elif action=='edit_message':
                m=next((m for m in s['messages'] if m['id']==request.message_id and m['role']=='user'),None)
                if not m:raise ConsoleError('这条作者回答不存在',404)
                log(s,action,m['id'],m['content'],request.value);m['content']=request.value
                for f in s['fields'].values():
                    if f['related_message_id']==m['id'] and not f['locked']:
                        f.update(status='AI_SUGGESTED',source='AI_INFERRED',suggestion=None)
                s['issues']=['回答已修改；关联的未锁定信息需要重新确认。']
            elif action=='proposal':
                if not row.get('proposal'):raise ConsoleError('尚无初始方案',409)
                proposal_suggestions(s,row['proposal']);s['proposal_imported']=True
            else:
                if k not in IDS:raise ConsoleError('未知设定字段',422)
                f=s['fields'][k];before=f['value']
                if action in {'field','accept','ignore','buffer'} and f['locked']:raise ConsoleError('先明确解锁，再修改此设定',409)
                if action=='buffer':f['edit_buffer']=request.value
                elif action=='clear_buffer':f['edit_buffer']=None
                elif action=='field':f.update(value=request.value,status='USER_CONFIRMED' if request.value.strip() else 'EMPTY',source='USER',suggestion=None,structured=None,related_message_id='',edit_buffer=None)
                elif action=='accept':
                    sug=f['suggestion']
                    if sug:f.update(value=sug['value'],source=sug['source'],status='USER_CONFIRMED',related_message_id=sug.get('related_message_id',''),structured=sug.get('structured'),suggestion=None)
                    elif f['status']=='AI_SUGGESTED':f['status']='USER_CONFIRMED'
                elif action=='ignore':
                    f['suggestion']=None
                    if f['status']=='AI_SUGGESTED':f.update(value='',status='EMPTY',structured=None)
                elif action=='lock':
                    if f['status'] not in CONFIRMED or not f['value']:raise ConsoleError('先确认设定，才能锁定',409)
                    f.update(locked=True,status='LOCKED',suggestion=None)
                elif action=='unlock':f.update(locked=False,status='USER_CONFIRMED')
                elif action=='public':f['public']=request.public
                f['updated_at']=now();log(s,action,k,before,f['value'])
            self.save(id,row,s)
            return self.view(id)

    def start(self,id,request,manager,*,preview=False):
        with self.drafts.lock:
            row=self.drafts.get(id)
            if request.version!=row['version']:raise ConsoleError('草稿已更新',409)
            s=session(row);k=request.field_id
            world_first=s.get('focus')=='world' and not request.mode.startswith('cover_')
            allowed_fields=WORLD_START_FIELDS if world_first else IDS
            previous_messages={m['id'] for m in s['messages']}
            if not preview and s.get('active_task'):
                try:active=manager.get(s['active_task'])
                except ConsoleError:active=None
                if active and active.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:raise ConsoleError('本会话已有生成中请求；可编辑下一轮设置或停止当前请求',409)
            if request.mode=='skip' and s.get('question'):
                s.setdefault('skipped_fields',[]).append(s['question']['field_id']);s['question']=None
            if k and k not in allowed_fields:raise ConsoleError('此构思方式不包含这个字段',422)
            if k and s['fields'][k]['locked'] and request.mode not in {'check'}:raise ConsoleError('锁定字段不能重新生成',409)
            text=request.message
            if request.choice is not None:
                q=s.get('question')
                if not q or q['field_id'] not in allowed_fields or request.choice>=len(q['options']):raise ConsoleError('候选方案已变化',409)
                text=q['options'][request.choice]['answer'];k=q['field_id']
                f=s['fields'][k]
                if not f['locked']:f.update(value=text,status='USER_CONFIRMED',source='USER',suggestion=None,structured=None)
            if not s['messages'] and s['description']:
                s['messages'].append(dict(id='msg_'+uuid.uuid4().hex,role='user',content=s['description'],timestamp=now(),focus=s.get('focus','story')))
            if text:s['messages'].append(dict(id='msg_'+uuid.uuid4().hex,role='user',content=text,timestamp=now(),focus=s.get('focus','story')))
            if text:s['reply_buffer']=''
            s['stage']='cover' if request.mode.startswith('cover_') else 'interview' if s['stage']=='idea' else s['stage']
            s['extraction_error']=None
            updated=row # Defer persistence until provider consent and credentials pass.
        # Cover AI receives a smaller, explicitly public package, never the interview history.
        is_cover=request.mode.startswith('cover_')
        package={k:f['value'] for k,f in s['fields'].items() if f['status'] in CONFIRMED and f['value'] and ((k in COVER_FIELDS and f['public']) or request.allow_spoilers)} if is_cover else s
        path=self.drafts.engine/'.agents/skills/novel-story-architect/SKILL.md'
        skill='' if world_first else path.read_text(encoding='utf-8-sig')
        proof={'kind':'built_in_world_first_policy','sha256':hashlib.sha256(WORLD_START_POLICY.encode()).hexdigest()} if world_first else {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        prompt=(f'ACTIVE DRAFT: {self.drafts.path(id)}\n共享 Story Architect Skill:\n{skill}\n'
          '你负责与作者合作构思，不写正文、不写文件、不调用工具、不创建Agent、不读其他项目。返回 outputSchema JSON，message 是适合聊天的自然中文。'
          '循序方向→核心→世界人物→叙事，每轮一个关键问题，最多两个；不要重复已确认内容。留白合理，现实作品不问修炼体系。'
          'question.field_id 必须来自字段目录，已确认/锁定字段不要再问。options 为2～4个有区别的可选答案（允许不提供）。'
          'skipped_fields 是作者决定暂时留白的字段，不继续追问。edit_buffer 是尚未确认的编辑暂存，不作为确认事实。'
          '未选方案只属于 AI_SUGGESTED；不能把推断包装成作者原话。明确原话可用source=USER，但source_quote必须逐字等于value且存在于相关用户消息，related_message_id必须指向该消息。归纳改写用AI_INFERRED。'
          '锁定/确认内容不能自动覆盖；需要修改时只提出候选并说明矛盾。未知保留EMPTY，不编造结局或秘密。'
          '局部任务仅返回目标字段的suggestions；options模式给3个方案；check只报告矛盾、不改设定。'
          '封面模式只读取下方公开包，不补写隐藏身份/结局，不画准确中文文字；生成2～4种背景概念，每种给prompt和negative，文字由软件独立排版。'
          '\n字段目录：'+json.dumps(CATALOG,ensure_ascii=False)+'\n模式：'+request.mode+'\n目标字段：'+str(k)+'\n当前资料：'+json.dumps(package,ensure_ascii=False))
        from .writing_config import writing
        cfg=writing({'writing':s.get('writing') or row['input'].get('writing')})
        prompt+='\n篇幅设置（作者决定，不得擅自切换）：'+json.dumps(cfg,ensure_ascii=False)
        if cfg['form'] in {'short','undecided'}:prompt+='\n采用轻量短篇访谈：描写什么、核心人物/事件、读者感受、结尾想法；允许跳过。除非作者需要，不问国家制度、世界历史、多卷或大量关系；提供3个方向也可以自由/日常/开放结尾。不生成正文。'
        elif cfg['form']=='novella':prompt+='\n中篇访谈关注目标、人物变化、关系、中段、结局和章节组织；不强制卷纲。'
        elif cfg['form']=='anthology':prompt+='\n合集仅讨论作品定位、排序、前言与风格差异，不创建各篇正文或共享秘密。'
        prompt+='\nProject writing language: '+row['input'].get('language','zh-CN')+'. Preserve user names and reference excerpts in their original language. Do not translate existing content unless explicitly requested.'
        prompt+='\n访谈深度：'+cfg['interview_depth']+'；quick只问最关键的一个问题，standard适量，deep按作者意愿深入，不要求填满。篇幅范围仅软件建议，微型作品也可以用短篇。'
        if is_cover and text:prompt+='\n作者本次明确补充（是否剧透由作者授权）：'+text
        if world_first:
            package={'focus':'world','description':s['description'],'fields':{fid:v for fid,v in s['fields'].items() if fid in WORLD_START_FIELDS},'messages':[m for m in s['messages'] if m.get('focus','story')=='world'],'skipped_fields':[fid for fid in s.get('skipped_fields',[]) if fid in WORLD_START_FIELDS]}
            prompt=(WORLD_START_POLICY+'\nReturn outputSchema JSON. message presents the actual setting draft. layer must be 世界观. '
                    'suggestions and question.field_id may only use the supplied world fields. Use AI_SUGGESTED for creative additions; '
                    'USER requires an exact source_quote and related_message_id from an actual supplied user message. '
                    'Confirmed and locked values are preserved; propose edits instead of replacing them. '
                    'For refine/simplify/redesign affect only the selected field; check only reports issues. '
                    'question may be null; at most one necessary question. No cover concepts. '
                    '\nWorld fields: '+json.dumps([c for c in CATALOG if c['field_id'] in WORLD_START_FIELDS],ensure_ascii=False)+
                    '\nMode: '+request.mode+'\nTarget: '+str(k)+'\nOutput language: '+row['input'].get('language','zh-CN')+
                    '\nUntrusted author data: '+json.dumps(package,ensure_ascii=False))
        ai_task='world' if world_first else 'interview'
        center=getattr(manager,'ai_center',None)
        if center is None:raise ConsoleError('AI 控制服务不可用；作者草稿仍可编辑',503)
        controls=center.controls_for(id,ai_task,id,request.ai_controls)
        # Decompose the exact former package, keeping only selected sources.
        # Native provider threads are never reused; visible history is portable.
        policy=prompt.replace(json.dumps(package,ensure_ascii=False),'（见下方按来源筛选的资料）',1)
        if skill:policy=policy.replace(skill,'（专业方法见独立 Skills 来源）',1)
        sources=[item('instructions','task','本次任务、字段目录与创作设置',policy,required=True),
                 item('message','instruction','当前作者指令',text or s['description'] or request.mode,required=True)]
        if skill:sources.append(item('skill:story-architect','skills','Story Architect 专业方法',skill,source='.agents/skills/novel-story-architect/SKILL.md',revision=proof['sha256'],priority=75))
        if not is_cover:
            if s['description'] and s['description']!=text:sources.append(item('idea','project','初始创作想法',s['description'],revision=row['version'],priority=70))
            for fid,f in s['fields'].items():
                if fid in allowed_fields and (f['value'] or f.get('edit_buffer')):
                    sources.append(item('field:'+fid,'world' if fid in {'world','era','power_system','factions','economy','politics'} else 'characters' if fid in {'protagonist','protagonist_name','characters','goal','personality','appearance','relationships'} else 'project',next(c['label'] for c in CATALOG if c['field_id']==fid),json.dumps({key:f.get(key) for key in ['value','status','source','edit_buffer']},ensure_ascii=False),locked=f['locked'],revision=f['updated_at'],priority=80 if f['status'] in CONFIRMED else 30))
            for m in s['messages']:
                if m['id'] not in previous_messages or world_first and m.get('focus','story')!='world':continue
                if m==s['messages'][-1] and m['role']=='user' and m['content']==text:continue
                sources.append(item(m['id'],'history',('作者' if m['role']=='user' else 'AI')+' · '+m.get('timestamp',''),m['content'],source=m.get('ai',{}).get('request_model','AUTHOR' if m['role']=='user' else 'UNKNOWN'),revision=m.get('timestamp',''),role=m['role']))
            for summary in s.get('summaries',[]):
                if world_first and summary.get('focus','story')!='world':continue
                sources.append(item(summary['id'],'history','作者可编辑历史摘要 v'+str(summary['version']),summary['content'],source=summary['model'],revision=summary['version'],summarized=True,source_message_ids=summary['source_message_ids'],priority=65))
        else:
            for fid,value in package.items():sources.append(item('field:'+fid,'project',fid,value,revision=row['version']))
        from app.creative.tasks import adapter as text_adapter,metadata
        a=text_adapter(center,id,ai_task,prompt,controls.model,role='AUTHOR',controls=controls,preview=True)
        a.source_items=sources
        output_schema=schema(InterviewOutput)
        if world_first:
            for name in ('Suggestion','Question'):output_schema['$defs'][name]['properties']['field_id']['enum']=sorted(WORLD_START_FIELDS)
            output_schema['properties']['layer']['enum']=['世界观']
        packet_prompt=center.control_prompt(a,prompt,output_schema,sources)
        packet=a.context_preview
        if preview:return {**packet,'model':controls.model,'parameters':controls.parameters,'draft_version':row['version'],'local_only':True}
        if request.preview_sha256 and packet['prompt_sha256']!=request.preview_sha256:raise ConsoleError('上下文已变化，请重新预览后发送',409)
        center.authorize(a,packet_prompt)
        s['ai_controls']=controls.model_dump()
        input_version=row['version'];input_fields=copy.deepcopy(s['fields'])
        internal=TaskRequest(type='creation_interview',options=TaskOptions(read_only=True,resume=False,timeout_seconds=max(30,controls.parameters.get('timeout',600))))
        def complete(output):
            with self.drafts.lock:
                current=self.drafts.get(id);state=session(current)
                stale=(state['fields']!=input_fields or state['description']!=s['description'] or state.get('writing')!=s.get('writing') or
                       [(m['id'],m['content']) for m in state['messages']]!=[(m['id'],m['content']) for m in s['messages']])
                message_id='msg_'+uuid.uuid4().hex
                try:
                    data=InterviewOutput.model_validate_json(output).model_dump()
                    if any(x['field_id'] not in allowed_fields for x in data['suggestions']) or data['question'] and data['question']['field_id'] not in allowed_fields:raise ValueError('未知字段')
                    if state.get('focus','story')!=s.get('focus','story'):raise ValueError('构思方式已切换，旧结果未应用')
                    if world_first and data['cover_concepts']:raise ValueError('世界观起步不生成封面或人物')
                    if is_cover and not 2<=len(data['cover_concepts'])<=4:raise ValueError('封面需要2～4个方向')
                    natural=data['message'];state['layer']=data['layer'];state['issues']=data['issues']
                    if not is_cover:
                        question=data['question']
                        state['question']=question if question and (state['fields'][question['field_id']]['status'] not in CONFIRMED or request.mode=='options' and request.field_id==question['field_id']) and question['field_id'] not in state.get('skipped_fields',[]) else None
                        for sug in data['suggestions']:
                            fid=sug['field_id']
                            if request.mode=='check' or (request.field_id and fid!=request.field_id):continue
                            f=state['fields'][fid]
                            if f!=input_fields[fid]:
                                if f.get('value')!=sug['value']:state['issues'].append('作者在生成期间更新了'+next(x['label'] for x in CATALOG if x['field_id']==fid)+'；旧结果未覆盖新编辑。')
                                continue
                            exact=any(m['role']=='user' and m['id']==sug['related_message_id'] and sug['value']==sug['source_quote'] and sug['value'] in m['content'] for m in state['messages'])
                            if f['locked']:
                                if f['value']!=sug['value']:state['issues'].append('AI 提议涉及已锁定字段：'+next(x['label'] for x in CATALOG if x['field_id']==fid))
                                continue
                            if f['status'] in CONFIRMED:
                                if f['value']!=sug['value']:f['suggestion']={**sug,'source':'AI_INFERRED' if sug['source']=='USER' else sug['source']}
                            elif sug['source']=='USER' and exact:f.update(value=sug['value'],status='USER_CONFIRMED',source='USER',suggestion=None,related_message_id=sug['related_message_id'])
                            else:f.update(value=sug['value'],status='AI_SUGGESTED',source='AI_INFERRED' if sug['source']=='USER' else sug['source'],related_message_id=sug['related_message_id'],suggestion=None)
                            f['updated_at']=now();log(state,'AI提取',fid,'',sug['value'])
                    else:state['cover_concepts']=data['cover_concepts']
                    state['extraction_error']=None
                except (ValueError,TypeError) as e:
                    try:natural=json.loads(output).get('message',output)
                    except (ValueError,AttributeError):natural=output
                    state['extraction_error']='结构化提取失败；对话已保留，可重试。'+str(e)[:300]
                state['messages'].append(dict(id=message_id,role='assistant',content=str(natural),timestamp=now(),ai=metadata(a),input_version=input_version,possibly_stale=stale,focus=s.get('focus','story'),context=receipt(packet)))
                state['active_task']=None
                self.save(id,current,state)
                return {'draft_id':id,'schema_ok':not state['extraction_error'],'message':natural,'skill':proof}
        with self.drafts.lock:self.save(id,row,s)
        def finished(task):
            if task.status=='SUCCEEDED':return
            with self.drafts.lock:
                current=self.drafts.get(id);state=session(current)
                if state.get('active_task')!=task.id:return
                partial=(task.result or {}).get('partial_output','')
                if partial:
                    import re
                    found=re.search(r'"message"\s*:\s*"((?:\\.|[^"\\])*)',partial,re.S)
                    try:natural=json.loads('"'+found[1]+'"') if found else partial
                    except ValueError:natural=partial
                    state['messages'].append({'id':'msg_'+uuid.uuid4().hex,'role':'assistant','content':natural,'raw_partial':partial,'timestamp':now(),'status':task.status,'ai':metadata(a),'input_version':input_version,'possibly_stale':True,'focus':s.get('focus','story')})
                state['active_task']=None;state['extraction_error']=task.error or '本次生成已停止；原始记录和已生成片段保留。'
                self.save(id,current,state)
        task=manager.prepared(internal,prompt,True,'project-main',output_schema,complete,adapter=a,ai_task=ai_task,application_actions=True,finished=finished)
        task.private_text=True
        current=self.drafts.get(id);s=session(current);s['active_task']=task.id
        self.save(id,current,s)
        return task

def proposal_suggestions(s,p):
    values={'premise':p['premise'],'conflict':p['core_conflict'],'story_engine':p['story_engine'],'themes':p['themes'],'world':p['world_concept'],'power_system':p['power_or_rule_system'],'factions':p['major_factions'],'protagonist':p['protagonist_concept'],'characters':p['major_character_roles'],'long_direction':{'macro_structure':p['macro_structure'],'volume_concepts':p['volume_concepts'],'reader_promises':p['reader_promises']}}
    for k,v in values.items():
        if not v:continue
        f=s['fields'][k]
        if f['locked']:continue
        if isinstance(v,str):value=v
        elif k=='protagonist':value='；'.join(label+'：'+v[key] for key,label in [('name','姓名'),('identity','身份'),('personality','性格'),('core_desire','目标'),('fear','恐惧'),('story_function','故事功能'),('arc','成长方向')])
        elif k=='characters':value='\n'.join(c['name']+'：'+c['identity']+'；目标：'+c['core_desire'] for c in v)
        elif k=='long_direction':value='\n'.join(label+'：'+v['macro_structure'][key] for key,label in [('opening','开端'),('development','发展'),('midpoint','中段'),('escalation','升级'),('climax','高潮'),('ending_direction','结局方向')])+'\n'+'\n'.join('卷概念：'+c['title']+'，'+c['function'] for c in v['volume_concepts'])
        else:value='；'.join(v)
        sug=dict(value=value,source='AI_SUGGESTED',related_message_id='',structured=v if not isinstance(v,str) else None)
        if f['status'] in CONFIRMED:f['suggestion']=sug
        else:f.update(value=value,status='AI_SUGGESTED',source='AI_SUGGESTED',structured=sug['structured'])

def reviewed_proposal(row):
    """Use only accepted field payloads; planning is never submitted as events."""
    s=session(row);v=confirmed(s);f=s['fields']
    character={k:'TBD' for k in ['name','identity','personality','core_desire','fear','story_function','arc']}
    if f['protagonist']['status'] in CONFIRMED and isinstance(f['protagonist'].get('structured'),dict):character.update(f['protagonist']['structured'])
    else:character['identity']=v.get('protagonist','TBD')
    if row['input']['locked_constraints'].get('protagonist'):character['identity']=v['protagonist']
    for key,fromkey in [('name','protagonist_name'),('core_desire','goal'),('personality','personality')]:
        if fromkey in v:character[key]=v[fromkey]
    macro={k:'TBD' for k in ['opening','development','midpoint','escalation','climax','ending_direction']};volumes=[];promises=[]
    direction=f['long_direction'].get('structured') if f['long_direction']['status'] in CONFIRMED else None
    if isinstance(direction,dict):macro.update(direction['macro_structure']);volumes=direction['volume_concepts'];promises=direction['reader_promises']
    macro['opening']=v.get('opening',macro['opening']);macro['ending_direction']=v.get('ending',macro['ending_direction'])
    return Proposal.model_validate(dict(premise=v.get('premise','TBD'),core_conflict=v.get('conflict','TBD'),story_engine=v.get('story_engine','TBD'),themes=[v['themes']] if v.get('themes') else [],reader_promises=promises,protagonist_concept=character,major_character_roles=f['characters'].get('structured') or [] if f['characters']['status'] in CONFIRMED else [],world_concept=v.get('world','TBD'),power_or_rule_system=v.get('power_system','TBD'),major_factions=[v['factions']] if v.get('factions') else [],macro_structure=macro,volume_concepts=volumes,risks=[],open_questions=[x['label']+'：待完善' for x in CATALOG if f[x['field_id']]['status'] not in CONFIRMED],user_locked=row['input']['locked_constraints'],lock_verdict='PASS',lock_reason='仅提交作者确认字段')).model_dump()

def initialize_profile(p,row):
    s=session(row);v=confirmed(s)
    world_first=s.get('focus')=='world'
    if world_first:v={k:value for k,value in v.items() if k in WORLD_START_FIELDS}
    write(safe(p,'metadata/creation-profile.json'),s)
    world=p/'bible/world.md'
    with world.open('a',encoding='utf8') as stream:
        facets=[('era','作者确认的时代与地点'),('economy','作者确认的经济体系'),('politics','作者确认的政治制度')]
        if world_first:facets=[('world','作者确认的世界观'),('power_system','作者确认的世界规则'),('factions','作者确认的组织与势力')]+facets
        for k,label in facets:
            if v.get(k):stream.write('\n## '+label+'\n\n'+v[k]+'\n')
    if not world_first and v.get('long_direction') and not s['fields']['long_direction'].get('structured'):
        with (p/'outlines/master-outline.md').open('a',encoding='utf8') as stream:stream.write('\n## 作者确认的长期方向（规划，非已发生事件）\n\n'+v['long_direction']+'\n')
    # Extra confirmed world facets use the existing Bible schema, without becoming facts in State.
    from app.library.bible import Entity
    for k,category in [('world','overview'),('era','era'),('economy','economy'),('politics','government'),('power_system','nature')]:
        if k not in v:continue
        id='entity_'+uuid.uuid4().hex
        e=Entity(id=id,name=next(x['label'] for x in CATALOG if x['field_id']==k),category=category,summary=v[k][:4000],details=v[k],source='USER',status='FORMAL',canon_level='SOFT',version=1,created_at=now(),updated_at=now()).model_dump()
        write(safe(p,'bible/entities/'+id+'.json'),e)
    import yaml
    canon=yaml.safe_load((p/'settings/canon-contract.yaml').read_text(encoding='utf8'))
    sources=yaml.safe_load((p/'metadata/canon-sources.yaml').read_text(encoding='utf8'))
    mapping={'premise':'premise','core_conflict':'conflict','power_or_rule_system':'power_system'}
    canon['strong']=[r for r in canon['strong'] if not r['id'].startswith('proposal_') or s['fields'][mapping[r['id'].removeprefix('proposal_')]]['status'] in CONFIRMED]
    sources={k:r for k,r in sources.items() if not k.startswith('proposal_') or any(x['id']==k for x in canon['strong'])}
    for key,field_id in mapping.items():
        rid='proposal_'+key
        if rid in sources:sources[rid].update(source='author_confirmed_profile',field_id=field_id,original_source=s['fields'][field_id]['source'],status=s['fields'][field_id]['status'])
    for k,f in s['fields'].items():
        if world_first and k not in WORLD_START_FIELDS:continue
        if f['locked'] and k not in {'title','genre','tone','style','pacing','narrative','romance','total_words','estimated_chapters','estimated_volumes','protagonist','era','ending'}:
            rid='profile_'+k;canon['hard'].append(dict(id=rid,statement=f['value'],check='manual',writer_view=[]));sources[rid]=dict(source='author_confirmed_profile',priority='HARD',scope=k)
    write_yaml(p/'settings/canon-contract.yaml',canon);write_yaml(p/'metadata/canon-sources.yaml',sources)
