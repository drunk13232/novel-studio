# Novel Studio 2.24.20 — 选区任务与真实执行边界

本地 Selected-Text Task Safety Preview / PARTIAL。保留已发布 2.24.19 与旧版；本轮不自动发布、提交 Git 或更改快捷方式。

## 使用与变化

选中文字后，AI 工具显示真实的读取准备、等待本机队列、已发送等待回执。未发送时可取消准备。等待期间改变原文、选区、源版本、模型/文风或已确认参考范围，会停止旧准备，要求作者检查后明确重新发起。认证或远端告知的受控重试也在真正发送前重新核对。若回执无法读取，不声称没有任务，而是提示先查看已有任务/候选记录，避免重复提交。

软件助手和 Python 控制台继续使用同一 Action Registry。生成选区修订时，沿用当前 Session、操作令牌、项目、选区和固定修改要求，在真正创建任务前验证取消、过期、归属和重复提交。短期操作凭证不进入模型输入、候选文件或比较快照；旧手动调用不强制增加该字段，不改变已有候选格式。实际子任务接入既有归属和停止机制；接受请求后即使辅助历史写入失败，也保留真实任务回执并提示。

模型回合已结束但作者确认的执行仍然有效时继续允许操作；取消当前执行任务则会阻止迟到启动。准备超时与界面失败不再统一冒充作者拒绝。人工确认本身不使用新增的 20 秒准备计时。

## 实际证据与边界

已在独立演示数据复现旧的准备后源变更提交、界面回执超时后的迟到任务以及后台取消后前端未观察到停止的迟到提交。针对这些链路，实际 headless 浏览器操作、原有 LocalAction/作者确认、真实本机 HTTP 和 TaskManager 配合明确标记的固定 MOCK 推理适配器完成检查。Python 控制台路径运行真实 bounded CPython WASI 和正式 SDK Action，不把它说成真实云端 AI 或 Codex/MCP 推理验收。

31 条核心场景覆盖准备读取/队列、修改/取消/重试、模糊回执、受控认证/告知重试、助手与 Python 前端归属、后台/当前执行取消，以及接受后排队和真正运行时的停止。网络故障场景是受控本机响应，不是服务商成功证明。现有导航回归、最终构建、冻结来源/资源、EXE worker、隔离静默安装、ZIP 和保护哈希结果分别保存在本地交付回执；未完成的验证不得从本说明推断通过。

不进行本轮原生窗口、实体中文输入法、系统 DPI、语音、真实 Codex/MCP、第三方付费模型或长时压测。真正请求已发送时不能承诺退回上游费用；取消依赖实际任务回执与原适配器能力。窗口内恢复仍需明确保存/下载，不能替代持久备份。已有大 Vite chunk 提示保留。真实作品的 Final / Canon / State / Knowledge 不进入测试。

## English

Local Preview / PARTIAL. Selected-text preparation checks live source, revision, selection, model/style and approved context after reads and at actual queued dispatch. Unsent preparation can be cancelled. Unreadable receipts remain explicitly uncertain; inspect existing history before retrying. Existing assistant and Python frontend bridges use scoped abort signals plus an ephemeral operation proof, validated against the existing live Session before creating a task. The transient proof stays out of model prompts, candidate files and comparison snapshots. Accepted children reuse existing task ownership/cancellation; ancillary history failure cannot erase an actual task receipt.

The 31 core headless flows use genuine local UI/APIs/TaskManager with explicitly fixed MOCK inference. Python Control additionally runs real bounded CPython WASI and its typed SDK. This does not establish cloud AI, real Codex/MCP, native GUI, physical IME/DPI or voice acceptance. Queue-before-receipt and running-after-receipt stops are distinct checks; already dispatched work is never falsely described as never started. Packaging and protection evidence are separate local gates. No new dependency, Agent framework, database migration, automatic adoption or public release.
