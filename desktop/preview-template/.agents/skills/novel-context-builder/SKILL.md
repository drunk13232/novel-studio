---
name: novel-context-builder
description: 为指定章节和 POV 构建按角色知识、时间及白名单过滤的 Writer Context，避免作者秘密泄漏。
---

先读 [Context 规范](../../../docs/context-builder-spec.md)。负责只读组包；不是搜集全部资料后给 Writer 的摘要器。

- V0.6：`context --audience WRITER|AUTHOR|CHECKER` 是三种不同输出。Writer 默认角色；AUTHOR/CHECKER 包不能改标签后当 Writer 包使用。
- Writer 包生成后做语义安全审查，将当前 project_id/packet_sha256/state_sha256/plan_sha256 和 reviewer、coverage: WRITER_SAFETY_REVIEW、audience: WRITER、result 保存到 `reviews/chapter-N/writer-safety.yaml`。失败返回 Planner 正向重建；禁止通过“不要暗示某秘密”补漏。后端重建并比对包，旧版 Context 不可直接恢复。
- 角色知道、读者知道、作者知道、本场可披露分别核对；reader_known_since_chapter 不授予角色知识。approved_disclosures.audience 可为 CHARACTER/READER/BOTH；始终按确切 scene 生效。

- 输入：Canon、已提交状态、指定章节计划、POV、可选场景及已标注可见性的历史材料。
- 输出：`reviews/chapter-N/context.yaml`，包含规范中的 14 个区域；运行 `context` 子命令，使用 `writer_view`，不得复制未经筛选的原始文件。
- 主过滤器仍是本 Skill。Story Skills context 仅作作者第二意见，不替换 Writer Context。Research 只加载作者所选或本章定向匹配的有限条目，以独立 REFERENCE MATERIAL 附件标记，保留原 Context Schema，不把现实/原作资料提升为 Canon 或角色知识。未选取时只查本项目 Research Index，不把全库提供给 Writer。
- 必须：验证知识来源、章节及故事时间；人物不知的真相和 payoff 完全排除；错误信念只以“角色相信的内容”提供，不标出其真假。
- 新揭示仅在作者批准的 `approved_disclosures` 的确切场景中提供；提醒先写获得信息事件。未指定场景时不放入该事实。
- 禁止：直接传整个人物卡、Canon statement、作者大纲、伏笔 intended_payoff、他人秘密；使用 AUTHOR-ONLY 区域绕过过滤；因计划存在就当作事件已发生；更改正文/State/Canon。
- Writer 阶段只读本包；若缺信息，回到本 Skill 请求定向组包，不自行打开作者资料。
