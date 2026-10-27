---
name: web-novel-writing-skill
description: 在本项目使用 NovelForge 规划或维护中文长篇小说的世界观、人物、大纲、章节审核和长期状态。适用于作者授权的小说工程任务；基础设施安装不启动创作。
---

# NovelForge 项目入口

此文件是本地路径适配入口，第三方源文件保持原样。

先读取工作区 `AGENTS.md`，再完整读取 [NovelForge 原生技能](../../../.novelforge/skills/SKILL.md)。该技能中的所有 `references/...` 都相对于 `novel-workspace/.novelforge/`，不是相对于原生 `skills/` 或本入口目录。

按照作者当前授权使用对应阶段、角色和模板。此入口不构成创作授权。当前由 `novel-orchestrator` 与 `novel-chapter-pipeline` 统一编排；三套能力的实时职责见 [V0.1 路由](../../../docs/third-party-routing.md)。

NovelForge 的静态世界/人物/纲要模板继续使用；动态状态以本地 `state/*.yaml` 为准。上游直接写 global-state/人物状态的动作改为 `novel-memory-keeper` 提取 → proposed → `novel-state-commit` 验证并落盘；不得绕过 Final、POV过滤或检查/修订分离。
