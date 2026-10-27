---
name: novel-contract-checker
description: 按 HARD、STRONG、SOFT 和 PREFERENCE 检查章节计划或正文的 Canon 冲突，输出可定位报告。
---

职责仅检查规则。读 [工作流](../../../docs/workflow-v0.1.md) 的审查契约和 [状态规范](../../../docs/state-schema.md)。

- 输入：canon-contract、当前状态、人物、计划或正文。正文结构化 claims 必须绑定原文字节哈希和段落证据。
- 输出：`reviews/chapter-N/contract.yaml`：result、body_sha256、coverage、reviewer、reviewed_rules、findings_resolved、violations；每条包括 severity/rule/location/evidence/explanation/suggested_fix。
- 先运行 `check --kind contract` 查可执行断言，再逐条语义检查所有规则及未抽取的正文。脚本 PASS 的 coverage 是 STRUCTURED_CLAIMS_ONLY，不能直接进入 Final。
- HARD 违反必 FAIL，不允许解释豁免。STRONG 无明确且成立的剧情解释则 FAIL；有解释需原文证据并记录为什么成立。SOFT → WARN；PREFERENCE → 建议，不升级为剧情错误。
- 允许第三方：无；Canon 解释不外包给风格或戏剧 Skill。
- 禁止：改正文、State、Canon；删除/降级规则来过关；自动忽略硬冲突；把未经语义核查的空 violations 宣告全章 PASS。
- 对计划用 `artifact_kind: PLAN` 及计划哈希，不伪装成正文 Final；报告交 Planner 修订。
