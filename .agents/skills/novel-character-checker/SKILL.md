---
name: novel-character-checker
description: 检查章节人物动机、目标、对白、情绪和关系变化的剧情支撑，以及 POV 知识越界。
---

只诊断人物/OOC，不把人物变化自动判错。读 [工作流](../../../docs/workflow-v0.1.md)。

- 输入：正文/计划、人物设定与状态、关系、知识获得记录、此前有证据的行为。
- 输出：`reviews/chapter-N/character.yaml`，每项 character/severity/category/location/evidence/reason/fix_direction；全章语义报告还含 result/body_sha256/coverage/reviewer/reviewed_rules/findings_resolved。
- 跑 `check --kind character` 后检查目标、压力下选择、台词辨识度、立场/亲密度/情绪转变、获得知识的过程。判断改变是否由场景中的压力、事件、认知或成长支撑。
- 允许第三方：`screenwriting:sw-character-conflict`（动机/变化/对手），`screenwriting:sw-dialogue`（人物口吻）；必须说明调用原因，输出只作为诊断。
- 禁止：改 Canon/人物卡/正文；替作者发明动机或诊断人格；角色已有成长证据仍仅因“不像以前”判 OOC；把作者知情当角色知情。
