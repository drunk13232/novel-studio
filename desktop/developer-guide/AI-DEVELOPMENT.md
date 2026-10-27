# Novel Studio：给 AI 与开发者的接手说明

本说明随 Windows ZIP 一起分发，帮助 AI 定位已有实现、理解保护规则和安排局部开发。

## 先确认你拿到什么

- `NovelStudio.exe`、`_internal/`：PyInstaller 的运行产物；`_internal/resources/frontend` 是编译后的 React 资源。
- `AGENTS.md`：本运行包的 AI 阅读规则。
- `ARCHITECTURE.md`：原始源码入口与业务边界。
- `DEVELOPMENT.md`：拿到源码后的安装、隔离开发与打包步骤。
- `README.txt`：普通用户启动说明。
- `_internal/resources/third-party`：第三方依赖许可证与通知。

**运行 ZIP 与开发源码 ZIP 分开。** 同版本 NovelStudio-Developer.zip 包含筛选后的 React、FastAPI、脚本、项目 Skills、模板与依赖锁文件；不含用户私稿、凭据和用户级插件环境。源码清单见 SOURCE-MANIFEST.json。取得提供者的使用/修改许可后再维护。本说明不新增源码授权，也不提供不存在的公共仓库链接。

其他电脑不需要沿用开发者的盘符。不要扫描全盘寻找私稿；由用户指定源码根、小说工作区及测试目录。

## 当前实现概况

软件为 React + Vite 前端、FastAPI 后端、PyInstaller + pywebview/WebView2 桌面窗口。手动写作不依赖 AI 网络。

当前包保留作者工作台、知识关联、修订、文献、图库、导出、数据中心；拥有 Codex 小说工作流、自定义 LLM API 与受控软件助手。字体可以独立设置，文学主题有六套：月白纸笺、青岚书房、夜墨星河、琥珀书灯、雾蓝晨光、紫檀夜读。

源码依赖声明中的关键版本：Codex Python SDK `0.160.1`、MCP `2.3.0`、OpenAI Python SDK `3.28.0`。前端与其他依赖以对应源码的 `package-lock.json`、`requirements.txt` 为准，不按记忆降级或升级。

2.8.3 增加首次启动、本机字体检测与排版预设、合并保存、实际工具目录；四个新增 MCP 工具复用原有 Level 1 Action。不代表完成运行验收。

## 一项任务的正确接手顺序

1. 确认源码身份、用户授权范围与根 AGENTS.md；先阅读对应模块，不重新实现已有功能。
2. 记录准备修改的源文件。触及数据格式前阅读现有 Schema、etag/hash、锁与备份逻辑。
3. 普通外观修改只走 CSS、React 组件与现有偏好设置，不触碰作品文件。
4. 功能改动复用已有服务，增加必要类型/Schema 与调用，不以原始文件写入代替业务接口。
5. 模型请求产生建议；受控 Action 产生真实操作。以 Dispatcher 与前端回执判断成功，不以模型文字判断成功。
6. 按用户授权决定是否构建、运行最小检查或打包。未运行的部分明确写“未验证”；不用 API 成功冒充桌面交互成功。
7. 生成新目录中的包，保留回退。不要把运行包中的私人配置复制到公开源码包。

## 常见改动入口

| 需求 | 首先阅读源码 |
| --- | --- |
| 主题/字体/设置 | `web/frontend/src/font-settings.tsx`、`typography.css`、`night-studio.css`、`settings-center.tsx`、`studio.tsx`；后端 `app/studio.py` |
| 增加主题 | 同步主题卡片、CSS tokens、前端 ThemeId/深浅色映射、Preferences 校验，以及 `app/assistant/models.py` 的 Theme/Context 枚举 |
| 正文编辑 | `writing-editor.tsx`（CodeMirror）、`studio.tsx`；保留输入法、光标、草稿恢复、etag 冲突机制 |
| 版本 Diff | `selection-diff-editor.tsx`（Monaco Diff）、`author-workbench.tsx`、现有修订服务 |
| 新增受控软件操作 | `app/assistant/actions.py`、`models.py`、`service.py`，以及 `studio.tsx` 的已有前端回执入口 |
| MCP 稳定性 | `app/assistant/codex_mcp.py`、`mcp_bridge.py`、`mcp_server.py`；不是新建规划模型 |
| 连接自定义模型 | `app/ai/center.py`、`provider.py`、`credentials.py`、`models.py` 与 `ai-settings.tsx` |
| 项目或文件保存 | `app/projects/service.py`、`app/workspace/service.py`、已有 domain/library 服务 |
| 备份/打包 | `app/library/data.py`、`desktop/launcher.py`、`NovelStudio.spec`、`build.ps1`、`package_zip.py` |

## AI 机制必须区分

- **Codex 小说工作流**：有项目范围、Skills、任务历史与独立线程；不能跨小说复用不应共享的 Context。
- **普通 LLM API**：文本、候选、只读分析，不天然获得文件权限；Function Calling 能力按实际配置验证。
- **Codex 软件操作**：Codex 是 MCP 客户端；本软件提供本地 stdio MCP Server，经认证回环桥转到现有 Action Registry。
- 原生 MCP 初始白名单为十二项：list_projects、open_project、open_chapter、search_characters、open_character、set_theme、get_project_status、create_character_draft。它不是全部应用 Action，也不是任意系统操作。
- SDK/MCP 连接复用仅限同项目、同权限、已结束且无待确认的可信会话；切换项目不得沿用旧操作上下文。
- 人工确认记录在应用执行层保存，独立于模型 Turn。重启会安全取消旧待确认建议，不自动恢复写操作。

## 可直接交给 AI 的任务模板

```text
请协助修改 Novel Studio。

源码目录：<我提供的完整源码根>
目标：<具体界面或功能>
允许修改：<模块/文件范围>
真实作品：只读保护，不用于测试写入。
测试工作区：<独立临时目录，或暂不允许运行>
验证要求：<仅构建 / 指定最小检查 / 不验证>
是否打包：<是/否；使用新的发行目录>

先读源码 AGENTS.md 与包内 AI-DEVELOPMENT.md、ARCHITECTURE.md。
检查现有实现，优先复用。不要修改全局 Codex 配置或登录，
不要生成小说、修改 Canon/State、自动提交 Git 或发布。
若没有完整源码，先明确说明缺失，不声称已完成源码修改。
报告实际改动和真实验证边界。
```

## 已知交付边界

部分 AI 操作有历史隔离检查证据，但本包说明不是验收证书。原生输入法、完整桌面助手操作、其他电脑兼容性和云端模型表现，必须在获得用户授权后单独确认。第三方接口未知能力不得标为已验证；真实收费请求需遵守用户许可。

## World Logic Lab V2.9

工程模块：web/backend/app/world_logic 与 web/frontend/src/world-logic.tsx。先读 docs/world-logic 的格式、安全、验收和适配器指南。复用现有 TaskManager、AICenter、Action Registry 与 Data Center；禁止从导入 YAML 动态执行 Python、任意 Shell、SQL 或安装插件。求解进程必须保持超时、内存与数量限制。实验只读 Canon，AI 验收提议不能改变历史冻结条件。


## AI 写作上下文与场景协写

正文集成在 web/frontend/src/writing-assist.tsx 和 selection-assistant.tsx；服务为 app/creative/writing.py，知识筛选复用 app/creative/state_view.py 与原有 knowledge_isolation 凭证函数。新功能只写本项目 metadata/studio/writing 候选记录；不得建立第二套 State 权威。维护时保留上下文显式审阅、来源预算、选区 UTF-16 与版本校验；事实候选只能通过有效 Final witness 进入既有 Memory / Proposed / Validation / 作者 State Commit。定向检查见 tests/test_writing_assist.py；全部使用临时原创演示项目。


## AI Creative Director (2.10.3 Preview)

入口是正文工具栏“AI 创作指挥台”，运行包使用说明见同目录 `AI-CREATIVE-DIRECTOR.md`；完整源码说明见 `docs/creative-director/README.md`。

先读 `app/creative/director.py`、`director_skills.py`、`creative-director.tsx`。它们复用现有 WritingAssist 的 Writer-safe Context、AICenter、TaskManager、ReviewCenter 与 Monaco Diff，不创建新的 Agent、模型路由器或状态权威。任务记录位于对应作品 `metadata/studio/director/`，含私人草稿和指令，禁止作为公开模板打包。

三个模式是快速直接执行、单场景导演、最多四步深度执行。实际 Skill 正文有按次加载凭证；普通 Provider 仅接收任务书和已批准安全包。停止当前请求与暂停后续调度必须区分；旧 stream 不会恢复，作者新要求从本地检查点发起新请求。预算、取消回执、精确 source revision 与 Final 修订保护不得绕过。报告不能未经安全筛选直接传给 Writer。真实 DeepSeek 需用户自行配置，兼容测试服务不是远端模型验收。

### 2.11.1 状态工作流维护提示

文件型 Codex 任务如果被 Windows 沙盒拒绝启动，不可扩大整个用户目录或根文件系统读取权限来掩盖问题。状态闭环已经使用现有纯文本 Adapter，由应用读取限定作品资料并调用原有状态函数。文本回合结束不代表语义门禁通过，更不代表文件操作完成。

修改时优先检查 `creative/state_bridge.py`、`state_tasks.py`、`writing.py`、`director.py` 和既有 `scripts/novel_workflow.py`。禁止给 UI 直接写 State 的捷径，禁止伪造语义 PASS，禁止取消作者的独立 Commit。新的格式、资源或历史记录必须经过现有公开打包白名单，不复制开发机数据。


### 2.15 世界创作工作台维护

先读 docs/worldbuilding-studio/README.md 和 TEMPLATE-FORMAT.md，再读 app/library/world_studio.py、world_templates.py 与既有 bible.py。只扩展 Category/Entity 与原 Bible 文件树，不建立第二套 Canon、实体数据库或 Agent。后台批次完成使用原系统写锁；HTTP 方法只借用中间件已经持有的真实锁。取消令牌、逐项采用、模板快照、原文版本与 Writer 可见摘要必须保留。私人的设计稿、模板实例、实验资料及 private-checks 不得进入公开源码包。世界蓝图是作者构思，历史候选不是已提交事件。


## World Model & Memory (2.16)

Extend Bible fields and Entity.periods rather than adding a rule store. WorldModel coordinates existing reference notes, Knowledge FTS and WorldLogic. Keep author history separate from committed State projections; never use latest fields to fill unknown history. Rule/source changes invalidate prepared mappings and Writer approval. Imported text and expressions remain untrusted data. See WORLD-MODEL-MEMORY.md and the included docs/world-model contracts. No private-checks files belong in a public candidate.
