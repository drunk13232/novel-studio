# 我的流程 / My Workflows · 2.24.0 Preview

## 开始使用

- 世界设定 → AI 世界创作工作台 → 我的流程。
- 正文工具栏 → 我的流程（也可从 AI 创作指挥台进入）。需要写作或 AI 候选评审时，先保存正文并批准本次 Writer 参考。
- 选择世界观或章节示例。修改名称、增加/移除/排序步骤、关闭不需要的步骤，并设置每步模型与作者检查点。
- 保存模板，填写本次目标。世界设定仅在显式选择条目且步骤启用来源时发送；蓝图也要逐步选择。正文始终使用现有已批准 Writer 上下文。
- “保存运行草案”不调用模型。检查运行页的模型与资料范围并确认，再执行当前步骤。
- 默认每步暂停。勾选连续运行仍尊重作者检查点、必须处理的问题和调用上限。
- 可修改待执行步骤并补充正向要求，生成新的运行快照；已完成结果不可覆盖。
- 正文候选在原指挥台与 Diff 中采用；世界候选在原世界工作台审阅采用。流程没有自动提交按钮。

## 首版实际步骤

| 类型 | 执行功能 | 边界 |
|---|---|---|
| world_overview | 原世界工作台 starter / overview | 一份概览，不要求人物、剧情或文学分析 |
| world_rules | 原世界工作台 nature 模板 | 规则、条件与未知量候选 |
| world_review | 原世界工作台 challenge | AI 反例与问题，不是确定性求解器证明 |
| chapter_write | 原指挥台 quick + Writer 安全包 | 生成/接续候选，不写原文 |
| chapter_review | 原文学评审指定维度 | 前序正文候选的独立报告，不自动回流 Writer |
| local_proofread | 原本地校审 | 只检查已保存原章的标点/排版，不是语义校对 |
| manual | 作者补充检查点 | 始终等待作者明确继续，不调用 AI |

流程是有限的顺序步骤。当前不支持任意脚本、开放循环、任意 Action、全部 Skills、资料检索或求解器节点。现有软件中的这些功能仍可独立使用。

## 模型、预算与恢复

每步复用已有模型/参数控件，只发送接口支持的参数。模板内编辑不自动写入全局或项目模型偏好。上下文预算不足会阻止请求，不删除必要的 Writer 规则。示例候选评审的 128K 上下文预算是可见、可修改的模板设置；实际模型窗口仍会限制它。费用以服务商 Usage 和账单为准，未知时不编造。

每次运行冻结模板版本。修改模板不影响已启动的运行；编辑待执行步骤会保留旧快照。已完成步骤不会在重试时再次执行。最多 12 步、24 次执行尝试，每步最多 3 次；AI 设计流程是额外的一次显式请求。长大输入或前序结果超过限额时要求作者缩小范围，不默默截断。

暂停只停止后续调度；停止会请求取消当前实际任务。取消后的正文前缀保留，重试会用保留内容创建新的请求，不声称恢复远端流。关闭面板不等于停止已授权的任务。软件重启或备份恢复不自动发请求；检查保存结果后继续。恢复为新作品的章节流程如需新的 Writer 安全批准，应从模板准备新运行，不跨作品复用旧授权。

## JSON 模板与共享

格式为 `novel-studio-workflow/1`，由现有 Pydantic Schema 校验。最多 96 KB，未知字段和未知步骤类型拒绝。导入只创建新模板，不安装包、不执行代码、不启动任务。导出不包含运行目标、正文、项目条目引用、实际结果或凭据；作者手写的自定义指令仍需自行检查是否含私人文本。

[最小模板示例](world-first.example.json)。模板、运行记录与快照位于现有项目 metadata/studio/workflows，进入现有备份机制。它们是配置、候选与报告，不是 Canon 或新 State 格式。

## English quick start

Open **My Workflows** inside World Studio or the Creative Director. Copy a preset, edit ordered steps, choose models and source scope, and save it. Prepare a local run, inspect its scope, then explicitly start. Checkpoints pause; active requests can be stopped. Reopen saved history to continue. Adopt outputs through the original World Studio or Writer-safe Diff. Import/export shares configuration only and never executes a template.

The first version supports the seven step kinds above, not an unrestricted graph or script engine. No new Agent framework, service, dependency or author-data migration is required. Third-party/provider fees and actual model capabilities remain applicable.
