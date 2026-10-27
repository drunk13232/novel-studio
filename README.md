# Novel Studio · 2.24.0 Custom Workflows Preview
## 2.24.0 本轮更新

既有创作指挥台与世界创作工作台新增“我的流程”：可编辑步骤、调整顺序、关闭步骤、选择具体模型与参数、限定资料范围并设置作者检查点。世界观与章节模板可保存、复制和 JSON 导入导出；运行记录保留版本、实际结果和取消后的部分候选。AI 可建议流程，但不会自动执行或采用设定与正文。详见[使用说明](docs/custom-workflows/README.md)和[验证边界](docs/custom-workflows/DELIVERY.md)。仍为 Preview；本地模拟接口通过不等于真实远端 AI 或原生桌面验收。

[![CI](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml)

> 计划仓库：`drunk13232/novel-studio`。当前仅为本地待审阅候选，尚未创建或发布仓库；CI 未在 GitHub 云端运行，徽章不代表通过。

本地优先的个人AI小说创作工作台。手动写作不需要AI；作者掌握正文、设定和修订的最终决定权。

**当前状态：Preview / PARTIAL；公开发布候选，尚未公开发布。许可证：Apache-2.0；Copyright 2026 drunk13232。** [English](README_EN.md)

## 功能与外部要求

|能力|实际已有范围|要求与边界|
|---|---|---|
|写作与安全修订|短篇、中篇、长篇、合集；CodeMirror 正文、Monaco Diff、多标签、分屏、自动保存与草稿保护。|本地 / Local|
|码字看板与年报|保存事件净增、删文负数、手动/AI来源分列；热力图、连续纪录、保存时段、目标和本地分享图。|本地；不是写作时长 / Local; not writing time|
|专注与开写仪式|可选番茄钟、打字机滚动、离线音效、开写清单、日目标和日记；久坐护眼提醒默认关闭。|本地；非阻断 / Local; non-blocking|
|跨章节查找替换|文本/大小写/全字/有超时的正则；逐条预览、专名提醒、显式确认、版本保护与批次回退。|本地；作者确认 / Local; author approval|
|人物、世界观与规则|人物、地点、势力、规则卡、百科、模板、来源引用和经过授权的 Writer 摘要。|本地；AI设计可选 / Local; optional AI design|
|时间线、关系与剧情矩阵|既有实体/事件关联、人物线和剧情线；计划与已提交事实明确分开。|本地 / Local|
|伏笔看板|计划、已埋设、部分/已回收、出处和逾期提醒；标记不改正文和 Canon。|本地 / Local|
|情绪/张力曲线|全书、人物和剧情线叠加，真实引文、作者修正、未知覆盖与低张力区段提示。|本地粗略信号；非文学评分 / Rough local signals; not literary scores|
|文学内核、评审与评分|文风/思想/伏笔/逻辑工作台，选区到全书的分阶段证据评分、历史对照和修订待办。|AI评价需所选模型 / AI evaluation needs a selected model|
|虚拟读者画像|项目内画像、多画像对照、冻结范围/预算、可验证引文和独立历史；无依据结果隐藏。|需要AI；模拟而非真实读者 / AI required; simulated, not real readers|
|文献与文风资料|本地导入、PDF/文档阅读、引用、书签、参考分屏和来源追溯。|作者自备合法资料 / Author-provided lawful sources|
|世界地图|本地底图或空白画布、地点标记、区域/路线、多地图、Bible绑定和备份。|不内置第三方地图 / No third-party maps bundled|
|世界逻辑实验室|Z3、NetworkX、SymPy/Pint、OR-Tools；冻结验收、反事实、来源和可导出报告。|基础求解本地；非社会预测 / Basic solving local; not social forecasting|
|AI协写与创作指挥台|上下文预览、具体模型与支持的参数、候选协写、Codex规划和所选Provider执行。|按需；不自动收费回退 / On demand; no automatic paid fallback|
|Codex与受控软件助手|复用登录、官方SDK、stdio MCP、Action Registry、执行回执和独立人工确认。|需外部安装/登录Codex；不是任意系统控制 / External authenticated Codex; not arbitrary system control|
|自定义API与本地模型|Chat Completions / Responses、流式、任务模型路由、系统密钥存储及用量记录。|需API或已运行本地服务 / Configured API or running local service|
|角色工作台与人物化界面|独立角色会话与既有受控助手；动态模型、运行时和声音按本机配置可用。|不分发私人角色模型、配音或Cubism Core / No private models, voices or Cubism Core distributed|
|章节平行版本|章节级草稿分支、Diff、显式正史切换、留痕与保护；默认统计和导出只认正史。|Final/提交保护仍生效 / Final/committed protection retained|
|印刷预览与成书|使用同一PDF排版结果预览/导出；开本、页码、字体和章节导航。|需本机Edge/Chrome及字体；部分格式需Pandoc / Local browser/fonts; some formats need Pandoc|
|朗读与音频导出|Windows SAPI本地声音、按章WAV、进度、取消和已完成章节续导。|需本机声音包；不保证音质 / Installed voices; quality varies|
|图片与外部视觉工具|素材、封面、ComfyUI工作流及可选可信Blender模板入口。|生成需自备外部服务/模型/软件 / Generation needs external services/models/software|
|插件、主题与语言|本地插件入口、既有主题及26种离线界面语言；新增高级界面主要简中/英文。|翻译/RTL和扩展能力仍为Preview / Translation/RTL and integrations remain Preview|
|备份与恢复|Manifest、哈希、SQLite索引、恢复为新项目；不把API密钥写入备份。|本地；换机重新填密钥 / Local; re-enter secrets on another machine|

## 使用与开发

Windows用户完整解压发行包，保留 `_internal` 与 EXE 同级；在首次引导选择独立数据目录或原创演示项目。不要把安装目录当成作品的唯一保存位置。AI不可用时仍可手动写作。

- [安装](INSTALL.md) · [独立开发与测试](docs/DEVELOPMENT.md) · [Windows构建](docs/WINDOWS-BUILD.md)
- [AI使用与权限](docs/AI.md) · [源码AI开发说明](desktop/developer-guide/AI-DEVELOPMENT.md)
- [更新记录](CHANGELOG.md) · [第三方声明](THIRD_PARTY_NOTICES.md)

实际版本由 `desktop/version.json` 与 `web/frontend/package.json` 共同记录。源码不包含开发依赖目录、真实作品、凭据或父仓库历史。外部Codex/Skills、ComfyUI、Pandoc、WebView2安装程序不在源码包中。部分功能需要用户自行配置；普通文本API不获得Codex文件权限。

## 验证边界与已知限制

历史2.22.2的局部验证（不代表当前版本已重新验收）：28项A/B后端隔离检查、3项共享评审回归、55项React组件断言；真实Data Center备份恢复和500章三线无界面图表检查通过。组件/推理夹具与真实服务结果分开标记。EXE命令行检查通过不等于原生窗口通过。

- 本次公开候选的独立安装、完整后端测试、构建与桌面验证，以[当前安装验证报告](docs/oss/INSTALL-VERIFICATION.md)为准；旧版记录不作为当前通过证据。
- 真实远端AI质量、所有服务商参数、物理中文输入法、Windows系统DPI组合与长期负载仍未全面验收。
- 情绪曲线是粗略局部信号；虚拟读者是模型模拟；引用匹配不证明文学判断正确。部分模型可能因未给证据而无可展示结论。
- 500章服务样本首次分析15.152秒、缓存分析6.884秒、缓存视图3.023秒；并非完整EXE速度、全书语义理解或同条件优化比例。
- 动态芳乃/蕾姆模型、Cubism运行时和私人声音不在公开包中；不宣称公开版已完成真实角色资产交付。
- PDF依赖本机浏览器/字体；音频依赖Windows声音包。特定样本通过不能覆盖所有PDF、排版问题或声音。
- 26种界面语言仍需母语审校，高级功能可能回退；作品不会被自动翻译。

## 展示、隐私与贡献

[截图来源及范围](docs/oss/SCREENSHOTS.md)。示例仅使用原创演示项目，截图是历史展示，不代表当前全部功能实测。

[贡献指南](CONTRIBUTING.md) · [安全说明](SECURITY.md) · [当前发布审计](docs/oss/PREPUBLICATION.md)。不要向Issue/PR上传私人小说、API Key、登录配置或未脱敏日志。没有虚构用户量、下载量或社区影响。

## 许可

[Apache-2.0](LICENSE) · Copyright 2026 drunk13232。参见 [NOTICE](NOTICE)、[COPYRIGHT](COPYRIGHT) 和[第三方声明](THIRD_PARTY_NOTICES.md)。第三方组件保留各自许可；软件许可不会自动覆盖作者的小说、文献、图片或私人角色模型。
