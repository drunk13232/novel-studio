import difflib
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Literal
from pydantic import Field
from app.errors import ConsoleError
from app.models.requests import TaskRequest, TaskOptions
from app.projects.foundation import schema
from app.domain.tasks import ReviewReport
from app.integrations.stack import resources, PRIORITY
from app.integrations.research import Strict, ResearchOutput
from app.integrations.story import StoryValidator
from app.tasks.storage import atomic_json

STORY_TASKS={'story_continuity_check':'continuity','story_knowledge_check':'knowledge','story_timeline_check':'timeline',
             'story_voice_check':'voices','story_context_build':'context','story_links_check':'links',
             'story_doctor':'doctor','story_names_check':'names'}
SPECIALIST_TASKS=[*STORY_TASKS,'research_topic','pov_review','dialogue_review','voice_preserving_revision']

class RevisionOutput(Strict):
    content: str
    explanation: str
    preserved_constraints: list[str]

class WritingSpecialists:
    def __init__(self,engine,registry,characters,planning,research):
        self.engine=engine;self.registry=registry;self.characters=characters;self.planning=planning;self.research=research
        self.story=StoryValidator(engine,registry,characters,planning)

    def save_report(self, project, report, chapter=None, voice=False):
        ws=self.registry.workspace(project)
        relative=('metadata/voice-analysis/' if voice else 'reviews/specialists/')+uuid.uuid4().hex+'.json'
        path=ws.resolve(relative,allow_reviews=True)
        atomic_json(path,report)
        report['saved_path']=relative
        return report

    def start(self,project,request,manager):
        if request.type not in SPECIALIST_TASKS: raise ConsoleError('无效专家任务',422)
        ws=self.registry.workspace(project)
        instruction=request.instruction or request.prompt or ''
        chapter=request.chapter
        if request.chapter_id:
            card=self.planning.get(project,request.chapter_id,'chapter')['value']
            chapter=card['number']
            if request.type not in STORY_TASKS and len([c for c in self.planning.rows(project,'chapter') if c['number']==chapter])>1:
                raise ConsoleError('跨卷重复章号尚不能唯一对应现有正文，请在写作页面指定全书章号',409)
        internal=TaskRequest(type=request.type,chapter=chapter,prompt=instruction or request.type,
                             options=TaskOptions(read_only=True,resume=False,timeout_seconds=1800 if request.type=='research_topic' and request.depth=='deep' else 600))
        if request.type=='voice_preserving_revision':
            internal.prompt=instruction or None
            internal.options.research_ids=request.research_ids
            return manager.start(internal)
        if request.type in STORY_TASKS:
            if request.type=='story_knowledge_check' and not request.character_id:raise ConsoleError('请选择当前项目角色',422)
            if request.character_id:self.characters.get(project,request.character_id)
            _,proof=resources(self.engine,'story')
            def execute(emit,cancelled):
                report=self.story.run(project,request,STORY_TASKS[request.type],emit,cancelled)
                report['skills']=proof
                return {'status':'interrupted' if cancelled() else 'completed','output':json.dumps(report,ensure_ascii=False)}
            def complete(text):
                report=json.loads(text)
                return self.save_report(project,report,chapter,request.type=='story_voice_check')
            return manager.prepared(internal,'',True,'project-main',complete=complete,target=request.chapter_id,
                                    execute=execute,provider='Story Skills',skill='story-skills:story-maintenance')
        if request.type=='research_topic':
            if not request.topic.strip(): raise ConsoleError('请填写研究主题',422)
            existing=next((r for r in self.research.list(project)['topics'] if r['title'].strip().casefold()==request.topic.strip().casefold() and r['category']==request.category),None)
            topic=request.topic_id or (existing['id'] if existing else 'topic-'+uuid.uuid4().hex)
            old=self.research.get(project,topic) if request.topic_id or existing else None
            material,proof=resources(self.engine,'research')
            index=self.research.list(project)['index'][:12000]
            today=date.today().isoformat()
            prompt=(f'ACTIVE PROJECT ROOT: {ws.root}\n你执行 Research Skill 的 Codex inline 调查。'
                    '禁止子 Agent、跨项目读取、Git 操作和文件修改。联网检索仅限本研究任务。'
                    '项目根明确为 ACTIVE PROJECT ROOT，不采用上层 git 根。后端负责写 .research/，你只返回 outputSchema。'
                    'Research ≠ Canon。不能修改小说、Canon、State、Knowledge、人物或大纲。不要研究任何未指定主题。\n'
                    +material+'\n本项目已有 Research Index，优先复用，不重复调查：\n'+index+
                    '\n待更新原资料（如有）：\n'+(old['content'] if old else '无')+
                    '\n研究主题：'+request.topic+'\n要求：'+instruction+'\n深度：'+request.depth+
                    '\n类别：'+request.category+'\n今天：'+today+
                    '\n返回 markdown（完整原生 FINDINGS.md）和 summary。frontmatter topic 必须为 '+topic+
                    '，title 为研究主题，category 为 '+request.category+'，depth 为 '+request.depth+
                    '；created / last_verified 日期 YYYY-MM-DD，status active，sources 是 url/fetched 列表。'
                    '必须包含 Summary、Findings、Insights、Strongest objection、Discarded approaches、Open questions、Timeline。'
                    '事实必须有实际取回的来源 URL，失败如实记录，不编造。保留反方检查；没有来源即开放问题。'
                    '更新须保留旧结论的 Timeline 和 Discarded approaches，不静默覆盖。')
            def complete(text):
                result=ResearchOutput.model_validate_json(text)
                meta,_=self.research.parse(result.markdown)
                if meta.get('category','reality')!=request.category or meta['depth']!=request.depth:
                    raise ConsoleError('研究分类或深度不匹配',422)
                row=self.research.save(project,topic,result.markdown,old['etag'] if old else None)
                return {'research_topic':row,'summary':result.summary,'reference_only':True,'provider':'Research Skill','skills':proof,'saved_path':row['path']}
            return manager.prepared(internal,prompt,True,'research-'+topic,schema(ResearchOutput),complete,target=topic,
                                    allow_web=True,provider='Research Skill',skill='research-codex:research')
        if not chapter: raise ConsoleError('请选择章节',422)
        row=ws.chapter(chapter);source=row['final'] or row['draft']
        if not source: raise ConsoleError('此检查需要已有 Draft 或 Final 正文',409)
        body=ws.content(source)
        references=['revision-checklist.md', 'cognition-layers-and-language.md'] if request.type=='pov_review' else ['revision-checklist.md','dialogue-and-behavior.md'] if request.type=='dialogue_review' else ['style-fidelity.md','cognition-layers-and-language.md']
        material,proof=resources(self.engine,'novel',references)
        plan=ws.yaml_file(row['plan']) if row['plan'] else {}
        context_path=f'reviews/chapter-{chapter}/context.yaml'
        context=ws.content(context_path,allow_reviews=True)['content'] if (ws.root/context_path).is_file() else ''
        # Reviewer is author-side and may inspect State. Revision receives only approved Writer Context.
        if request.type=='voice_preserving_revision' and not context:
            raise ConsoleError('保留声音修订需要本章 novel-context-builder 的过滤 Context',409)
        task_context={'plan':plan,'current_state':ws.yaml_file('state/current-story-state.yaml'),
                      'knowledge':ws.yaml_file('state/knowledge-state.yaml'),
                      'characters':[c['canonical'] for c in self.characters.list(project)],
                      'canon':ws.yaml_file('settings/canon-contract.yaml')} if request.type!='voice_preserving_revision' else {'filtered_writer_context':context}
        prompt=(f'ACTIVE PROJECT ROOT: {ws.root}\n本轮使用实际 novel-writing Skill，限定 Specialist Reviewer。'
                '不建第二主流程、目录或版本系统，不调用子 Agent、不联网、不修改文件、Canon、State 或 Knowledge。'
                '用户优先级：'+PRIORITY+'。Research 只作 REFERENCE MATERIAL，采用为 Canon 需作者独立 Proposal Commit。\n'
                +material+'\n当前任务：'+request.type+'\n要求：'+instruction+'\n定向材料：'+json.dumps(task_context,ensure_ascii=False)+
                '\n当前正文本体：\n'+body['content']+'\n'+self.research.reference(project,request.research_ids))
        if request.type=='voice_preserving_revision':
            prompt+='\n只输出候选修订 content / explanation / preserved_constraints。保留声音、信息边界、剧情事实；不能以文学化为由压平作者特征。不应用到 Draft/Final，后端保存独立 REVISE 候选。'
            output=schema(RevisionOutput)
            def complete(text):
                result=RevisionOutput.model_validate_json(text)
                if ws.content(source)['etag']!=body['etag']:raise ConsoleError('正文已变化，修订候选已拒绝',409)
                path=f'reviews/chapter-{chapter}/voice-revision-{uuid.uuid4().hex}.md'
                target=ws.resolve(path,allow_reviews=True)
                self.research.write(target,result.content)
                return {'revision_candidate':True,'provider':'novel-writing','content':result.content,'explanation':result.explanation,
                        'preserved_constraints':result.preserved_constraints,'saved_path':path,'source_path':source,'source_sha256':body['etag'],
                        'diff':''.join(difflib.unified_diff(body['content'].splitlines(True),result.content.splitlines(True),fromfile=source,tofile=path)),
                        'requires_final_check':True,'automatic_apply':False,'skills':proof}
        else:
            prompt+='\n只返回 verdict PASS/WARN/FAIL、summary、issues；每个问题有 severity / message / evidence，证据含段落位置和引用，不修改稿。POV 检查知识/内心越界；对白检查信息说明、潜台词、口吻与行动后果，避免重复宽泛文风检查。'
            output=schema(ReviewReport)
            def complete(text):
                report=ReviewReport.model_validate_json(text).model_dump()
                if report['verdict'] not in ['PASS','WARN','FAIL']:raise ConsoleError('审稿 verdict 无效',422)
                if ws.content(source)['etag']!=body['etag']:raise ConsoleError('正文已变化，请重新审稿',409)
                report.update(report_only=True,provider='novel-writing',skills=proof,source_path=source,source_sha256=body['etag'])
                return self.save_report(project,report,chapter)
        return manager.prepared(internal,prompt,True,f'chapter-{chapter:03}-{request.type}',output,complete,target=request.chapter_id or source,
                                provider='novel-writing',skill='novel-writing')
