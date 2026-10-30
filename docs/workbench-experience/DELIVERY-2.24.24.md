# Novel Studio 2.24.24 — Bounded Save Verification Preview

本地 Preview / PARTIAL。公开版和 Public Allowlist 仍为 2.24.23，旧发行包保留。本轮不自动公开、接入快捷方式或改变真实数据目录。

## 实际问题与修复

旧版的核对 GET 没有独立时限；隔离实测中，等不到响应头和收到半段 JSON 后停住均在 12 秒后仍占用保存状态。

新逻辑仅对保存回执不明后的那一次只读核对设置 10 秒时限，覆盖 fetch 和 response.json。复用既有 api(signal)、AbortController 和 timer finally 清理，不使用只丢弃 Promise 却保留请求的伪超时。原始正文 PUT 不绑定此取消信号，也不自动重发。未知结果仍走既有编辑/导航/退出/恢复保护。正常核对及时完成仍可确认保存。

中文和英文提示明确这次读取的时限、超时后仍不确定的保存状态，以及继续编辑、保留恢复副本或稍后比较的操作。没有新依赖、框架、Agent、数据格式、迁移或权限。

## 实测

18 个独立 headless 场景：6 个时限场景（响应头停顿、JSON 体停顿、正常慢响应、等待期间新输入、迟到响应、自动保存防重放），另有 12 个既有保存回执/格式回归。使用真实本地写入与磁盘字节核对、明确故障 HTTP 端点；不调用模型，不使用真实作品。

5 个超时状态切换实测 10.039～10.121 秒，正常慢响应约 1.34 秒确认。浏览器 fetch 或 response.json 真实抛出 AbortError，只有一条主 PUT 和一条核对 GET。迟到响应不能清除未知状态；超时不重发自动保存。作者明确手动恢复和重新载入可用，自动恢复设置仍关闭；仅当副本与磁盘不同才显示恢复提示。

首次测试驱动的页脚选择器、同文本恢复提示预期、服务端即时断开假设均修正并保留原失败记录；这些不是额外通过场景，也没有改产品来迎合测试。

## 边界

浏览器停止读取不保证后台服务立即停止处理。10 秒限制不覆盖原始保存 PUT、其他维护写入、系统休眠/冻结或主线程无法调度定时器的时段。不能把未知结果说成保存失败或成功。本轮未新增原生窗口、实体中文输入法、DPI、语音、真实云端 AI 和长期性能验收。旧的隔离服务退出异常及候选外 config.toml 漂移仍未归因，不回滚全局配置。

## Mature implementation references

[WHATWG Fetch: aborting fetch and response body](https://fetch.spec.whatwg.org/#abort-fetch), [DOM AbortController](https://dom.spec.whatwg.org/#interface-abortcontroller). Existing local GET signal support is reused; no retry gateway or broad mutation cancellation is introduced.

## English

A 10-second deadline bounds only the post-save verification read, including response-body consumption. Submitted mutations are never cancelled or replayed. Unknown outcomes retain edits and existing author protections. Eighteen isolated headless scenarios passed; native GUI/physical IME/DPI/voice/cloud-AI acceptance remains unverified. Browser cancellation is not a guarantee that server-side work has stopped.
