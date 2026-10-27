# 2.12 设计与方法取舍

范围：只深化原有功能；不建立文学价值评分、第二套知识库、审稿队列或编辑器。

- [Novelcrafter Codex](https://www.novelcrafter.com/help/docs/codex/the-codex)：复用现有实体、文风与明确选中的上下文，作者看到的内容不等于 Writer 获准知道。
- [Plottr plot devices](https://plottr.com/plot-devices/)：让伏笔与场景、进展和回收保持关联；本文本证据与计划分开，不强制回收期限。
- [Scrivener](https://www.literatureandlatte.com/scrivener/overview)：轻量关联视图覆盖原有稿件与笔记，而非重建存储层。
- [ProWritingAid sentence length](https://help.prowritingaid.com/article/49-how-to-use-the-sentence-length-report)：用分布与定位帮助观察节奏；不将计数当成质量。
- [Fictionary evaluate](https://fictionary.co/support/help-docs/evaluate/)：把人物诉求、选择与场景后果联起来；保留自由结构，不强制每一场戏套用标准模板。
- 现有 `sw-premise-theme`：思想与反方思想通过人物行动和代价表现。其关于单一命题或标准结论的方法只作参考，作者多义性要求优先。实际分析记录加载源文的摘要指纹；未安装时使用内置人物与场景方法。

确定性部分复用当前文本统计、版本校验、NetworkX 和世界实验室。文学理解使用现有 Codex / API Adapter + TaskManager；引用经过服务端逐字定位，无法定位的引用拒绝保存。AI 只能给出观察、条件性风险、信息不足、可能歧义和解释。

作者记录采用既有笔记的一个可选类型字段，无 SQLite 迁移。文风档案只增加可选原文来源和适用范围；旧档案、主题与项目格式继续可用。正文、人物事实、Knowledge 与 State 权威不变。

Writer handoff 使用作者编辑的正向文本，不自动转述完整报告。选定素材绑定版本、POV、场景、记录与证据指纹；原有 Writer Context 预览批准和输出校验继续执行。模拟读者路径明确拒绝作者文学记录。
