# 模型控制技术记录

基线：Novel Studio 2.16.0。交付补丁：2.16.1 Advanced AI Controls Preview。

现有依赖保持：openai-codex 0.160.1、Codex CLI 0.160.0、openai Python SDK 3.28.0、React / Vite / i18next。没有新增依赖或修改 SDK 源码。

## 官方接口核实

- [Codex App Server](https://developers.openai.com/codex/app-server)：通过官方 `model/list` 发现模型、默认与支持的 reasoning effort；`thread/start.model` 和 `turn/start.model / effort` 真实传参。本机安装包的 `Thread.turn` 暴露 model / effort；`ThreadStartParams` 没有独立的 `modelReasoningEffort` 字段，因此没有向它发送虚构字段。
- [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning)：Chat 与 Responses 使用不同推理字段，档位依模型不同。
- [Responses create](https://developers.openai.com/api/reference/python/resources/responses/methods/create)：输出上限和 API 参数依据当前 SDK 映射。
- [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)：官方端点 Chat 的 thinking 在受控 extra_body 中；使用支持的精确档位，不将 medium 等默默映射为另一等级。禁用思考模式会忽略的采样项。Top P 等特殊行为通过确认的参数范围/条件配置，未知时禁用。

模型名不用于推断能力。自定义兼容服务的能力依据用户配置；未知字段为 UNKNOWN。未引入 Gemini / Anthropic 原生 SDK，也不宣称普通兼容服务具有原生参数能力。

## 接线

`app/ai/controls.py`：类型验证、优先级、只读来源选择、确定性预算裁剪、来源回执。

`app/ai/center.py`：复用原 `ai-settings.json`，作用域配置、目录、收藏、预设、实际回传窗口缓存、现有费用/远端授权。

`app/ai/parameters.py`：协议级白名单映射；拒绝未知和无效参数。没有任意脚本或 JSON 透传。

原 Codex / LLM Adapter：冻结每轮配置，实际 model / effort、流式结果、Usage、取消前缀和回执；不修改全局登录或配置。

原 Creation、WorldStudio、Assistant：从其已有授权数据生成逐来源载荷。Writer-safe 服务继续在预算选择前过滤知识；预算器没有读取文件或新增授权的能力。

前端复用 Radix Dialog、原模型选择器、i18next 与 mutation queue。很短的偏好队列在 AI 请求入队前冲刷，避免刚调整参数马上发送仍用旧设置。没有第二套模块加载或调度系统。

## 已知协议边界

目录不是 entitlement。上下文窗口仅展示官方返回或当前请求明确报告的值，标明来源；输出上限缺失则未知。

Codex 服务端实际输入 Token 包含应用无法完整观察的基础上下文。本地预算限制应用发送的可管理资料；不伪装为完整上游计费 Token 硬限制。基础指令精简仅适用于已存在的纯文本胶囊，普通文件工作流与 MCP 权限边界保持。

本轮保留单次生成不自动重试、不自动续写、不跨服务商回退。不能确认的能力停用；本地协议 Mock 不作为真实远端能力证据。
