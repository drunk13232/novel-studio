---
name: novel-state-commit
description: 验证由已通过 Final 的章节产生的 Proposed State Diff，并在验证通过后提交正式小说状态。
---

只做状态验证/落盘，不能写正文。读 [两阶段提交及恢复](../../../docs/workflow-v0.1.md)。

- 输入：Final witness、Memory extraction、Proposed Diff、当前 State、验证回执。
- 输出：结构/引用/哈希检查结果、验证 receipt、正式状态变化与 ledger，或具体失败原因。
- 先人工/Skill 逐项对比 Proposed Diff 与 Final 原文：抽取是否正确、是否遗漏、是否把推断当事实、知识来源与获得顺序、未解 HARD/STRONG。必要时回 Memory Keeper 生成新 proposal。
- 逐项核查后保存 `state/proposed/ID.review.yaml`，格式用 `templates/proposed-review.yaml`；必须绑定 proposal_sha256、逐项 verified_operations 与 extraction_complete。脚本拒绝缺失/过期的审查记录。
- 再 `validate-proposal` 检查 Schema/引用/基线/正文及审查哈希；只有两层检查通过才能 `commit`。正文、报告、Canon/计划、基线或 proposal 修改后回执失效，重新验证。
- 允许第三方：无。
- 禁止：commit 前修改正式 State；用伪造 PASS 代替语义检查；修改既定 canonical_truth；改 Canon/正文；自动 Git commit；有失败事务继续推进。
- 文件提交有排他锁、写前回滚 journal、单文件原子替换、ledger 最后安装；不是数据库事务。进程中断时使用 recover；恢复前所有标准读取入口拒绝读正式状态。
