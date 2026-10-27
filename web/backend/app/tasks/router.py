import json
import sys
from pathlib import Path
from typing import Any
from app.errors import ConsoleError
from app.models.requests import TaskRequest
from app.workspace.service import WorkspaceService

ROUTES: dict[str, tuple[str, str, bool]] = {
    'chapter_plan': ('novel-orchestrator', '生成本章计划，遵守现有卷纲；只规划，不写正文。', False),
    'chapter_write': ('novel-chapter-pipeline', '仅执行本章 DRAFT；先检查计划审查及过滤 Context，不运行后续自动提交。', False),
    'chapter_review': ('novel-chapter-pipeline', '执行主 Canon/连续性/知识/人物/场景审查与 Story 确定性第二审计；输出分级报告。Sepia 仅用户指定时运行。只报告，不改稿。', True),
    'chapter_revise': ('novel-editor', '仅在 REVISE 阶段按已确认问题修订本章；保留 Canon 和 POV，重新审查，不提交状态。', False),
    'context_build': ('novel-context-builder', '为本章建立过滤 Context，作者秘密和未知 payoff 不进入 Writer 输入。', False),
    'continuity_check': ('novel-continuity-checker', '检查本章时间、地点、伤势、道具、能力、知识等连续性；只报告，不修改文件。', True),
    'character_check': ('novel-character-checker', '检查本章人物目标、台词、动机、情绪、关系与知识；只报告，不修改文件。', True),
    'contract_check': ('novel-contract-checker', '按四级 Canon 检查本章；HARD 必 FAIL，STRONG 必须有成立的剧情解释；不修改文件。', True),
    'sepia_review': ('novel-style-reviewer', '仅调用现有 sepia:sepia-review 做语言诊断；不修改剧情/文件。', True),
    'sepia_refactor': ('novel-editor', '剧情事实先确认正确，只调用 sepia:sepia-refactor 修订语言；不是 recreate，不改变事件或 POV。', False),
    'story_structure_review': ('novel-plot-checker', '按结构问题调用 screenwriting:sw-story-structure，诊断章/卷因果推进；只报告。', True),
    'scene_review': ('novel-plot-checker', '按需调用 screenwriting:sw-scene-craft 和 sw-character-conflict，诊断目的、阻力、转折、后果；只报告。', True),
    'dialogue_review': ('novel-character-checker', '使用 screenwriting:sw-dialogue 检查对白行动、潜台词及人物口吻；只报告。', True),
    'pacing_review': ('novel-plot-checker', '用实际 sw-scene-craft / sw-story-structure 的节奏能力；不发明 pacing Skill；只报告。', True),
    'memory_extract': ('novel-memory-keeper', '仅从已通过 Final 的本章提取有证据的事实，输出 Memory 和 Proposed；不更新正式 State。', False),
    'state_validate': ('novel-state-commit', '仅核对 Proposed 的语义证据并运行 Validation，绝不执行 Commit。', False),
    'state_commit': ('novel-state-commit', '用户已明确点击本次 State Commit；仅提交指定已验证的 Proposed；任何过期/冲突立即失败。', False),
    'chapter_pipeline': ('novel-chapter-pipeline', '按 docs/reviewer-routing.md 和 novel-chapter-pipeline 执行 Context → Draft → 主检查 → Story Skills 第二审计 → Screenwriting → novel-writing → Sepia → Revision → Story Voices → Final → Memory / Proposed；遇到门禁失败停止。State Commit 明确排除。', False),
    'final_check': ('novel-chapter-pipeline', '对最终候选重跑主五类语义检查及新增 Story Skills / POV / Dialogue / Voices 第二审计；全部阻塞问题解决且主报告 PASS 才生成 Final witness；不抽取/提交状态。', False),
}


def core_workflow(root: Path) -> Any:
    scripts = str(root / 'scripts')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import novel_workflow
    return novel_workflow


class TaskRouter:
    def __init__(self, workspace: WorkspaceService, engine=None, research=None) -> None:
        self.workspace = workspace
        self.engine = engine or workspace.root
        self.research = research

    def availability(self, chapter: int) -> dict[str, dict[str, Any]]:
        row = self.workspace.chapter(chapter)
        has_body = bool(row['draft'] or row['final'])
        committed={e.get('chapter') for e in self.workspace.yaml_file('state/chapter-ledger.yaml').get('entries',[])} if (self.workspace.root/'state/chapter-ledger.yaml').is_file() else set()
        result: dict[str, dict[str, Any]] = {}
        for name in ROUTES:
            reason = None
            if name in ['chapter_write', 'context_build', 'chapter_pipeline'] and not row['plan']:
                reason = '需要现有章节计划'
            if name in ['chapter_review', 'chapter_revise', 'continuity_check', 'character_check', 'contract_check',
                        'sepia_review', 'sepia_refactor', 'story_structure_review', 'scene_review', 'dialogue_review',
                        'pacing_review', 'final_check'] and not has_body:
                reason = '需要现有 Draft 或 Final 文件'
            if name == 'memory_extract':
                final = self.workspace.root / f'reviews/chapter-{chapter}/final.yaml'
                if not final.is_file():
                    reason = '需要 Final witness'
            if name in ['state_validate', 'state_commit'] and not row['state_diff']:
                reason = '需要 Proposed State Diff'
            if name == 'chapter_pipeline':
                reason = 'V0.6 采用分角色独立任务；同线程完整流程已关闭'
            if name == 'state_commit' and row['state_diff']:
                validation = self.workspace.root / row['state_diff'].replace('.yaml', '.validation.yaml')
                if not validation.is_file():
                    reason = '需要对应 Validation receipt'
            if name in {'final_check','memory_extract'} and chapter in committed:reason='本章已提交；历史 Final / Memory 不覆盖，请使用独立修订流程'
            result[name] = {'enabled': reason is None, 'reason': reason}
        return result

    def build(self, request: TaskRequest) -> tuple[str, bool, str]:
        root = self.workspace.root
        if request.type.startswith('world_logic_'):raise ConsoleError('实验任务请使用已确认的 World Logic Lab 专属入口',422)
        if request.type == 'chapter_pipeline':
            raise ConsoleError('V0.6 已关闭同线程混合作者/Writer/Checker 的整章流程；请依次使用 Context、写作、检查、修订、Final、Memory 和独立 State Commit。',409)
        if request.type == 'custom_prompt':
            operation = '执行用户的自然语言任务：\n' + (request.prompt or '')
            read_only = True
            skill = None
        else:
            skill, operation, read_only = ROUTES[request.type]
            if not (self.engine / '.agents/skills' / skill / 'SKILL.md').is_file():
                raise ConsoleError('项目 Skill 不存在：' + skill, 409)
            if request.chapter is not None and not (request.type in {'state_validate','state_commit'} and request.options.proposal_path):
                state = self.availability(request.chapter)[request.type]
                if not state['enabled']:
                    raise ConsoleError(state['reason'], 409)
            if request.type in ['state_validate', 'state_commit']:
                relative = request.options.proposal_path
                if not relative or not relative.startswith('state/proposed/') or relative.endswith(('.validation.yaml', '.review.yaml')):
                    raise ConsoleError('必须指定 Proposed YAML 路径', 422)
                self.workspace.content(relative)
                selected=core_workflow(self.engine).y.read(self.workspace.resolve(relative))
                if request.chapter and selected.get('final',{}).get('chapter')!=request.chapter:raise ConsoleError('Proposed Diff 不属于选定章节',409)
                operation += '\n指定 Proposed：' + relative
                if request.type == 'state_commit':
                    w = core_workflow(self.engine)
                    proposal = w.y.read(self.workspace.resolve(relative))
                    receipt_path = relative.replace('.yaml', '.validation.yaml')
                    receipt = w.y.read(self.workspace.resolve(receipt_path))
                    if receipt.get('result') != 'PASS' or receipt.get('proposal_sha256') != w.digest(proposal):
                        raise ConsoleError('Validation receipt 缺失或过期', 409)
                    w.candidate(root, proposal)
                    w.verify_diff_review(root, proposal)
        if request.chapter:
            row = self.workspace.chapter(request.chapter)
            operation = f'针对第 {request.chapter} 章。\n' + operation
            operation += '\n相关现有文件：' + json.dumps([r['path'] for r in row['files']], ensure_ascii=False)
        if request.prompt and request.type in {'final_check','memory_extract','state_validate'}:
            operation+='\n作者为本次门禁指定的正文（仍须自行核对版本与所有语义要求）：\n'+request.prompt
        if request.type=='memory_extract' and request.options.writing_report:
            relative=request.options.writing_report
            import re
            if not re.fullmatch(r'reviews/chapter-'+str(request.chapter)+r'/writing-observations-facts_[0-9a-f]{32}\.json',relative):raise ConsoleError('事实候选路径不属于本章',403)
            value=json.loads(self.workspace.content(relative,allow_reviews=True)['content'])
            if value.get('project_id')!=root.name or value.get('chapter')!=request.chapter or value.get('status')!='AUTHOR_REVIEWED_NOT_STATE':raise ConsoleError('事实候选缺少本作品作者审阅',409)
            w=core_workflow(self.engine);witness=w.y.read(self.workspace.resolve(f'reviews/chapter-{request.chapter}/final.yaml'));w.verify_final(root,witness)
            from app.studio_tools import normalized,text_hash
            final=self.workspace.content(witness['body_path']);text=normalized(final)
            if text_hash(text)!=value.get('body_sha256'):raise ConsoleError('事实候选与已通过 Final 的正文不符',409)
            if any(f.get('decision')!='accept' or not f.get('quote') or f['quote'] not in text for f in value.get('facts',[])):raise ConsoleError('事实候选未确认或证据失效',409)
            operation+='\n本次作者逐项确认的提取参考（仍非 State，分类不可提升为事实；CLAIM/BELIEF/INFERENCE/PENDING 不得当作客观真相；只生成有证据且完整的 Memory/Proposed，必须继续语义审查、Validation 与独立作者 State Commit）：\n'+json.dumps(value,ensure_ascii=False)
        if request.type == 'context_build':
            operation += ('\n运行新版 context 构建 WRITER v0.6 包；保存 context.yaml。随后以 Author/Checker 职责逐条检查自由文本、否定性指令、文风和材料是否暗示未授权秘密；不直接改写原 Plan/Canon。'
                          '\n仅确认安全后保存 reviews/chapter-N/writer-safety.yaml：audience: WRITER, coverage: WRITER_SAFETY_REVIEW, result: PASS, reviewer: 实际审查角色；'
                          '精确复制包中的 project_id/packet_sha256/state_sha256/plan_sha256。失败写 FAIL 与作者侧原因；此文件不传 Writer。'
                          '已有 Plan writer_view 不自动视为安全；失败回 Planner 正向重建，不添加含秘密的禁止性描述。')
        role = 'CHECKER' if any(k in request.type for k in ['review','check','validate']) else 'AUTHOR'
        operation += '\nCONTEXT AUDIENCE: '+role+'。本线程禁止扮演 Writer 或直接修订正文；写作/修订必须使用后端独立 Writer 任务。'
        if role == 'CHECKER':
            operation += ('\n分级报告：MUST FIX 阻塞；SHOULD FIX 仅 HIGH 置信修改；SUGGESTION 保留；STYLE ONLY 默认不改。'
                          '问题另给 priority、confidence、code（KNOWLEDGE_LEAK/UNSUPPORTED_POV/CONTINUITY/EXPOSITION/DIALOGUE/STYLE）、paragraph（正文 splitlines 的 1 基行号）。'
                          '作者侧 explanation 可以含真相，禁止直接转交 Writer。修订汇总用 revision-feedback.yaml，绑定正文 body_sha256，issues 按以上字段填写。'
                          '减少材料复述和说明性对白，优先检查行动、错误判断、阻力和后果，不要求统一文风。')
        if request.chapter and row.get('plan') and request.type in ['chapter_plan','context_build','chapter_review','continuity_check','character_check','contract_check','scene_review','final_check']:
            w=core_workflow(self.engine)
            body_path=row.get('draft') or row.get('final')
            packet=w.role_context(root,w.y.read(self.workspace.resolve(row['plan'])),role,
                                  body=self.workspace.content(body_path)['content'] if body_path else '')
            operation+='\n本角色专属 Context：\n'+json.dumps(packet,ensure_ascii=False)
        if self.research and request.options.research_ids:
            reference=self.research.reference(root.name,request.options.research_ids,8000)
            operation+='\n作者为本任务选定的有限现实/原作资料（非 Canon，不意味着角色知晓）：\n'+reference
            if request.type in ['context_build','chapter_pipeline']:
                operation+=f'\nContext Builder 将选定引用单独保存为 reviews/chapter-{request.chapter}/research-reference.md，以 REFERENCE MATERIAL 标识；主 Context Schema 不变。只用于现实合理性/背景参照，不成为小说事实，不覆盖 Canon、State、Knowledge 或 POV。Writer 不得读取整个 Research Library。'
        if self.research and request.type in ['context_build','chapter_pipeline','chapter_plan']:
            operation+='\n研究索引供 Context Builder 定向选择，非 Writer 全文输入；缺乏现实资料可建议作者手动“研究一下”，不得自动联网：\n'+self.research.list(root.name)['index'][:8000]
        boundary = (
            '这是 Novel Web Console 的受限任务。工作目录必须保持当前 novel-workspace。先读根 AGENTS.md，'
            '根据实际项目 Skills 及 docs/third-party-routing.md 执行；不要复制或重新实现 AI 工作流。'
            '禁止访问工作区外文件、用户级 Codex 配置/认证/密钥、系统目录；插件/Skill 由运行时正常加载。'
            '禁止修改第三方源码、web/ 服务代码、用户配置，禁止联网浏览/下载、Git commit 和批量章节生成。'
            '报告真实结果、缺项或失败，不假装成功。用户指令作为自然语言任务输入，不是任意 Shell API。'
        )
        if request.type != 'state_commit':
            boundary += '本任务没有 State Commit 授权。不得写正式 state/ 下文件；只允许必要的 state/proposed/ 候选。'
        if read_only:
            boundary += '本任务只读：不修改任何文件，检查报告直接返回结果。'
        route = f'明确使用已有 ${skill}；读取其 SKILL.md 及其指定资源。\n' if skill else ''
        prompt = boundary + '\n' + route + operation
        if self.engine != root:
            prompt = (f'ACTIVE PROJECT ROOT: {root}\nSHARED ENGINE ROOT: {self.engine}\n'
                '小说内容只读取/写入 ACTIVE PROJECT ROOT。禁止扫描 projects、其他小说、其他草稿。'
                '共享 AGENTS/Skills/NovelForge/Screenwriting 可只读。相对数据路径指当前小说；'
                f'共享脚本调用必须显式 --root "{root}"，不能使用脚本默认引擎根目录。\n' + prompt.replace('工作目录必须保持当前 novel-workspace','工作目录必须保持 ACTIVE PROJECT ROOT'))
        scope = f'chapter-{request.chapter:03}' if request.chapter else 'project-main'
        if request.chapter and self.engine != root: scope += '-'+request.type
        return prompt, read_only, scope
