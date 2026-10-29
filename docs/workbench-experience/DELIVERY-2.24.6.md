# Novel Studio 2.24.6 — Save Integrity Preview

Local delivery · 2026-10-29 · Preview / PARTIAL

本轮启用三个子代理分工处理候选暂存、正文保存和记录表单；主代理保存基线、检查交叉调用、统一构建与打包。没有新 Agent 产品功能、依赖、后端接口或数据格式迁移，没有自动 Commit、Push、公开发布或快捷方式更新。旧版保留。

## 已复现的问题

1. 仅检查同一个候选版本也会停掉后续自动暂存。
2. 旧待办/灵感 A 的真实保存回执迟到时，等待期间输入 B 被无条件清空。
3. 对干净正文重复 Ctrl+S 仍发送保存请求；该回执与切章交错时，旧章恢复副本可能收进新章内容。演示中两章正文自身没有变化。
4. 上次保存仍在等待时，新文本的自动保存定时器可能提前触发并被锁拒绝，却未在保存结束后重新安排。
5. 保存等待期间撤销到旧基线时，暂时“干净”的编辑器不能据此允许离开并丢掉撤销意图。

## 实际修复

- 候选检查记住检查前 paused 状态。相同 etag 成功读取恢复正常自动暂存；冲突、错误和本地恢复所需的人工暂停不会被检查解除。
- 记录表单使用既有复合状态的函数式快照比较。仅当前完整表单仍等于提交快照时清空文本；后续新文字、优先级或标签保留。当前章节作用域变化后的迟到清空不处理。未变表单成功后仍沿用原有字段保留行为。
- 干净正文不重复 PUT。保存、恢复副本及可见回执按发起时的项目、章节路径和加载代次验证，绝不借用当前另一章正文生成旧章恢复副本。
- 保存期间可继续输入和撤销。现有自动保存 effect 观察 saving，在回执结束后为仍未保存的文本重新安排保存。
- 现有导航门禁在保存进行中提醒稍候；保存结束后正常离开。它不把模型、后台任务或新导航框架引入写作。

## 实际检查

- 相关后端测试 32 passed；既有保存、候选 CAS、计划记录和交互保护仍通过。
- 候选专项：4 组实际本地界面 + 1 组注入保存 503；同版本自动暂存、保留人工暂停、真实两客户端冲突、A/B 说明独立及处理后只读。
- 表单专项：7 组实际本地界面 + 2 组注入 503；受控及独立灵感表单、新输入/字段保留、页签卸载后保留、未改表单正常清空、失败不清空、演示正文不变。
- 正文专项：3 组实际本地界面 + 1 组注入 503；无变化 Ctrl+S 不写入、等待期间输入后再保存、撤销与导航保护、失败后显式重试。
- 专项使用实际本地业务 API；延迟的是 HTTP 回执，未用假成功替代保存。注入错误单列 FAULT_INJECTION_UI_PASS，不是远端 API 或真实 AI 通过。
- 统一生产前端回归、TypeScript/Vite、Diff 边界、打包资源、安装器的最终结果以发行目录 WORKBENCH-VERIFICATION.json、INSTALLER-VERIFICATION.json 为准，只在实际完成后写入。

## 数据和恢复

测试仅使用各自的公开演示副本与隔离应用数据。真实作品、Final、Canon、State、Knowledge 和用户配置不参与测试写入。受保护文件按本轮开始的当前哈希复核，旧版四个交付文件也逐个校验。原有临时表单和窗口内恢复副本仍有原先的会话边界：离开前请保存或下载；不承诺未保存内容跨重启保留。

## 验证边界

无界面浏览器不等于 Windows WebView2 原生点击验收；中文字符串输入不等于物理拼音输入法通过。EXE 的无窗口打包运行时与隔离静默安装也单独记录。真实远端 AI、原生桌面、物理 IME、系统 DPI 和长时间运行仍未在本轮验证。未调用额外收费模型、未扩展 AI 权限，未宣称启动速度或内存改善。既有大型懒加载 chunk 提示仍保留。

## English

Three bounded fixes improve save integrity: unchanged candidate inspection preserves normal autosave without releasing an earlier manual pause; entry receipts clear text only when the complete composer still matches the submitted snapshot; manuscript receipts and recovery remain bound to the original project, path and load generation.

Clean Ctrl+S avoids a redundant write. Typing and undo remain available during saving, later text is scheduled for autosave after the receipt, and existing navigation protection waits for an in-flight save before leaving. Existing storage, author decisions and writer protection remain authoritative.

Specialized local browser groups: candidate 4 local + 1 injected failure; entry composers 7 local + 2 injected failures; manuscript 3 local + 1 injected failure. Related backend tests: 32 passed. Actual delays apply to real local API receipts. Package/runtime/installer results are recorded only after execution. Native GUI, physical IME, real remote AI and long-duration operation remain separate unverified gates. No automatic Git or public-release action is performed.
