# Novel Studio 2.24.19 — 助手导航与正文输入保护

本地 Assistant Navigation Safety Preview / PARTIAL。公开版本仍以 Releases 为准，本轮不自动发布或更新快捷方式。

## 使用

通过软件助手已有结果的“打开文档”“查看正文候选”“查看创作任务”导航时，可以继续编辑。若读取返回前产生未保存输入，软件保留原编辑器并停止该次跳转，提示先保存或处理修改；作者 Ctrl+S 保存后，可以再次明确点击原入口。

作者已经切换页面、章节或发起较新的导航时，较早读取失效。文件没有真正读成功，就不会继续展示对应候选或创作任务。失败后重新点击会清除该结果按钮的旧错误；旧请求的错误不能覆盖较新的操作。

保留现有 Action Registry、作者批准、源版本、Diff、自动保存、恢复与 Canon / State / Knowledge 隔离。没有新增依赖、数据格式、迁移、Agent 或文件权限。

## 实际证据

旧 2.24.18 的三个入口在隔离项目中均复现过：持有真实 GET 响应时继续键盘输入，迟到响应触发旧磁盘正文重载并丢失新缓冲区；磁盘原文未改变。使用允许关闭自动保存和恢复的真实设置，不使用正式作品。

修复后 18 条 headless 指针/键盘流程通过：三个入口分别覆盖等待期间输入、正常打开、受控文件读取失败与明确重试、作者先离开页面、新请求使旧读取失效、旧错误晚到。另有一条独立流程实际 Ctrl+S 保存被保留的新输入，再重试导航，磁盘和重开内容一致。错误场景使用明确标注的本地 HTTP 503 注入；不是物理磁盘故障、真实 AI 或原生 GUI 验收。

57 项相关后端回归通过（133.50 秒），TypeScript / Vite 生产构建通过。确定性本地操作没有模型调用，未产生远端推理费用。版本元数据与 Windows 包在这些源码检查后统一更新；包体、冻结源码对齐、EXE worker、隔离安装、ZIP 和数据保护结果记录在本地交付回执，不能从“已构建”推断“原生 GUI 全部通过”。

## 验证边界

本轮动态浏览器证据集中在三个正文结果入口。人物、世界条目、文献、报告读取复用相同守卫并通过类型构建，但未逐项开展桌面交互验收。未进行新的真实 Codex/MCP、云端模型、实体中文输入法、系统 DPI、语音或长期使用验收。模型请求发起前的上下文准备属于另行排查范围，不以导航检查证明它已全面通过。恢复副本的窗口内边界继续沿用既有说明。

## English

Local Preview / PARTIAL. Delayed assistant-result reads recheck live project, page, document ownership, newer navigation and unsaved input. New typing stays in its original editor; save and explicitly retry. Failed or superseded file loads cannot proceed to candidate/director display. Retry clears its own error and older requests cannot overwrite newer feedback. Existing Actions, approvals and source guards remain.

Eighteen actual headless pointer/keyboard flows plus one explicit Ctrl+S/retry flow passed in isolated synthetic data. Negative read cases deliberately inject local HTTP 503; they do not prove real disk-fault or native desktop handling. Fifty-seven scoped backend tests passed in 133.50 seconds. No cloud AI was called. Packaged-worker/silent-install checks are separate from native GUI, physical IME/DPI, voices and real Codex/MCP acceptance. No automatic new public release.
