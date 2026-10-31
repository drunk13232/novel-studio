# Novel Studio 2.24.28 — Shutdown Admission Preview

RESULT: Local Preview / PARTIAL. This combines the completed lifecycle and task-admission fixes. Previous local/public 2.24.27 remains available; this version is not automatically published or assigned to a desktop shortcut.

## 修复范围

- 服务启动前登记回收动作。启动失败、生命周期异常、取消或某一关闭方法报错时，继续尝试其余服务；单个错误/取消原样返回，多个错误用标准异常组保留。
- 在等待首个服务/线程回收前，先关闭主、项目、草稿及已有文献任务管理器的入口。关闭中的项目/草稿工厂与 prepared 入口拒绝新任务，不再初始化其后续执行。
- 排队任务先取消，再请求运行中的任务中断。已排队但尚未执行的任务再次检查关闭标记，不能在关闭后启动新的执行或模型请求。
- 单个中断失败时，仍处理其他任务；只尝试关闭该任务自己的既有 adapter。等待真实 runner 结束后返回，保留中断/关闭错误及意外 runner 异常；正常取消不冒充关闭失败。
- 启动器依据后端实际 shutdown_failed 标记记录错误，不再始终写“干净退出”。原有作者退出确认、备份及写入等待保留。

## 验证边界

64 项不同的相关本地检查通过（42 项生命周期/任务/退出保护/恢复 API，加 22 项既有任务恢复、模型参数及监督回归）。最后三项收尾门禁/异常聚合复核为重复检查，不另加数量。模型参数请求使用 MockTransport；固定本地 adapter/runner 用于明确故障注入。假窗口退出测试不代表原生窗口验收。没有真实 AI 请求。

真实回环 HTTP 正常及注入关闭错误两项场景，已检查认证正文保存、回读、版本化恢复副本及退出后的精确 BOM/换行字节。关闭错误保留为失败状态，相关管理器及图片/备份线程已停止。只有隔离演示草稿改变。

本轮用于原 WinError 10054 调查的五个 headless 浏览器场景在与桌面相同的 30 秒配置下通过并正常退出；这是任务修复前的诊断组合，不作为最终新二进制的 GUI 验收。当前轮没有重现该异常，根因仍未确认。完整桌面点击、实体中文输入法、系统 DPI、真实 Codex/MCP/语音工作负载未新增验收。打包和交付后的实际检查另记交付报告；本说明不预先声称这些已通过。

不修改标准库、不切换事件循环、不提高现有超时、不按进程名强杀。某个关闭方法永远不返回或外部系统故障，不在本次异常收尾保证内。恢复副本仍不能替代独立作品备份。无新依赖、数据迁移、权限扩大或正式作品写入。

## English

Register cleanup before startup, retain the existing close order/thread dispatch, continue other closers after errors, and preserve single failures/cancellations or explicit groups. Stop admission for known main/project/draft/reference managers before the first service wait. Closed factories and prepared calls reject new work; queued runners recheck admission and are cancelled before active interruptions can release the queue.

One interrupt failure no longer skips other owners. The fallback uses only that task's existing adapter close. Shutdown waits for actual runner completion and reports unexpected runner errors; expected cancellation is not a failure. Launcher logging uses Uvicorn's real shutdown-failed flag. Existing author exit/backup/write protection remains.

64 unique targeted local checks passed, plus three separately identified repeated guard checks. Protocol tests use MockTransport and task tests use fixed local workers, not remote AI. Two real loopback save/recovery/shutdown runs preserved exact bytes and reported an injected close failure. The five headless diagnostic cases preceded the task fixes; they do not prove final native GUI acceptance. Original WinError 10054 remains unresolved/not reproduced. Native GUI, physical IME/DPI, real Codex/MCP/voice workloads are not newly verified. Packaging results are recorded separately after execution. No dependency, format migration, permission expansion, stdlib patch or forced global process termination.
