# Novel Studio 2.24.26 — Bounded Chapter Opening Preview

RESULT: PARTIAL / Local Preview. No new public release or shortcut update.

## 实际问题与修改

原版打开章节使用 Promise.all 等待正文和恢复副本，任一请求不返回就持续隐藏编辑器。隔离复现 12 秒后仍停在加载状态且没有取消入口。现有读取现在按本次控制器、项目和载入代次归属，两个 GET 共用 10 秒响应头/JSON 正文时限；作者可取消，后续打开、换项目或返回书架会停止旧读取。请求失败停止其尚未完成的配对读取，完成的正常读取不伪造取消事件。只在完整同路径响应通过校验后应用正文和恢复副本，未完成的恢复检查不能被忽略。

加载中暂停原编辑器的自动保存触发，并在实际保存入口检查读取归属；这是防止对隐藏旧章节误发保存，不取消、重放或修改已提交保存。失败/取消保留原有文字与恢复信息，沿用已存在的编辑器状态缓存；真实未保存输入和撤销/重做通过，无须重写编辑器。取消后不弹出已启用的开写仪式。失败只由作者显式重试。

原版工作区恢复先打开默认/上次正文，再打开保存标签，导致相同目标也重复读取。对照实际未修改的 2.24.25 发行前端，同目标与不同目标两项场景均为 4 次 GET；新版本先选择最终目标，各为 2 次（正文和恢复副本各一次）。保留概览标签的正文上下文、显式“继续写作”的目标语义及只读正式稿。仅证明请求数量减少，不声称启动耗时或内存下降百分比。

## 实际验证

39 项隔离 headless：12 项章节读取，5 项工作区恢复，12 项保存回执/格式，6 项保存核对时限，4 项只读磁盘快照。覆盖响应头、流式 JSON 正文、恢复读取停顿、显式取消、初次打开取消、后续打开取代旧请求、回书架、503、错误路径响应、正常及短暂延迟读取、未保存缓冲区与撤销/重做。保存事件游标和磁盘字节核对；仅未保存输入用例允许既有恢复副本维护，不允许正文写入。

原生 AbortError 来自真实浏览器 fetch/JSON 读取，非仅观察 UI 标签或对完成的信号调用 abort。前后对照和错误测试调用记录保留；重复运行不累计通过数。已有保存核对测试现在仅观察保存阶段，避免把新增章节读取的独立 AbortSignal 错计成保存请求。

简中和英文文案，其他语言既有回退。没有新依赖、Agent、数据库格式、迁移或权限扩大。正式用户数据、Canon/Final/State/Knowledge 不参与写入测试。原始保存 PUT 和恢复副本维护写入未新设超时；浏览器读取消不保证后台立即结束。先前候选外的全局配置漂移与更早隔离服务退出异常不在此声称已归因/修复。

## English

Chapter and recovery reads have one owned, cancellable 10-second deadline including headers and JSON bodies. Complete matching responses are required before applying state; failed/cancelled reads preserve existing text and do not bypass recovery. New reads and scope changes cancel obsolete reads. Existing undo/redo caching is reused and verified. Workspace restoration resolves the target once: retained v2.24.25 made four GETs in both measured scenarios; the new implementation makes two. No elapsed-startup or memory claim is inferred from request counts.

Thirty-nine isolated headless cases passed; no AI request. Native window interaction, physical Chinese IME, actual system DPI, voice and cloud AI are UNVERIFIED. Packaged worker and silent installer checks, if recorded in the delivery report, are separate from graphical desktop acceptance. No publication, shortcut replacement, personal data move, global Codex edit or Git commit/push.
