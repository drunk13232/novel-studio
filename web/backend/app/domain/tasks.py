import copy
import json
import uuid
import yaml
from pydantic import Field
from typing import Literal
from app.errors import ConsoleError
from app.models.requests import TaskRequest,TaskOptions
from app.projects.foundation import schema
from app.projects.models import ChangeOutput
from app.domain.characters import CharacterCanon,Strict,normalize,validate_card

CHARACTER_TASKS=['character_create','character_refine','character_consistency_check','character_difference_check']
class DomainTask(Strict):
    type:str
    target:str|None=None
    character_id:str|None=None
    character_ids:list[str]=Field(default_factory=list,max_length=4)
    section:str|None=None
    instruction:str=Field(default='',max_length=8000)
    input:dict=Field(default_factory=dict)
    count:int=Field(default=3,ge=1,le=100)
    chapter_ids:list[str]=Field(default_factory=list,max_length=10)
class ReviewIssue(Strict):
    severity:str
    message:str
    evidence:list[str]
    priority:Literal['MUST FIX','SHOULD FIX','SUGGESTION','STYLE ONLY']='SUGGESTION'
    confidence:Literal['HIGH','MEDIUM','LOW']='MEDIUM'
    code:Literal['KNOWLEDGE_LEAK','UNSUPPORTED_POV','CONTINUITY','EXPOSITION','DIALOGUE','STYLE']|None=None
    paragraph:int|None=Field(default=None,ge=1)
class ReviewReport(Strict):
    verdict:str
    summary:str
    issues:list[ReviewIssue]

class CharacterTasks:
    def __init__(self,registry,characters,proposals,foundation):
        self.registry=registry;self.characters=characters;self.proposals=proposals;self.foundation=foundation
    def validate(self,project,operations):
        ws=self.registry.workspace(project)
        for op in operations:
            if op.get('action','write')!='write' or not op['path'].startswith('characters/'):raise ConsoleError('人物候选范围错误',403)
            id=op['path'].removeprefix('characters/').removesuffix('.yaml');self.characters.path(id)
            previous=normalize(ws.yaml_file(op['path'])) if (ws.root/op['path']).exists() else None
            card=validate_card(ws.parse_yaml(op['content']),id,previous)
            self.characters.references(project,card)
    def start(self,project,request,manager):
        ws=self.characters.writable(project)
        ids=request.character_ids or [request.character_id or (request.target or '').removeprefix('characters/').removesuffix('.yaml')]
        selected=[self.characters.get(project,id)['canonical'] for id in ids if id] if request.type!='character_create' else []
        if request.type=='character_difference_check' and not 2<=len(selected)<=4:raise ConsoleError('请选择 2–4 人',422)
        if request.type in ['character_refine','character_consistency_check'] and len(selected)!=1:raise ConsoleError('请选择当前人物',422)
        resources,proof=self.foundation.resources()
        context={'characters':selected,'available_characters':[r['canonical'] for r in self.characters.list(project)],'project_canon':ws.yaml_file('settings/canon-contract.yaml')}
        bases={f['path']:ws.content(f['path'])['etag'] for f in ws.list_files() if f['path'].startswith('characters/') or f['path']=='settings/canon-contract.yaml'}
        prompt=f'ACTIVE PROJECT ROOT: {ws.root}\n只读取当前项目和下列共享 Skills，不访问其他小说，不创建子 Agent，不使用 Sepia，不写正文或 State。\n'+resources+'\nCharacter Canon 与当前剧情 State 分离；所有秘密 AUTHOR ONLY，不能直接送入角色 Writer Context。\n资料：'+json.dumps(context,ensure_ascii=False)+'\n用户输入：'+json.dumps(request.input,ensure_ascii=False)+'\n要求：'+request.instruction
        if getattr(self,'research',None):
            prompt+='\n本小说 Research Index（REFERENCE MATERIAL，非 Canon，先利用已有职业/背景研究，不重复联网调查）：\n'+self.research.list(project)['index'][:8000]
        if request.type in ['character_consistency_check','character_difference_check']:
            prompt+='\n只报告，按 outputSchema 返回 verdict PASS/WARN/FAIL、summary、issues，每个问题必须给资料字段证据；相似仅是 WARN，不能自动判 FAIL。'
            def complete(text):
                report=ReviewReport.model_validate_json(text).model_dump()
                if report['verdict'] not in ['PASS','WARN','FAIL']:raise ConsoleError('审查 verdict 无效',422)
                if request.type=='character_difference_check' and report['verdict']=='FAIL':report['verdict']='WARN'
                return {**report,'skills':proof,'report_only':True}
            output=schema(ReviewReport)
        else:
            id=selected[0]['id'] if selected else 'character_'+uuid.uuid4().hex
            path=self.characters.path(id);bases[path]=ws.content(path)['etag'] if (ws.root/path).exists() else None
            template=CharacterCanon(id=id).model_dump()
            prompt+='\n返回完整候选 YAML content、explanation、lock_verdict PASS/FAIL、lock_reason；保持 id='+id+'。模板：\n'+yaml.safe_dump(template,allow_unicode=True,sort_keys=False)
            prompt+='\n字段严格遵守 CharacterCanon Schema：'+json.dumps(CharacterCanon.model_json_schema(),ensure_ascii=False)+'\nrelationships.initial 的每个值必须是 {type: [], public_state: {description: ...}, private_state: {description: ...}, history: []}，不得是字符串；没有必要的关系可留 {}。'
            if selected:prompt+='\n严格保留 HARD；局部区域为 '+str(request.section)+'，其余区域在服务器冻结。'
            if request.section and request.section not in ['personality','speech','story','appearance','psychology','behavior']:raise ConsoleError('无效人物局部区域',422)
            def complete(text):
                data=ChangeOutput.model_validate_json(text).model_dump()
                if data['lock_verdict']!='PASS':raise ConsoleError('人物锁定审查 FAIL',409)
                card=CharacterCanon.model_validate(ws.parse_yaml(data['content'])).model_dump()
                if selected and request.section:
                    merged=copy.deepcopy(selected[0]);merged[request.section]=card[request.section];card=merged
                validate_card(card,id,selected[0] if selected else None)
                ops=[{'path':path,'content':yaml.safe_dump(card,allow_unicode=True,sort_keys=False),'action':'write'}]
                return self.proposals.stage(project,request.type,ops,data['explanation'],proof,bases,lambda ops:self.validate(project,ops))
            output=schema(ChangeOutput)
        internal=TaskRequest(type=request.type,prompt=request.instruction or request.type,options=TaskOptions(read_only=True,resume=False))
        return manager.prepared(internal,prompt,True,'project-main',output,complete,target=request.character_id or request.target)
