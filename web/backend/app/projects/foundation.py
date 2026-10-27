import copy
import difflib
import hashlib
import json
import re
import uuid
from pathlib import Path
import yaml
from app.errors import ConsoleError
from app.models.requests import TaskRequest,TaskOptions
from app.projects.models import Proposal,ChangeOutput
from app.projects.service import validate_locks,write_yaml,now

TYPES=['story_architect','story_architect_refine','world_expand','character_create','character_refine','master_outline_generate','volume_outline_generate']

def schema(model):
    value=model.model_json_schema()
    def strict(node):
        if isinstance(node,dict):
            if node.get('type')=='object' and 'properties' in node:
                node['additionalProperties']=False;node['required']=list(node['properties'])
            for v in node.values():strict(v)
        elif isinstance(node,list):
            for v in node:strict(v)
    strict(value);return value

class Foundation:
    def __init__(self,engine,registry,drafts):
        self.engine=engine;self.registry=registry;self.drafts=drafts

    def resources(self):
        paths=[self.engine/'.agents/skills/novel-story-architect/SKILL.md',self.engine/'.agents/skills/web-novel-writing-skill/SKILL.md',self.engine/'.novelforge/skills/SKILL.md']
        for name in ['sw-story-structure','sw-character-conflict']:
            matches=list((self.engine/'docs/vendor/screenwriting-skills').rglob('SKILL.md'))
            p=next((p for p in matches if p.parent.name==name or p.parent.name==name.removeprefix('sw-')),None)
            if not p:raise ConsoleError('缺少共享 Screenwriting Skill：'+name,409)
            paths.append(p)
        contents=[];provenance=[]
        for p in paths:
            text=p.read_text(encoding='utf-8-sig');contents.append(f'共享 Skill 源文 {p}:\n{text}')
            provenance.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        return '\n\n'.join(contents),provenance

    def prompt(self,root,idea):
        resources,proof=self.resources()
        prompt=(f'ACTIVE PROJECT ROOT: {root}\nSHARED ENGINE ROOT: {self.engine}\n'
            '这是作者授权的基础规划任务，不写小说正文，不提交 State，不直接写正式 Canon。'
            '只读当前小说/草稿及共享 Skills。禁止读其他小说、其他草稿、用户秘密；禁止扫描 projects。'
            '使用下列真实加载的 NovelForge、novel-story-architect、Screenwriting Story Structure 和 Character/Conflict。'
            '不调用 Sepia，不启用第二主调度器，不创建子 Agent。源文内容由后端定向读取，不是伪造摘要。'
            '按照 outputSchema 只返回最终 JSON。不要写任何文件。所有 AI 设定是 AI PROPOSED。'
            'locked_constraints 是 USER LOCKED，在对应主人公/世界/结局字段逐字保留；若任何设定相冲突 lock_verdict 必须 FAIL。'
            '保留作者输入，允许 UNKNOWN/TBD；世界紧凑，人物最多主角及6个关键结构角色，宏观卷概念，不生成章纲或正文。'
            '人物自己的人生目标与叙事功能必须分别表述。不要把题材套成升级/重生等固定套路。\n'
            +resources+'\n用户输入：\n'+json.dumps(idea,ensure_ascii=False))
        from .writing_config import writing
        cfg=writing({'writing':idea.get('writing')})
        if cfg['form']!='novel':
            prompt+='\n篇幅适配规则优先于共享 Skill 的长篇建议：'+json.dumps(cfg,ensure_ascii=False)+('。只讨论作者的单篇构思；未要求的世界/人物留空或 TBD，volume_concepts 必须为空。允许开放结尾、无反转或无传统冲突，不强制人物成长。' if cfg['form']!='novella' else '。关注全篇、中段、关系与人物弧，不强制分卷；未经作者要求 volume_concepts 为空。')
        return prompt,proof

    def start_draft(self,id,request,manager):
        row=self.drafts.get(id)
        if request.version!=row['version']:raise ConsoleError('草稿版本已变化',409)
        if request.type not in ['story_architect','story_architect_refine']:raise ConsoleError('草稿仅允许 Story Architect',422)
        prompt,proof=self.prompt(self.drafts.path(id),row['input'])
        if row.get('creation'):
            from .creation import confirmed,session
            prompt+='\n作者已确认的创作档案（优先于AI推断；未填写留TBD）：'+json.dumps(confirmed(session(row)),ensure_ascii=False)
        output=schema(Proposal);section=request.section
        locks=row['input']['locked_constraints']
        output['properties']['user_locked']={'type':'object','properties':{k:{'type':'string','const':v} for k,v in locks.items()},'required':list(locks),'additionalProperties':False}
        if request.type=='story_architect_refine':
            if not row['proposal']:raise ConsoleError('需要已有 Proposal',409)
            match=re.fullmatch(r'volume_concepts\.(\d+)',section or '')
            if match:
                index=int(match[1])
                if index>=len(row['proposal']['volume_concepts']):raise ConsoleError('卷索引不存在',422)
                selected=output['$defs']['Volume']
            elif section in output['properties'] and section not in ['user_locked','lock_verdict','lock_reason']:
                selected=output['properties'][section]
            else:raise ConsoleError('不允许重做此区域',422)
            output={'type':'object','properties':{'replacement':selected,'lock_verdict':{'type':'string','enum':['PASS','FAIL']},'lock_reason':{'type':'string'}},'required':['replacement','lock_verdict','lock_reason'],'additionalProperties':False,'$defs':output.get('$defs',{})}
            prompt+='\n只重做 '+section+'，返回 replacement。其余部分被冻结，由服务器合并。原方案：\n'+json.dumps(row['proposal'],ensure_ascii=False)
        else:prompt+='\n生成完整 Project Proposal；user_locked 与 locked_constraints 精确相同。'
        prompt+='\n本次指令：'+request.instruction
        def complete(text):
            data=json.loads(text)
            if request.type=='story_architect_refine':
                if set(data)!= {'replacement','lock_verdict','lock_reason'}:raise ConsoleError('局部重做返回了额外区域',409)
                if data['lock_verdict']!='PASS':raise ConsoleError('局部重做违反 USER LOCKED：'+data['lock_reason'],409)
                proposal=copy.deepcopy(row['proposal'])
                if match:proposal['volume_concepts'][index]=data['replacement']
                else:proposal[section]=data['replacement']
            else:proposal=data
            proposal=Proposal.model_validate(proposal).model_dump();validate_locks(proposal,row['input'])
            updated=self.drafts.update(id,row['version'],proposal=proposal,accepted=False)
            if updated.get('creation'):
                from .creation import session,proposal_suggestions
                state=session(updated);proposal_suggestions(state,proposal);state['proposal_imported']=True
                state['active_task']=None
                state['proposal_snapshot']=proposal;state['proposal_stale']=False
                updated=self.drafts.update(id,updated['version'],creation=state)
            write_yaml(self.drafts.path(id)/('proposal-v'+str(updated['version'])+'.yaml'),proposal)
            return {'draft_id':id,'version':updated['version'],'proposal':proposal,'skills':proof,'section':section}
        internal=TaskRequest(type=request.type,prompt=request.instruction,options=TaskOptions(read_only=True,resume=False))
        task=manager.prepared(internal,prompt,True,'project-main',output,complete)
        if row.get('creation'):
            state=copy.deepcopy(row['creation']);state['active_task']=task.id
            row=self.drafts.update(id,row['version'],creation=state)
        return task

    def start_project(self,id,request,manager):
        if request.type in ['story_architect','story_architect_refine']:raise ConsoleError('Story Architect 在向导草稿中执行',422)
        ws=self.registry.workspace(id);m=self.registry.get(id)
        if m['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
        idea=ws.yaml_file('metadata/user-input.yaml');prompt,proof=self.prompt(ws.root,idea)
        if getattr(self,'research',None):
            prompt+='\n本项目 Research Index（REFERENCE MATERIAL，非 Canon；需要现实资料时先定向读取已有主题，缺项建议作者手动调查，不自动联网）：\n'+self.research.list(id)['index'][:8000]
        targets={'world_expand':'bible/world.md','master_outline_generate':'outlines/master-outline.md'}
        target=targets.get(request.type)
        if request.type=='character_create':target='characters/character_'+uuid.uuid4().hex[:12]+'.yaml'
        if request.type=='character_refine':
            target=request.target
            if not target or not re.fullmatch(r'characters/[a-zA-Z0-9_-]+\.yaml',target):raise ConsoleError('请选择当前小说人物文件',422)
            if not ws.resolve(target).is_file():raise ConsoleError('当前小说人物不存在',404)
        if request.type=='volume_outline_generate':
            if not request.target or not re.fullmatch(r'[1-9]\d?',request.target):raise ConsoleError('请选择卷号（1-99）',422)
            target=f'outlines/volumes/volume-{int(request.target):02}.md'
        ws.resolve(target)
        old=ws.content(target) if (ws.root/target).exists() else None
        canon=ws.content('settings/canon-contract.yaml')
        context={f['path']:ws.content(f['path'])['content'] for f in ws.list_files() if f['path'].startswith(('bible/','characters/','outlines/master','settings/')) and f['size']<50000}
        prompt+='\n当前小说定向资料：\n'+json.dumps(context,ensure_ascii=False)+'\n任务：'+request.type+'\n目标：'+target+'\n指令：'+request.instruction+'\n只返回目标文件完整候选 content、变更解释及锁定事实审查。'
        if target.startswith('characters/'):
            prompt+='\n人物卡必须采用此 YAML 模板并保持全部字段类型：\n'+(self.engine/'engine/templates/character.yaml').read_text(encoding='utf8')
            prompt+='\nid 为目标文件 basename；已有卡不得更改 id。'
        def complete(text):
            data=ChangeOutput.model_validate_json(text).model_dump()
            if data['lock_verdict']!='PASS':raise ConsoleError('锁定事实审查 FAIL：'+data['lock_reason'],409)
            self.check_change(ws,target,data['content'],idea)
            pid='change_'+uuid.uuid4().hex
            value={'id':pid,'project_id':id,'version':1,'status':'PROPOSED','target':target,'content':data['content'],'explanation':data['explanation'],
                'base_etag':old['etag'] if old else None,'canon_etag':canon['etag'],'input_etag':ws.content('metadata/user-input.yaml')['etag'],'created_at':now(),'skills':proof}
            value['diff']=''.join(difflib.unified_diff((old['content'] if old else '').replace('\r\n','\n').splitlines(True),data['content'].replace('\r\n','\n').splitlines(True),fromfile=target+' (current)',tofile=target+' (proposed)'))
            write_yaml(ws.root/'metadata/proposals'/f'{pid}.yaml',value)
            return value
        internal=TaskRequest(type=request.type,prompt=request.instruction,options=TaskOptions(read_only=True,resume=False))
        return manager.prepared(internal,prompt,True,'project-main',schema(ChangeOutput),complete)

    def check_change(self,ws,target,content,idea):
        if len(content.encode('utf8'))>ws.max_bytes:raise ConsoleError('候选过大',413)
        if target.startswith('characters/'):
            value=ws.parse_yaml(content);template=yaml.safe_load((self.engine/'engine/templates/character.yaml').read_text(encoding='utf8'))
            if not isinstance(value,dict) or set(value)!=set(template) or value.get('id')!=Path(target).stem:raise ConsoleError('人物卡 Schema / ID 不匹配',422)
            def check_types(actual,expected):
                if expected is None:return actual is None or isinstance(actual,str)
                if isinstance(expected,dict):return isinstance(actual,dict) and (not expected or set(actual)==set(expected) and all(check_types(actual[k],v) for k,v in expected.items()))
                if isinstance(expected,list):return isinstance(actual,list) and all(isinstance(x,str) for x in actual)
                return isinstance(actual,type(expected))
            if not check_types(value,template) or value['role'] not in ['PROTAGONIST','STRUCTURAL','SECONDARY']:raise ConsoleError('人物卡字段类型 / role 无效',422)
            if (ws.root/target).exists():
                previous=ws.yaml_file(target)
                if value['role']!=previous['role'] or value['canon']['locked']!=previous['canon']['locked']:raise ConsoleError('局部完善不能修改人物 role / USER LOCKED',409)
            locked=idea['locked_constraints'].get('protagonist')
            if value.get('role')=='PROTAGONIST' and locked and locked not in content:raise ConsoleError('主人公锁定原文缺失',409)
        if target=='bible/world.md' and idea['locked_constraints'].get('era') and idea['locked_constraints']['era'] not in content:raise ConsoleError('时代锁定原文缺失',409)
        if target=='outlines/master-outline.md' and idea['locked_constraints'].get('ending') and idea['locked_constraints']['ending'] not in content:raise ConsoleError('结局锁定原文缺失',409)

    def review(self,id,change):
        if not re.fullmatch(r'change_[0-9a-f]{32}',change):raise ConsoleError('无效变更 ID',403)
        ws=self.registry.workspace(id);value=ws.yaml_file(f'metadata/proposals/{change}.yaml')
        if not value or value.get('project_id')!=id:raise ConsoleError('变更不属于此项目',404)
        return value

    def accept(self,id,change,request):
        with self.registry.lock:
            value=self.review(id,change);ws=self.registry.workspace(id)
            if self.registry.get(id)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
            if value['version']!=request.version or value['status']!='PROPOSED':raise ConsoleError('变更版本/状态已变化',409)
            target=ws.resolve(value['target']);old=ws.content(value['target']) if target.exists() else None
            if (old['etag'] if old else None)!=value['base_etag'] or ws.content('settings/canon-contract.yaml')['etag']!=value['canon_etag'] or ws.content('metadata/user-input.yaml')['etag']!=value['input_etag']:raise ConsoleError('候选基线已变化；请重新生成或合并',409)
            self.check_change(ws,value['target'],value['content'],ws.yaml_file('metadata/user-input.yaml'))
            if old:
                content=value['content'].replace('\r\n','\n')
                if old['line_ending']=='CRLF':content=content.replace('\n','\r\n')
                ws.save(value['target'],content,old['etag'])
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('x',encoding='utf8') as f:f.write(value['content'])
            value['status']='ACCEPTED';value['version']+=1;write_yaml(ws.root/f'metadata/proposals/{change}.yaml',value)
            return value

    def edit(self,id,change,request):
        with self.registry.lock:
            value=self.review(id,change);ws=self.registry.workspace(id)
            if self.registry.get(id)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
            if value['version']!=request.version or value['status']!='PROPOSED':raise ConsoleError('候选已更新或结束',409)
            self.check_change(ws,value['target'],request.content,ws.yaml_file('metadata/user-input.yaml'))
            old=ws.content(value['target'])['content'] if (ws.root/value['target']).exists() else ''
            value.update(content=request.content,version=value['version']+1)
            value['diff']=''.join(difflib.unified_diff(old.replace('\r\n','\n').splitlines(True),request.content.replace('\r\n','\n').splitlines(True),fromfile=value['target']+' (current)',tofile=value['target']+' (proposed)'))
            write_yaml(ws.root/f'metadata/proposals/{change}.yaml',value)
            return value

    def discard(self,id,change,request):
        with self.registry.lock:
            value=self.review(id,change);ws=self.registry.workspace(id)
            if self.registry.get(id)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
            if value['version']!=request.version or value['status']!='PROPOSED':raise ConsoleError('候选已更新或结束',409)
            value.update(status='DISCARDED',version=value['version']+1)
            write_yaml(ws.root/f'metadata/proposals/{change}.yaml',value);return value
