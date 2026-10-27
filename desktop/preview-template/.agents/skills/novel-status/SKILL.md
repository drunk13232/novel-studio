---
name: novel-status
description: 只读查看小说工程的当前章节、POV、时间地点、活跃线索、伏笔和待提交状态差异。
---

- 输入：`state/` 当前 YAML 与 proposed、chapter-ledger。
- 输出：运行 `scripts/novel.ps1 status` 的简短报告：Project/Volume/Chapter/POV/Location/Time/Active Characters/Open Threads/Open Foreshadowing/Canon Warnings/Last State Commit/Pending Diff。
- 允许第三方：无。中央 State 是权威，不请求第三方另建状态摘要。
- 禁止：输出全部作者秘密、读完状态后开始写作、改正文/State/Canon、把 State Commit 等同 Git commit。
- 若发现事务锁或 journal，报告未完成事务；读 [恢复说明](../../../docs/workflow-v0.1.md)，先恢复再读状态，不把半提交文件当权威快照。
