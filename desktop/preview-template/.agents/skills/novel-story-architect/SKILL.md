---
name: novel-story-architect
description: 为作者已选定的小说草稿设计宏观故事方案，或局部重做主人公、世界和卷概念；方案审阅后才初始化正式项目。
---

先确定 ACTIVE PROJECT ROOT，读取 [方案契约](../../../docs/story-architect.md)。

使用真实 NovelForge 的灵感、世界、人物、总纲阶段；结构与人物阻力问题分别参考 Screenwriting 的 sw-story-structure 和 sw-character-conflict。不调用 Sepia，不启动 sw-workflow 或额外 Agent。

区分 USER LOCKED 与 AI PROPOSED。作者原文和锁定事实不可悄悄重写；对应方案字段保留锁定原文，矛盾返回 FAIL。空白允许 UNKNOWN/TBD。主角自己的欲望与在故事中的功能分别定义。按题材选择有用规则，不自动加入重生、系统或其他套路。

返回任务指定的 JSON Schema 结果，内容为紧凑世界、少数关键人物和宏观卷结构。不要生成章节正文，不写正式 Canon/State。后端提供的共享 Skill 源文与当前项目快照可直接使用，无需扫描 projects。

局部重做只返回指定区域 replacement；其他区域由后端冻结、合并和版本校验。三卷中的第三卷只能修改其单个卷概念，不能重新生成前两卷。

世界、人物和纲要完善也只返回候选完整文件及理由；通过 diff、作者接受和基线校验后才落盘。任何权限、锁定事实、版本或 Schema 冲突都报告失败，不通过更改 Canon 来掩盖。
