# 2.20 技术与安全选择

## 复用

原 Action Registry / TaskManager / FastAPI / React / WebView2 / Pydantic / Context Builder；原 Codex Python SDK 0.160.1、CLI 0.160.0、MCP Python SDK 2.3.0。无新 Agent 框架、数据库、常驻网关或桌面容器。

Codex 实际模型与 effort 由既有模型目录和 RequestControls 校验。受限助手继续只启用 Novel Studio 自身 stdio MCP；Shell、其他 MCP、插件、全局文件写入、网络工具不可用。普通检查任务继续使用既有只读适配器。复用当前登录，不改用户全局配置。

官方参考：[Codex SDK](https://developers.openai.com/codex/sdk)、[Codex MCP](https://developers.openai.com/codex/mcp)。运行中追加指令使用实际已安装 SDK `turn_steer`；不兼容或已结束的任务明确拒绝，不能自动重启收费请求。

## 真正 Python 隔离

用 **Wasmtime 49.0.0** 加 **CPython 3.14.7 WASI**。WASM 中运行完整 CPython，标准输入输出只桥接已注册动作；不在 FastAPI 内执行不可信 Python。WASI capability 仅只读挂载 CPython 标准库和公开 SDK，不继承主机环境、不挂载作品/用户目录、不提供 sockets 或 Shell。

Wasmtime 为 Bytecode Alliance 的成熟运行时，Python 包许可证 **Apache-2.0 WITH LLVM-exception**。CPython 使用 PSF 及随附历史声明。本版 CPython WASI 二进制来自 Python 维护者 Brett Cannon 的构建仓库，**不是 python.org 官方 Windows Python 安装包**。[来源与完整性](https://github.com/brettcannon/cpython-wasi-build/releases/tag/v3.14.7) 由 `RUNTIME-LOCK.json` 锁定，归档 SHA-256 为 `2e064d3fb8172471d39d741348efa722349c40b96301f69968dff714999c584b`；逐文件校验，重新下载不关闭 TLS。

官方技术参考：[Wasmtime Python API](https://bytecodealliance.github.io/wasmtime-py/)、[CPython WASI 构建](https://github.com/python/cpython/tree/main/Tools/wasm)。实际 49.0.0 `WasiConfig.preopen_dir(..., fs_mutable=False)` 与最新版示例不同，按已安装 API 使用。

独立 owned 子进程，Windows Job Object（已安装 pywin32 312 / PSF）限制1进程、1GiB宿主进程内存，关闭即回收；WASM 线性内存256MiB、fuel与epoch上限、10–180秒壁钟、输出128000字符、最多100次 RPC，且仍受作者当前 Action 步数限制。默认步数12。没有给 Python 主机权限，也不以 import 黑名单冒充沙箱。

不是通用系统自动化终端；WASI 不含任意本机扩展和外部 pip。外部作者自建 Python 是另外的信任边界，由主动短期授权接入 loopback Action API。

## 审批与并发

Python 计划保持 Level 2；AI 文本任务、结果交接保持 Level 3。没有自动预批准字段。审批固定参数和来源版本，不授权模型后续自由规划。子动作逐项检查原权限与变更租约；排队调度本身不持有小说写锁，以免 UI 回执和子任务相互等待。

取消使未执行动作失效，收回当前 Python 进程及其 owned 子任务；不关闭无关 Codex。只读编排与 AI 子任务复用 TaskManager 的兼容调度选项，领域写入仍经过现有锁、冲突检查与 Proposal 流程。

## 分发

Windows 包携带 WASI/Wasmtime 与许可，用户不需单独装 Python。Developer ZIP 保留 SDK、固定哈希安装脚本和文档，排除大型运行目录、私有数据与 Git 历史。私人芳乃/蕾姆 Live2D、语音和聊天不进入公开候选。项目最终开源许可证仍由用户决定。
