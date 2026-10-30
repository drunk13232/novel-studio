# Novel Studio · 2.24.26 Bounded Chapter Opening Preview

## 当前公开版本：2.24.26 Preview

汇总 2.24.24～2.24.26：保存后的码字统计同步、只读磁盘快照、保存回执核对时限、可取消的章节加载和工作区恢复请求去重。安装程序、便携 ZIP、SHA-256：[2.24.26 Release](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.26-preview)。旧版保留供回退。

**Preview / PARTIAL**：2.24.26 本地交付记录有 39 项隔离 headless 场景；打包工作进程和静默安装/卸载另外核验。原生桌面点击、实体中文输入法、系统 DPI、语音、真实云端 AI 和长期使用未新增验收。当前提交的实际 CI 结果见 Actions 和 Release。正在开发的恢复机制修改未纳入本版。

章节正文与恢复副本读取共用 10 秒时限，保存回执不明时只读核对，不自动重发正文写入；恢复副本不替代持久备份。

## 2.24.26

本地 Preview / PARTIAL。章节正文和恢复副本读取可取消，10 秒时限覆盖响应头与正文；失败时保留原有内容，不跳过恢复检查，也不重放保存。恢复工作区先确定最终目标，两项实际对照由 4 次读取降为 2 次，不据此夸称启动时间减半。39 项隔离 headless 检查通过，包括未保存文字、撤销/重做、启用仪式后的取消、保存与格式回归。见 [2.24.26 说明](docs/workbench-experience/DELIVERY-2.24.26.md)。本轮未发布或更新快捷方式。

## 2.24.25

本地 Preview / PARTIAL。保存结果不明后，作者成功重载不同磁盘版本时同步刷新真实码字进度；不补造字数或保存事件。未确认状态直接提供现有比较/重载入口，空磁盘文件可明确查看；比较读取支持关闭取消、失败重试和时限。28 个隔离 headless 场景通过。见 [2.24.25 说明](docs/workbench-experience/DELIVERY-2.24.25.md)。公开版仍为 2.24.23，未自动发布或更新快捷方式。

## 2.24.24

本地 Preview / PARTIAL。保存回执不明后的只读核对设置 10 秒时限，覆盖响应头和 JSON 响应体；超时停止此次浏览器读取，保留编辑与未确认状态，不取消或重放已提交的正文写入。18 个隔离 headless 场景通过。见 [2.24.24 说明](docs/workbench-experience/DELIVERY-2.24.24.md)。当前公开版仍为 2.24.23；本轮未自动发布或更新快捷方式。

## 当前公开版本：2.24.23 Preview

本次汇总 2.24.20～2.24.23 的选区 AI 取消、离开/退出与真实保存回执修复。安装程序、便携包与 SHA-256：[2.24.23 Release](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.23-preview)。旧版保留供回退。

**Preview / PARTIAL**：47 个隔离 headless 场景验证保存、恢复及离开保护。原生桌面窗口、实体中文输入法、系统 DPI、语音、真实云端 AI 与长期使用未新增验收；退出桥替身不等于原生关窗。CI 结果以当前提交 Actions 和 Release 为准。

不明保存回执仅只读核对一次，不自动重发写入；恢复副本不替代持久备份。

## 2.24.23

本地 Preview / PARTIAL。区分正文保存和恢复副本处理；正文已确认写入时，不把清理副本失败显示成正文保存失败。回执不明时只读核对磁盘，不自动重发写入；不同或无法确认的版本保持编辑与离开保护，即使撤销回旧缓存也不会误判已保存。明确选择手动恢复副本可帮助比较，不更改自动恢复设置。见 [2.24.23 说明](docs/workbench-experience/DELIVERY-2.24.23.md)。未自动公开或接入快捷方式。

## 2.24.22

本地 Preview / PARTIAL。安全退出复用既有保存、恢复、偏好设置和桌面桥。返回写作、关闭或 Esc 会取消尚未交给桌面端的退出；迟到回执不再触发关窗接口。逐阶段显示真实状态与错误，桌面接管后明确不可撤回。桌面端退出准备防重复，备份后复查任务，关闭工作线程准备失败可重试。见 [2.24.22 说明](docs/workbench-experience/DELIVERY-2.24.22.md)。未自动公开或更新快捷方式。

## 2.24.21

本地 Preview / PARTIAL。“保存后离开”与“保留恢复副本后离开”现在具有独立的当前操作归属。点击继续编辑、关闭或 Esc 后，迟到的写入回执不能再次导航；内容、页面或操作已变化时会停止后续离开。弹窗显示实际保存状态、失败原因和明确重试，关闭恢复时说明不可用选项。见 [2.24.21 说明](docs/workbench-experience/DELIVERY-2.24.21.md)。本地版本未自动发布，公开下载以 [GitHub Releases](https://github.com/drunk13232/novel-studio/releases) 为准。

## 2.24.20

本地 Preview / PARTIAL。选区 AI 准备、队列发送及重试时重新检查原文与授权范围；助手与 Python 控制台复用已有会话和执行令牌，在真正创建任务前拒绝已取消、过期或不符的操作。已接受的子任务沿用原有归属与取消；不明回执先查历史，不自动重放。新增中文/英文状态和错误提示。见 [2.24.20 说明](docs/workbench-experience/DELIVERY-2.24.20.md)。公开下载仍以 [GitHub Releases](https://github.com/drunk13232/novel-studio/releases) 为准。

## 2.24.19

2.24.19 Preview。修复助手结果导航的异步输入保护：读取返回后重新核对当前页面、章节、较新操作和未保存修改；读取失败时停止后续候选或任务展示。明确重试清理自己的错误。沿用现有 Action 与作者确认。见 [2.24.19 说明](docs/workbench-experience/DELIVERY-2.24.19.md)。

安装程序、便携包和校验值见 [2.24.19 Releases](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.19-preview)。

> **已公开 2.24.19 的验证边界与限制（后续本地修复见上文）：** 原生窗口、实体中文输入法、系统 DPI、语音与新真实模型验收仍未完成。选区 AI 的准备和取消仍存在已知迟到提交边界：助手回执超时或取消后，候选任务仍可能启动。请先检查任务记录再重试；付费模型建议暂避该选区入口，等待后续修复。采用仍须作者在既有 Diff 中确认。窗口内恢复副本不等于持久备份。

## 2.24.18

2.24.18 Preview。历史与外部候选入口统一读取归属，过时响应不覆盖新候选；等待期间的未保存输入会在载入前重新核对。提供实际读取状态、取消读取与失败后明确重试。沿用原有 Diff、版本与作者确认。见 [2.24.18 说明](docs/workbench-experience/DELIVERY-2.24.18.md)。

安装程序、便携包和校验值见 [2.24.18 Releases](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.18-preview)。


## 2.24.17

本地迭代，合并至 2.24.18 Preview。修复多窗口载入后保留副本失去关闭保护的问题：可单独下载真正的本地副本，明确恢复或放弃后再继续。另一窗口已处理的候选保持只读，修订台同步保护。下载不等于项目暂存，副本仍是窗口内状态。见 [2.24.17 说明](docs/workbench-experience/DELIVERY-2.24.17.md)。

## 2.24.16

2.24.16 Preview。新候选不会继承上一轮说明或勾选；已处理历史可查看作者暂存的文字与说明。原文过期的只读历史保持所选版本，不再被另一版本暂存内容覆盖。既有原文与作者采用权限不变。安装程序与便携版见 [Releases](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.16-preview)。见 [2.24.16 说明](docs/workbench-experience/DELIVERY-2.24.16.md)。

## 2.24.15

2.24.15 Preview 包含 2.24.14 的候选编辑改进，并修复关闭后迟到保存回执对新比较窗口的影响：取消的版本切换或关闭操作不会在重开后重演。作者已保存的原候选快照继续保留；正式采用与源版本保护不变。见 [2.24.15 说明](docs/workbench-experience/DELIVERY-2.24.15.md)。保持 Preview / PARTIAL，不把 headless 浏览器或 worker 检查当作原生窗口、实体输入法或真实模型验收。

## 2.24.14

本地迭代，已合并至 2.24.15 Preview。 修复候选比较中的勾选保留、独立版本恢复和持续输入：自动暂存不再打断候选与说明输入；明确暂存可记住所选版本。编辑后新增、扩大的或合并的修改需要作者重新核对。见 [2.24.14 说明](docs/workbench-experience/DELIVERY-2.24.14.md)。公开发行仍以 Releases 为准。

## 2.24.13

2.24.13 Preview 发布候选；包含 2.24.11–2.24.12 的本地可靠性修复。修复不同换行下的候选引用定位、保留到光标、局部重写与文学评分选区。作者在既有 Diff 明确采用候选时，保持原文件换行和 UTF-8 BOM，保留原始候选及接受前快照；已有混合换行来源仍受保护。见 [2.24.13 说明](docs/workbench-experience/DELIVERY-2.24.13.md)。本地检查与真实 AI、原生窗口、实体输入法及 DPI 验收分开。

## 2.24.12

本地迭代，合并至 2.24.13 Preview。AI 追加、重写、取消保留和重启恢复改变候选时，旧报告统一标为历史；缺失版本依据时明确显示无法核实。核实过的原文引用可以定位候选，正文或引用来源变化另行提示。补齐后台清理后的有效完成回执处理。见 [2.24.12 说明](docs/workbench-experience/DELIVERY-2.24.12.md)。原生桌面、实体中文输入法、DPI 与新远端 AI 验收仍未完成。

## 2.24.11

本地迭代，合并至 2.24.13 Preview。累计修复作者接管时的输入保留、任务状态刷新顺序、报告归属与读取重试；连接检查不再阻塞作者保存，探测异常后可再次检查。保留现有作者确认、项目隔离与候选流程。见 [2.24.11 说明](docs/workbench-experience/DELIVERY-2.24.11.md)。原生桌面、实体中文输入法、DPI 与新远端 AI 验收仍未完成。

## 2.24.10

本次修复现有创作指挥台的输入保留、保存回执与工作台切换：查看“我的流程”不丢失全书目标草稿；保存期间的新输入保留；离开、Diff 和 Python 交接受保护；关闭后迟到的回执不会重新弹出工作区。保留原有作者确认与候选流程。详见 [2.24.10 说明及验证边界](docs/workbench-experience/DELIVERY-2.24.10.md)。继续标记 Preview / PARTIAL；未把浏览器检查当作原生桌面、中文输入法或真实 AI 验收。

## 2.24.9

本轮强化现有创作指挥台：配套 Codex 运行时、真实正文交付与字数目标、同任务断点恢复、输入预算预检、场景接口和全书候选版本核对。所有写作仍是候选，采用由作者决定；字数不代表文学质量。本机试写使用隔离原创项目。使用与验证边界见[2.24.9 说明](docs/workbench-experience/DELIVERY-2.24.9.md)。以下 2.24.5–2.24.8 为历史本地迭代记录，其改进合并至本次 2.24.9 Preview 发布。窗口、输入法与 DPI 仍不以浏览器或 worker 检查代替原生验收。

## 2.24.8

本轮复用创作指挥台与 Writer，将单章创作、真实进度、停止、继续和 Diff 候选接入 MCP。模型阶段遵守请求超时；作者选择的候选可作为有版本与来源的续写参考，仍需检查并确认，不自动进入 Canon。助手历史保留安全的候选查看入口。真实试写在独立目录进行，正文与运行记录不进入公开包。继续标记 Preview / PARTIAL；原生桌面、实体输入法及完整文学质量未在本轮重新验收。 详见[工作流说明](docs/workbench-experience/DELIVERY-2.24.8.md)。

## 2.24.7

本地迭代，已包含在后续 Preview 发行版。本轮补齐已有待办、修订和灵感的编辑保护：保存回执迟到时保留继续输入的修改，并以回执版本为基线继续保存；等待期间撤销、关闭和离开受原门禁保护。简中/英文说明区分本次已保存提交与后续未保存编辑。见[使用说明](docs/workbench-experience/README.md)与[检查边界](docs/workbench-experience/DELIVERY-2.24.7.md)。

## 2.24.6

本地迭代，已包含在后续 Preview 发行版。本轮针对保存回执迟到的真实问题：正文保存与恢复绑定原章节作用域；提交待办、修订和灵感时保留等待期间的新输入；正常检查同一候选版本后继续自动暂存，原有人工暂停仍保留。继续沿用原保存与作者确认通道，不增加数据格式。见[使用说明](docs/workbench-experience/README.md)和[本轮检查边界](docs/workbench-experience/DELIVERY-2.24.6.md)。

## 2.24.5

本地迭代，已包含在后续 Preview 发行版。重点修复写作恢复：本章待办与修订输入在切换页签或收起工具后保留；候选读取失败可以重试，两窗口冲突可先对比再明确载入，并在当前比较窗口内恢复刚才的本地编辑。已采用/拒绝记录显示真实只读状态，拒绝后本章列表立即刷新。采用、版本校验与正文保护继续走原通道。详见[使用说明](docs/workbench-experience/README.md)和[本轮验证边界](docs/workbench-experience/DELIVERY-2.24.5.md)。

## 2.24.4

候选手工编辑和说明可按版本在项目内暂存，重启后继续；关闭比较仍保留候选，采用正文必须另行确认。正文侧栏的“本章工作”集中展示目标、待办、修订事项、候选与出处。现有 AI 控制显示计划模型、接收服务、支持的思考档位和资料范围；打开控件本身不调用模型。详见[使用说明](docs/workbench-experience/README.md)和[本轮验证边界](docs/workbench-experience/DELIVERY-2.24.4.md)。

## 2.24.3

正文工具接入现有可调侧栏，不再挤占正文上方的大块空间；创作指挥台可直接进入，资料审核后返回所选工具，但不会自动调用模型。未保存正文先走原保存通道，保存失败或等待期间的新输入不会被旧上下文覆盖。修订台区分关闭比较与拒绝建议，切换或关闭前保护尚未采用的手工编辑与修订说明。详见[工作台使用说明](docs/workbench-experience/README.md)与[本轮验证边界](docs/workbench-experience/DELIVERY-2.24.3.md)。

## 2.24.2

创作指挥台现在支持指定步骤单独执行、步骤独立模型与参数、复制步骤及独立候选尝试。Python 的真实输出可显式带回作者备注，显示候选版本过期提示，并可移除备注。所有执行继续经过现有上下文、权限、预算及 Diff 保护。详见[使用说明](docs/creative-director/README.md)和[本轮验证](docs/creative-director/DELIVERY-2.24.2.md)。


## 2.24.1

创作指挥台分为任务书、候选正文、结果与回执；规划和写作可分别保存具体模型与参数。已保存候选可以显式交给现有 Python Control 做本地只读分析，再返回同一条任务。载入脚本不会自动执行、调用 AI 或修改正文。见[控制台说明](docs/creative-director/README.md)与[验证边界](docs/creative-director/DELIVERY-2.24.1.md)。

## 2.24.0 本轮更新

既有创作指挥台与世界创作工作台新增“我的流程”：可编辑步骤、调整顺序、关闭步骤、选择具体模型与参数、限定资料范围并设置作者检查点。世界观与章节模板可保存、复制和 JSON 导入导出；运行记录保留版本、实际结果和取消后的部分候选。AI 可建议流程，但不会自动执行或采用设定与正文。详见[使用说明](docs/custom-workflows/README.md)和[验证边界](docs/custom-workflows/DELIVERY.md)。仍为 Preview；本地模拟接口通过不等于真实远端 AI 或原生桌面验收。

[![CI](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml)

> 公开仓库：`drunk13232/novel-studio`。GitHub Actions 的实际状态请查看徽章与运行记录；本地验证、云端 CI、原生桌面和真实 AI 验收分别记录，不相互替代。

本地优先的个人AI小说创作工作台。手动写作不需要AI；作者掌握正文、设定和修订的最终决定权。

**当前状态：Preview / PARTIAL；本地开发预览，公开发行以 Releases 为准；完整验证边界与发行说明见 [Releases](https://github.com/drunk13232/novel-studio/releases)。许可证：Apache-2.0；Copyright 2026 drunk13232。** [English](README_EN.md)

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
