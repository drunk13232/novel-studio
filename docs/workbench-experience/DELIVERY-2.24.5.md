# Novel Studio 2.24.5 — Writing Recovery Preview

Local delivery · 2026-10-29 · Preview / PARTIAL

本轮不自动 Commit、Push、发布 GitHub 或更新桌面快捷方式。旧版保留。实际打包结果、校验值和隔离安装检查见发行目录的 WORKBENCH-VERIFICATION.json、INSTALLER-VERIFICATION.json 与 SHA256SUMS.txt；这些文件只有执行完成后才产生，不将构建计划当作验收。

## 实际问题与修复

- 新待办与修订输入原先会随本章页签卸载而清空。现在同章节会话保留文本、优先级等控件值，并保留未保存离开保护、明确清空和直接返回入口。
- 已处理历史原先显示“已暂存，尚未采用”，并可勾选片段产生无法保存的脏状态。现在显示实际 ACCEPTED/REJECTED 状态，只读片段不再可编辑。
- 初次候选读取失败现在提供重试，保持编辑/采用锁定；关闭后迟到读取不能重新打开旧视图。
- 两窗口冲突可以先检查本地/已保存文本与说明，再由作者明确载入。刚才的本地版本只在当前比较窗口内可恢复；恢复后暂停自动暂存，必须显式保存。关闭或重启不会保留这个临时副本，需先下载重要内容。
- 已在其他窗口处理的记录不会被当作另一份可写候选，也不会把生成原稿冒充实际采用文本。保留本地下载入口，历史用于核对真实采用文本。
- 冲突未解决时“暂存并关闭/继续”禁用并说明原因，继续比较、下载和明确放弃仍可操作。
- 显式拒绝候选发出项目作用域本地事件，立即更新本章列表；拒绝不修改正文。
- 短窗口原先可把工具入口压至约 1px 高。保留工具条最小可点击高度，编辑区在小高度窗口允许伸缩，避免入口落在裁剪层后。侧栏底部预留滚动避让，短窗口不固定工具内标题，避免浮动助手和标题遮挡底部操作。

## 验证口径

- 后端相关候选存储、交互保护、计划记录：32 passed。
- 片段合并边界：13 checks passed；不是本轮重新实现 Diff 算法。
- TypeScript 与生产 Vite 构建执行；仍存在既有 Monaco/PDF/时间线的大 chunk 提示，不将其描述为已消除。
- 隔离演示数据上的实际生产前端与本地业务 API 验证：表单保留、导航保护、只读历史、并发版本比较与恢复、明确保存、拒绝刷新。
- 读取失败重试使用一次注入的 503；该项单列 FAULT_INJECTION_UI_PASS，不是远端服务成功或真实 AI 验收。
- 中文字符串、Ctrl+S、撤销、重存和切章重开使用 CodeMirror 与实际本地保存通道；不模拟或宣称物理拼音输入法通过。
- 迟到读取与英文小窗口的执行结果详见交付 JSON。无界面浏览器检查不等于 Windows WebView2 原生桌面验收。
- EXE 的无窗口打包运行时检查、安装器隔离静默检查分别记录，不冒充桌面窗口点击通过。

## 数据与权限

既有正文、Final、Canon、State、Knowledge 保护、项目作用域、etag 和人工采用接口不变。所有测试写入独立公开演示副本；受保护数据按本轮开始的文件哈希进行末次核对，结果仅报告数量。没有新依赖、Agent、后端接口、数据库迁移或任意文件权限。未调用远端模型，未修改全局 Codex 配置。构建使用现有裁剪源包和许可收集机制，不包含本轮私有测试目录。

## English

This local Preview fixes discarded chapter-task input, falsely editable handled history, non-retryable initial reads and awkward concurrent-candidate recovery. Inspect both versions before an explicit load; restoring the window-local copy requires manual save. That temporary copy does not survive closing or restart. Existing persisted candidate drafts remain recoverable through the original records and backups.

Rejected proposals refresh Current Chapter via a scoped local event. Handled records are read-only, and unsatisfied save-and-leave actions are disabled with an explanation. Short windows retain a clickable author-tool strip instead of shrinking it to approximately one pixel.

Related backend tests: 32 passed. Hunk boundary checks: 13 passed. Production-browser checks, one injected read failure, packaged runtime, installer checks, native desktop and real AI are distinct gates. Exact completed results are recorded in release verification JSON files. Physical IME, native WebView2 interaction, real remote AI and long-duration usage remain unverified for this update. No startup or memory improvement is claimed.
