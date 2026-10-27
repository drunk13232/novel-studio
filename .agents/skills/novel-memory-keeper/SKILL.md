---
name: novel-memory-keeper
description: 从通过 Final Check 的最终章节提取有原文证据的状态变化，生成待验证 Proposed Diff。
---

只抽取已发生事实，先读 [两阶段机制](../../../docs/workflow-v0.1.md) 和 [状态 Schema](../../../docs/state-schema.md)。

- 输入：Final witness、与 witness 哈希完全相同的正文、当前 State；不能输入 Draft 代替 Final。
- 输出：`reviews/chapter-N/memory.yaml`，模板见 `templates/memory-extraction.yaml`；含 events、character/relationship/knowledge/location/item/faction changes、伏笔新建/推进/回收、线索开启/推进/关闭，以及映射到 State 的 operations。
- 每条变化和 operation 必须附原文 evidence；知识变更记录 character、fact、获得章/时间/source_event，不能由推测补真相。检查中央知识记录与人物知识投影同步。
- 用 `extract` 绑定 Final，然后 `propose` 暂存到 `state/proposed/`；交 `novel-state-commit` 验证。
- 允许第三方：NovelForge Memory Keeper 参考，只经 `web-novel-writing-skill` 读取相应 Phase；禁止上游直接落盘动作。
- 禁止：评价文风、改正文、改正式 State/Canon、从计划预期或作者 payoff 抽取“已发生”事件；凭空补齐记忆。
