# World Logic Lab 1.0 — Novel Studio V2.9.2 Enhanced Preview

从小说左侧打开「世界逻辑实验室」。先复制一个模板，填写变量、选择有限来源、接受假设，在「验收标准」确认新版本，再运行本地实验。AI 是可选设计助手，未登录仍可完整进行手动实验。

确定性结果只适用于本次输入和执行过的规则，不证明世界观整体合理，不构成社会经济预测，不更新 Canon/State/Final/Knowledge。作者决定形式化是否忠实于原设定。实验是研究资料，不进入 Writer Context。

- [实验格式](EXPERIMENT-FORMAT.md)
- [规则语法](RULE-SPECIFICATION.md)
- [验收指南](ACCEPTANCE-GUIDE.md)
- [适配器接口](SOLVER-ADAPTER-GUIDE.md)
- [模板制作](TEMPLATE-AUTHORING.md)
- [安全模型](SECURITY-MODEL.md)
- [版本与复现](VERSIONING.md)
- [技术选型](TECHNICAL-SELECTION.md)

现有 API 根路径：`/api/projects/{project_id}/world-logic`。完整核心数据保存在该项目 `metadata/world-logic/` 的 JSON 文件中，SQLite 仍只是现有知识索引，实验不依赖私有数据库才能导出。现有 Data Center 自动包含这个 metadata 子目录。

AI 使用任务路由「世界逻辑实验设计」，可选 Codex 当前登录或已有自定义 API。只发送用户选择的来源、实验和选段；不读取整部小说。AI 输出先保存为 Proposal，接受只生成实验草稿，确认规则之后才允许运行。AI 假设默认不接受。结果复核另存侧栏意见，不能修改确定性报告。

分享模板默认清空输入值和原作品来源；名称和变量标识改为中性名称；数学公式和阈值仍可能体现私人设计，请分享前检查。报告默认移除输入快照和设定文本，运算输出仍需作者检查。明确选择 `include_private=true` 才导出私有前提。JSON/YAML 导出、JSON/Markdown 报告均可离线使用。

V2.9.2 Enhanced Preview adds typed chronology, real finite-resource scheduling, parameter counterexamples, three-scenario comparison and source mapping. See [Enhanced Guide](ENHANCED-GUIDE.md) and [the verification report](V2.9.2-REPORT.md).
