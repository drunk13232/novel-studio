import hashlib,json,uuid
from pydantic import Field
from app.errors import ConsoleError
from app.domain.characters import Strict,Text
from app.domain.tasks import ReviewReport
from app.domain.planning import Volume,ChapterCard,dump
from app.projects.models import ChangeOutput
from app.projects.foundation import schema
from app.models.requests import TaskRequest,TaskOptions

PLANNING_TASKS=['chapter_light','volume_outline_generate','volume_outline_refine','chapter_skeleton_generate','chapter_cards_deepen','chapter_plan_refine','chapter_plan_review']
class Skeleton(Strict):
    title:Text=None
    chapter_goal:str
    conflict:str
    turn:str
    outcome:str
class SkeletonOutput(Strict):
    chapters:list[Skeleton]=Field(min_length=1,max_length=100)
    explanation:str

class PlanningTasks:
    def __init__(self,registry,planning,characters,proposals,foundation):
        self.registry=registry;self.planning=planning;self.characters=characters;self.proposals=proposals;self.foundation=foundation
    def start(self,project,request,manager):
        ws=self.characters.writable(project);kind=request.type;board=self.planning.board(project,request.target)
        resources,proof=self.foundation.resources()
        scene_path=self.foundation.engine/'docs/vendor/screenwriting-skills/plugins/screenwriting/skills/sw-scene-craft/SKILL.md'
        resources+='\n共享 Scene Craft 源文：'+str(scene_path)+'\n'+scene_path.read_text(encoding='utf-8-sig');proof.append({'path':str(scene_path),'sha256':hashlib.sha256(scene_path.read_bytes()).hexdigest()})
        volume=self.planning.get(project,request.target,'volume')['value'] if request.target else None
        if kind not in ['volume_outline_generate'] and not volume:raise ConsoleError('请选择已接受的卷纲',422)
        selected=[self.planning.get(project,id,'chapter')['value'] for id in request.chapter_ids]
        if any(c['volume']!=request.target for c in selected):raise ConsoleError('只能深化当前卷的章节',422)
        if kind in ['chapter_cards_deepen','chapter_plan_refine'] and not 1<=len(selected)<=10:raise ConsoleError('每批选择 1–10 章；通常 5–10，fixture 可选 3',422)
        if kind=='chapter_skeleton_generate' and board['chapters']:raise ConsoleError('当前卷已有骨架，请使用深化、增删、合并或拆分',409)
        bases=self.planning.bases(project)
        context={'master_outline':ws.content('outlines/master-outline.md')['content'],'canon':ws.yaml_file('settings/canon-contract.yaml'),'characters':[r['canonical'] for r in self.characters.list(project)],'volume':volume,'chapters':board['chapters'],'selected':selected,'foreshadowing':board['foreshadowing'],'threads':board['threads'],'timeline_warnings':board['warnings'],'current_story_state':ws.yaml_file('state/current-story-state.yaml'),'runtime_characters':{r['canonical']['id']:r['runtime'] for r in self.characters.list(project)},'knowledge_state':ws.yaml_file('state/knowledge-state.yaml')}
        prompt=(f'ACTIVE PROJECT ROOT: {ws.root}\n这是 V0.5 规划，不写正文，不写文件，不改 State。Outline ≠ Fact；计划死亡不改变 alive；预期知识不等于 Known。只读当前小说及提供的共享 Skills；不读其他项目，不创建子 Agent，不用 Sepia。\n'+resources+'\n资料：'+json.dumps(context,ensure_ascii=False)+'\n用户要求：'+request.instruction+'\n用户输入：'+json.dumps(request.input,ensure_ascii=False))
        prompt+='\n重点范围：'+str(request.section)+'；仅检查所选章节时以 selected 为主体，全卷资料作背景。'
        prompt+='\n检查冲突升级、节奏变化、主线/人物弧/关系、伏笔节奏、高潮位置，避免流水账。节奏采用 sw-scene-craft 的“进出与节奏”以及 sw-story-structure，不假称独立 Pacing Skill。'
        if kind=='chapter_plan_review':
            prompt+='\n只报告 PASS/WARN/FAIL、summary、issues 字段及证据。检查连续无预期变化、重复冲突/地点/结尾、人物长期不推进、中段塌陷、高潮时机、未标倒叙；正常 FLASHBACK 不作错误。修改建议写报告，不能附带文件操作。'
            def complete(text):
                result=ReviewReport.model_validate_json(text).model_dump()
                if result['verdict'] not in ['PASS','WARN','FAIL']:raise ConsoleError('无效审查 verdict',422)
                return {**result,'report_only':True,'skills':proof}
            output=schema(ReviewReport)
        elif kind=='chapter_skeleton_generate':
            prompt+=f'\n输出恰好 {request.count} 章紧凑 Skeleton，仅 title / chapter_goal / conflict / turn / outcome，每项一短句，无 Scene Card。作者接受后才深化。'
            output=schema(SkeletonOutput);output['properties']['chapters'].update(minItems=request.count,maxItems=request.count)
            def complete(text):
                result=SkeletonOutput.model_validate_json(text).model_dump()
                if len(result['chapters'])!=request.count:raise ConsoleError('骨架章数不符',422)
                ops=[]
                for n,row in enumerate(result['chapters'],1):
                    card=ChapterCard(id='chapter_'+uuid.uuid4().hex,number=n,order=n,volume=volume['id'],status='PLANNED',**row).model_dump()
                    path=self.planning.path(card['id'],'chapter');bases[path]=None;ops.append({'path':path,'content':dump(card),'action':'write'})
                return self.proposals.stage(project,kind,ops,result['explanation'],proof,bases,lambda ops:self.planning.validate(project,ops))
        else:
            output=schema(ChangeOutput)
            if kind in ['volume_outline_generate','volume_outline_refine']:
                id=volume['id'] if volume else 'volume_'+uuid.uuid4().hex
                template=volume or Volume(id=id,number=max([v['number'] for v in self.planning.rows(project,'volume')]+[0])+1,status='PLANNED').model_dump()
                prompt+='\n输出 content 为一个完整 Volume YAML；explanation / lock_verdict PASS/FAIL / lock_reason。保持 id 与 number，新卷 PLANNED，已有卷保持模板 status。模板：'+dump(template)+'\nSchema：'+json.dumps(Volume.model_json_schema(),ensure_ascii=False)
            else:
                prompt+='\n输出 content 为完整 ChapterCard YAML 列表，且恰好包含所选稳定 ID；保持 id、volume、number、order；每章一到少量 Scene Card，不写正文。状态 PLANNED、planning_level DETAILED。每项一短句，未定义可 null。Schema：'+json.dumps(ChapterCard.model_json_schema(),ensure_ascii=False)
            def complete(text):
                result=ChangeOutput.model_validate_json(text).model_dump()
                if result['lock_verdict']!='PASS':raise ConsoleError('规划 Canon/HARD 审查 FAIL',409)
                data=ws.parse_yaml(result['content']);ops=[]
                if kind in ['volume_outline_generate','volume_outline_refine']:
                    value=Volume.model_validate(data).model_dump()
                    if value['id']!=id or value['number']!=template['number'] or value['status']!=template['status']:raise ConsoleError('卷 ID/编号/规划阶段不匹配',422)
                    path=self.planning.path(id,'volume');bases.setdefault(path,None);ops=[{'path':path,'content':dump(value),'action':'write'}]
                else:
                    if not isinstance(data,list) or len(data)!=len(selected) or {c.get('id') for c in data}!={c['id'] for c in selected}:raise ConsoleError('深化必须保留全部所选稳定 ID，且各一次',422)
                    previous={c['id']:c for c in selected}
                    for row in data:
                        card=ChapterCard.model_validate(row).model_dump();old=previous[card['id']]
                        if any(card[k]!=old[k] for k in ['id','volume','number','order']) or card['status']!='PLANNED':raise ConsoleError('深化不能改卷、编号、ID 或进入正文阶段',422)
                        card['planning_level']='DETAILED';ops.append({'path':self.planning.path(card['id'],'chapter'),'content':dump(card),'action':'write'})
                return self.proposals.stage(project,kind,ops,result['explanation'],proof,bases,lambda ops:self.planning.validate(project,ops))
        internal=TaskRequest(type=kind,prompt=request.instruction or kind,options=TaskOptions(read_only=True,resume=False))
        return manager.prepared(internal,prompt,True,'project-main',output,complete,target=request.target)
