# Novel Studio 2.24.22 — Safe Exit Reliability Preview

本地 Preview / PARTIAL。未自动上传、提交或更新快捷方式。

## 安全退出

退出准备分为任务检查、正文保存或恢复副本、布局与阅读位置保存。此时仍可点击返回写作、关闭或 Esc 撤销本次退出；实际已发出的保存仍按真实结果完成，不伪装成已经撤销写入。迟到回执不能恢复旧退出或影响新弹窗。每次异步准备后核对当前项目、文件、页面、输入法组合和未保存内容，保存是否完成采用实际结果而非迟到的界面标记。

一旦调用桌面退出接口，既有桌面端会检查退出备份并关闭窗口，这个接口没有撤回能力。界面此时明确显示桌面接管，不再提供虚假的取消；成功回执表示已接受关闭，弹窗保留至窗口实际销毁。接口缺失、拒绝、备份或关闭准备失败仍显示原因并允许恢复或明确重试。

桌面桥增加小范围非阻塞互斥保护，重复接受的退出不会重复备份或创建关闭线程；退出备份返回后复查已有应用任务。创建关闭工作线程失败时恢复保护状态。保留原有“等待 JS 回复线程结束后才销毁 WebView”的约定。没有新增桌面权限或取消 RPC。

## 实际证据

27 个独立 headless 浏览器场景：15 个退出流程、12 个上一轮离开弹窗回归。真实本地保存、恢复、偏好设置 API；退出边界仅使用明确标记的记录/拒绝替身，没有关闭真实窗口。9 项 launcher/readiness 测试直接运行实际 Bridge 逻辑，使用假的窗口和备份回调验证互斥、备份前后任务检查、失败重试及回复线程次序；readiness 用真实回环 HTTP 服务。

旧版在四个准备阶段均复现：返回写作并继续输入后仍调用桌面退出接口。原始观察保留。开发中发现正常保存完成后的 React 标记短暂滞后，已按真实保存结果与同步锁判断，保留原始失败并重新通过正常保存退出检查。模拟 HTTP 503、模拟桌面拒绝及线程创建故障不是物理磁盘故障或真实原生窗口验收。

原生 Windows 窗口、实体中文输入法、系统 DPI、真实语音/云端 AI 和长期使用未新增验收。没有操作桌面鼠标键盘或系统输入模拟。作品、Canon、State、Knowledge、Final、全局 Codex 配置及旧包保持保护；公开 Allowlist 仍是上次已发布版本。历史隔离服务退出异常原因仍未知，不以本轮干净关闭宣称根因已解决。

## English

Scoped exit preparation stays cancellable before the desktop boundary. Late checks/writes cannot revive cancelled or superseded exit attempts. Actual save completion and live scope are rechecked; errors remain inside the dialog and retries are explicit. Native dispatch is shown truthfully as non-cancellable, and its accepted receipt does not claim that a still-visible window is already closed.

The existing native bridge uses a small non-blocking preparation guard, idempotent accepted closure, a post-backup owned-task check and a retryable close-worker-start failure. The original reply-worker join is preserved. No new dependency, framework, migration, data format, permissions or desktop RPC.

27 headless browser flows and 9 launcher/readiness checks passed. Desktop boundaries, windows, backup callbacks and fault injections are clearly controlled test doubles; no native GUI, physical IME/DPI, voice or real-cloud-model acceptance is claimed.
