# Writing Reliability — 2.24.9 Preview

## 简体中文

本版继续使用现有 AI 创作指挥台、Writer、TaskManager、受控 MCP Action 与候选 Diff，不增加新调度框架。

1. **四种状态分开看**：模型回合完成、正文交付量、Diff 候选、作者采用彼此独立。可设置章级目标；不足时显示差额，不自动放宽目标。全书校验每章只计当前正文或作者明确选择的一个完整候选，源版本变更后提示重新核对，不写入码字统计或 Canon。
2. **失败后继续原任务**：检查点保存保留文本、已完成步骤与预算。作者明确继续后只执行剩余步骤；重复暂存未变结果返回已有候选。进程重启后无法确认已用耗时，需要先明确审阅预算，不能把未知耗时当作零。
3. **先检查输入预算**：本地预检检查实际下一步输入与保守的后续增长估计，不调用模型；估计不是精确 Token 计数。修改任务后旧预检失效。不自动删去必要资料、增加限额或跨服务商回退。
4. **补充场景接口**：现有步骤可填写目标、阻碍、选择、后果、入口状态与出口状态。真实执行位置告诉 Writer 当前步骤及剩余步骤。确切重复长段落可以定位供作者审核，不能自动判文学错误或删文。
5. **配套 Codex 运行时**：默认使用 Python SDK 配套的 CLI，保留显式覆盖。包内已核对 SDK/CLI 0.160.1；复用现有登录，不包含登录凭据，不重写全局配置。
6. **源与复核时效**：编辑候选后重新核对；旧 Diff 或旧复核不再冒充当前版本。空结果不会把写作步骤标为完成。

### 实测与边界

- 本地相关后端测试 72 项通过，前端生产构建通过，隔离浏览器 11 项交互检查通过。
- 当前登录的 Codex 通过现有 MCP/Action 链路实际生成、保存和读取原创隔离候选；31 章明确选择的候选合计 102,115 汉字。它们未被作者采用，没有进入正式作品、Canon 或码字统计。
- 编排由授权操作者显式发起并确认，不宣称一次模型 Turn 自主写完十万字；字数达标不是文学质量证明。
- 同一失败任务真实保留 486 字前缀、继续剩余两步，得到 2,044 / 2,400 字，仍如实显示不足。
- 同一基础模型复核一章 5,214 字候选：12 处引用中 10 处定位成功，2 处未核实并标出；不是独立模型共识，也没有完成全书文学终审。
- 现有 Data Center 备份恢复到新隔离项目，31 章候选及选定版本完整；正式正文仍未自动采用。
- 最终 EXE 的 MCP/WASI 入口、配套 CLI、包内完整性及静默隔离安装/卸载已执行。原生窗口点击、实体中文输入法、系统 DPI 与长期写作体验未在本轮重新验收，不能用浏览器/worker 代替。
- 四步真实生成任务的已记录耗时约 90.68–176.99 秒；没有同条件加速对照。配套 CLI 让 ZIP 比 2.24.8 增加约 142.49 MiB。
- 真实试写稿、模型会话、个人资源、凭据和私有审计记录均不进入公开源码及 Windows 包。

## English

This Preview extends the existing Director, Writer, TaskManager, scoped MCP actions and candidate Diff. It adds no orchestration framework.

- Model completion, delivered prose, staging and author adoption are distinct. Chapter targets report shortfalls honestly. Book checks count one current manuscript or explicitly selected full candidate per chapter, validate freshness, and never alter writing metrics or Canon.
- Durable checkpoints retain prose and completed steps. Explicit resume runs the remaining steps; unchanged staging is idempotent. Unknown elapsed time after a process restart requires an author budget review.
- Local next-step preflight estimates actual input and conservative future growth without calling a model. Estimates are not exact token counts. Edits invalidate earlier checks; providers and limits never change silently.
- Optional scene intent and entry/exit conditions plus actual execution position support continuity. Exact repeated passages are located for author review, never automatically deleted or treated as literary verdicts.
- SDK-paired CLI 0.160.1 is included; explicit overrides remain supported. Existing login is reused; credentials and global user configuration are not shipped.
- Edited candidates no longer claim stale Diff/review results as current. Empty responses cannot complete a writing step.

Validation is separated by gate: 72 related local tests, production frontend build, 11 isolated headless-browser interactions, real Codex/MCP drafting and recovery, frozen MCP/WASI workers, isolated silent installer and backup/restore. A controlled 31-chapter trial selected 102,115 candidate Han characters, without author adoption or Canon/statistics changes. This was author-directed orchestration, not a single autonomous model turn. Length does not establish literary quality. One same-model sample review verified 10 of 12 quotes and flagged the other two; no full-book literary approval is claimed. Native GUI, physical Chinese IME, system DPI and long-duration personal use remain unverified in this iteration. Private trial data is excluded from public artifacts.
