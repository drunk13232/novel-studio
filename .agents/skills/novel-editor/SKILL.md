---
name: novel-editor
description: 在 REVISE 阶段按已确认的检查问题修订单章正文，保持 Canon、事件和 POV 信息边界。
---

- 输入：经安全审查的 Writer View、已剔除泄密段的原稿、后端转换的结构化安全反馈。完整五类报告与隐藏真相只留 Checker；禁止直接复制 suggested_fix/explanation 到 Writer。
- 每次修订使用新的 Writer 线程和独立目录。MUST FIX 必修；SHOULD FIX 仅 HIGH 置信；SUGGESTION 保留，STYLE ONLY 默认不强制。秘密问题只发段落编号与通用修改方向。
- 输出：修订稿、逐项修改记录和需要重新审查的清单；所有语义审查及正文哈希重新生成。
- 允许第三方：`sepia:sepia-refactor` 仅在剧情事实正确而表达欠佳时使用；`sepia:sepia-recreate` 仅在不可修补的指定段落/场景且作者明确要求重写时使用。`sepia:sepia-hemingway` 只有作者明确选此声音、style-profile opt-in 后使用。
- 对事实错误先按 Checker 修复；涉及 Canon 更改回作者决策，不让语言工具编造更方便的情节。
- 冻结事件、目标、情绪状态、信息揭示、关系、时间、世界规则和 POV。修改后逐项对照；第三方默认 full rewrite 不能扩大选中范围。
- 需要保留作者声音时可定向调用已安装 novel-writing 的 style-fidelity.md；它提出独立 REVISE 候选，不覆盖原稿。Style 修改服从 docs/reviewer-routing.md 的优先级；修订后做 Story Skills voices 第二意见，再走原 Final 门禁。声音分析仅保存 metadata/voice-analysis/，不改 style-profile.yaml。
- 禁止：在检查阶段偷偷改稿、修改 State/Canon、重写后沿用旧 PASS 或 Final witness。
