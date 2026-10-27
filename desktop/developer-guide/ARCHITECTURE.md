# Novel Studio：源码结构与数据边界

以下是**完整源码工程**的相对路径，不是运行包当前目录的文件清单。路径如不在你取得的源码中，应先确认版本，不能猜测并新建第二套系统。

## 结构

```text
web/frontend/            React、TypeScript、Vite；锁文件管理前端依赖
  src/studio.tsx         主工作台、当前项目、导航、偏好与前端 Action 回执
  src/api.ts             已有请求辅助、会话请求校验与远端资料授权提示
  src/settings-center.*  设置分类、搜索与分区滚动
  src/font-settings.tsx  字体、主题卡片与 ThemeId
  src/typography.css     字体、排版及主题预览
  src/night-studio.css   文学主题颜色 tokens
  src/writing-editor.tsx 正文 CodeMirror 编辑组件
  src/selection-diff-editor.tsx  Monaco Diff
  src/author-workbench.* 标签、分屏、待办、修订与导入等入口
  src/knowledge-*.tsx    知识与关联界面
  src/software-assistant.*  软件助手聊天/确认/执行状态
  src/ai-settings.tsx    API、模型路由、用量与帮助
web/backend/
  requirements.txt       后端依赖声明
  app/config.py          环境变量与工作区配置
  app/main.py            FastAPI 组装、会话/来源保护、已有路由
  app/studio.py          工作台偏好、正文目录与恢复副本
  app/projects/          项目注册、创建与创作模式
  app/workspace/         文件范围、内容版本与安全保存
  app/domain/            人物/规划/候选/任务等领域服务
  app/library/           设定、文献、图片、知识、索引、数据中心
  app/tasks/             TaskManager、路由、历史、任务锁
  app/codex/             小说工作流 Codex SDK 与项目指令隔离
  app/ai/                普通 API Provider、路由、参数、系统凭据
  app/assistant/         受控应用操作、确认、Codex MCP 与分段计时
  app/integrations/      Research、Story 投影及其他已有接入
scripts/                 小说工作流、Context 与 Knowledge 约束
.agents/skills/          已有项目 Skills（不是用户全局登录配置）
.novelforge/             已有 NovelForge 资源，注意第三方许可
engine/templates/        项目初始化模板
schemas/                 已有数据约束
projects/                小说项目；可能包含真实私稿，不能随开发包分享
web/runtime/             运行元数据/中间产物；不能随源码包分享
release/                 构建输出，保留旧版本
desktop/                桌面窗口与发行打包
  launcher.py            桌面窗口、单实例、回环服务与退出清理
  NovelStudio.spec       PyInstaller 收集范围
  build.ps1             现有安装包构建入口
  package_zip.py         发行包限制与 ZIP；自动附开发说明
  developer-guide/       本说明的唯一维护来源
```

## 四类位置

1. **应用源码**：React / Python / 脚本 / 模板，可以做授权范围内的软件改动。
2. **安装目录**：EXE、_internal、依赖、编译资源与说明。字体来自操作系统，不随包复制。
3. **小说工作区**：由用户选择；projects/<稳定项目ID> 才是一本作品。根目录遗留模板不是当前小说。
4. **个人应用数据**：偏好、阅读位置、AI 非敏感配置与历史等。由 `NOVEL_STUDIO_HOME`、`NOVEL_STUDIO_DATA`、安装目录旁 `data-location.json` 和启动路径决定；按实际代码确认，不假设目录相同。

小说正文、Canon、已提交 State/Knowledge/Timeline 是受保护数据。SQLite/FTS 是关联与可重建索引，不替代 Canon。

## 请求与执行

```text
React → src/api.ts → FastAPI 路由 → 已有项目/领域/文件服务
软件助手 → 校验 Action → 权限/项目/版本检查 → Dispatcher
         → 如需确认：固定 Proposal → 用户确认 → 重新校验 → 执行
         → 如需导航：前端 claim → 既有导航 → 真实执行回执
Codex（软件操作） → stdio MCP → 经认证回环 Bridge → 同一受控 Action
普通 LLM API → 文本/审稿/修改候选 → 作者 Diff 确认 → 既有修订保存
```

不要把 AI 文字“已完成”解释为真实执行。停止、拒绝、过期、项目切换后的迟到回执不能触发新的写入。

## 已有保护要点

- API 回环监听、来源/Host 与 X-Novel-Request 会话校验继续保留；开发请求复用 src/api.ts。
- MCP 桥使用临时认证、会话代次与操作白名单，不向普通网页开放密钥或执行通道。
- 保存使用 etag/hash 与服务锁；冲突可见，不静默覆盖，不无限重试非幂等请求。
- Confirmations 的 action_id、项目/会话、固定参数、资源、expected_revision、权限、过期、状态与执行回执不可省略。
- API Key 使用现有 keyring/会话机制；常规 Provider API 不返回完整密钥。外部 API 使用 HTTPS，本地 HTTP 仅限回环。
- Writer View 与 Author/Checker View 分开；隐藏真相不能以“禁止写出某秘密”的句子进入 Writer。
- 文献、Research、Outline、AI 候选与灵感不是已提交事实；State Commit 只走已有验证与作者批准。

## 2.11.1 创作闭环边界

- `web/backend/app/creative/director.py` 在应用层绑定指挥与执行 Provider；第三方文本模型不是 Codex 内部线程。不要自动跨服务商回退。Skills 来源和实际方法应用保留在任务书中。
- `creative/state_bridge.py` 连接现有语义 Final、Memory、Diff 与本地 Commit。已提交章节禁止重跑会覆盖历史 witness 的 Final / Memory；重新审稿或改正文使用既有独立修订入口。
- `creative/state_tasks.py` 复用文本 Adapter、TaskManager、项目 Skills 和原有 `scripts/novel_workflow.py`。模型只返回结构化语义数据，应用写报告与 Proposed；不要给模型扩大 Shell 或文件权限。
- 时间来自作者明确输入的结束状态锚点，不自动来自大纲；它不是各动作的精确发生时刻。知识来源未知时保持 UNKNOWN，不能从一句对白补造 acquired receipt。模型失败的候选必须保留并阻止提交。
- State Commit 必须匹配正文、Final、语义 Diff review、Validation、基线和 proposal 哈希，并有独立作者确认。重复有效提交幂等；提交后刷新正文保护与 Writer Context。
- `creative/writing.py` 与 `state_view.py` 读取已提交角色知识、关系、物品和身体状态的安全视图，不将反事实与创作素材当作事实。
- `state-workflow.tsx` 复用 StudioDialog 展示完整 Diff；不要把大量操作压缩到正文工具条的小滚动区。
- 开发验证只用隔离的原创演示数据。`docs/*/private-checks`、本机用户作品和运行历史不属于公开源码或发行包。
