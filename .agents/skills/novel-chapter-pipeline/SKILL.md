---
name: novel-chapter-pipeline
description: 编排单章计划、过滤上下文、写作、独立审查、修订、Final、记忆与状态提交的完整流程。
---

编排单章，不代替各检查器。必须读 [阶段权限表与命令](../../../docs/workflow-v0.1.md)。

- V0.6 安全覆盖：本 Skill 只做作者侧编排。不能在已读取 Canon/秘密的线程中继续扮演 Writer。Web 的混合单线程 chapter_pipeline 已关闭；使用 Context / Writer / Checker / Revision 独立任务。安全审查绑定 Context 哈希后才进入 Writer 独立目录和新线程。
- Writer 减少材料复述与流程解释；让行动后果、关系冲突、错误判断、现实阻力和环境细节承载信息。专业对白围绕当下诉求，避免人物轮流讲解程序。
- 主 Canon/连续性/知识/POV/人物/场景检查与必要 Story 确定性检查自动运行。专项 Screenwriting / novel-writing 扩展审稿按发现的问题调用；Sepia、声音模板和全文重写仅用户请求时运行。
- MUST FIX 必修并阻塞 Final；SHOULD FIX 仅高置信修改；SUGGESTION 保留；STYLE ONLY 默认不改。下面旧阶段序列中的 Sepia REVIEW / VOICES 是可选节点，不要求全部调用。

- 输入：作者本轮单章授权、Canon、State、卷纲/章纲、style profile。
- 输出：计划、过滤 Context、Draft、五类报告、修订记录、Final witness、Memory、Proposed Diff、Validation receipt 和 State Commit 结果。
- 严格顺序：PLAN → PLAN REVIEW → CONTEXT BUILD → DRAFT → CANON CONTRACT → 主 CONTINUITY → KNOWLEDGE / POV → CHARACTER → Story Skills CONTINUITY / KNOWLEDGE → Screenwriting SCENE / CONFLICT / DIALOGUE → novel-writing POV / DIALOGUE → Sepia REVIEW → REVISE → Story Skills VOICES → FINAL CHECK → MEMORY EXTRACT → PROPOSED STATE DIFF。State Commit 保持独立确认。
- 状态工作完成前的阶段均不写正式 State 或 Canon。检查器只报告；修订只在 REVISE；修订后重跑全部最终检查并绑定新正文哈希。
- DRAFT：NovelForge Writer 使用 Context 包。事实无矛盾且需要语言帮助时才按路由调用 `sepia:sepia-write`；输入只能是 Context 包和冻结事实。
- 允许第三方：NovelForge 维持长篇工程；Screenwriting 只查场景/戏剧性；Story Skills 做确定性第二审计；novel-writing 做 POV/对白/保留声音审稿；Sepia 做语言。先读 [审稿路由](../../../docs/reviewer-routing.md)，不得越过输入边界。
- Story 原生检查通过 `python <SHARED ENGINE ROOT>/scripts/writing_stack_audit.py --root ACTIVE_PROJECT --command continuity --chapter N` 与 `--command knowledge --character-id POV --chapter N` 调用；修订后用 `--command voices --chapter N`。只写一次性 metadata/story-validation 投影；报告不得当作 State。
- novel-writing 使用已安装 `novel-writing/SKILL.md` 与 cognition-layers-and-language / dialogue-and-behavior / style-fidelity 的定向参考；审稿只报告。现有 Final 的五类报告继续绑定最终正文，把第二审计与 POV/对白发现汇入对应审查门禁；未解决的高优先级冲突阻止 Final。
- 任一 HARD/STRONG 未解冲突阻塞 Final。最终五类语义报告均 PASS 才生成 witness；机械 PASS 不替代语义 PASS。
- 禁止：批量生成、在审核中偷偷修稿、将 WARN 升格成假 PASS、借状态提交自动 Git commit。
