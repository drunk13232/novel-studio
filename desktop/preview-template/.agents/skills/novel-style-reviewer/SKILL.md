---
name: novel-style-reviewer
description: 按项目 Style Profile 检查中文语言冗余、套话、句式重复和 AI 味，只报告表达问题。
---

- 输入：正文、style-profile、冻结事实/POV边界；文风未设定时以可读性诊断，不假定某种作者声音。
- 输出：`reviews/chapter-N/style.yaml`，含 result/body_sha256/coverage: SEMANTIC_REVIEW/reviewer/reviewed_rules/findings_resolved/issues；只记录原文定位、语言问题和修订方向。
- 允许第三方：`sepia:sepia-review`；入口必须读取其规定的唯一 sibling Sepia 主技能。外部 review 的结构/剧情意见只标越权项，交本地相应 Checker 判断，不作为自动修改依据。
- 禁止：修文、State/Canon 修改、替代人物/结构审核、自动选择 Hemingway、因为高风险表达出现就认定机器生成。
- 语言节奏归此入口；事件顺序/场景节奏交 `novel-plot-checker`。
- Sepia Optional，仅用户请求语言诊断或指定局部润色时运行；基础 style 语义审稿仍保留。不要因“AI 味”统一声音或扩写所有对白。表达建议默认 STYLE ONLY；明显损害理解且高置信的问题可 SHOULD FIX。
