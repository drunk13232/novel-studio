---
name: novel-orchestrator
description: 编排本项目中文长篇小说的创作阶段、Canon 和状态权威；用于创建工程、续作或选择下一阶段。
---

负责阶段路由，不代替正文作者或专门检查器。先读根 AGENTS，再读 [架构](../../../docs/architecture-v0.1.md) 和 [使用说明](../../../docs/authoring-guide.md)。

- 输入：作者本轮授权、已定 Canon、当前 YAML 状态、现有阶段产物。
- 输出：当前阶段、缺项、下一步及具体产物路径；由作者授权的阶段才推进。
- 顺序：Idea → Story Architect → World Bible → Character Bible → Master Outline → Volume Outline → Chapter Planner；章节转交 `novel-chapter-pipeline`。
- 允许第三方：`web-novel-writing-skill`（NovelForge 阶段、模板、工程管理）；结构问题才调用 `screenwriting:sw-story-structure`、人物动机才调用 `screenwriting:sw-character-conflict`。每次记录问题、输入边界、建议及采用理由。
- 禁止：启动第二个主控制器、另立权威 bible、自行替换 Canon、因为安装/状态查询开始创作、批量写章节、跳过 Final/Proposed Validation 直接写正式 State。
- 主状态以 `state/*.yaml` 为准；旧 Markdown 状态只作引用，不双写。NovelForge 中直接提交状态的指令由本地两阶段提交机制接管。

本阶段 V0.1 只建基础设施和人工 fixture；后续须以作者新请求决定创作范围。
