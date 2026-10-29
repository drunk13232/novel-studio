# 2.24.8 MCP Writing Workflow Preview

本版复用现有创作指挥台、Writer、TaskManager、Writer Context、确认对象与 Monaco Diff，没有新增规划模型、Agent 框架、数据库或依赖。

## 使用

1. 打开当前章节，在正文工具中检查并确认写作上下文。候选历史的“继续这份候选”会将未采用稿作为明确的有限参考；它不是 Canon 或人物已知事实。
2. 为软件助手选择明确模型并授权本作品正文范围。`get_approved_writing_context` 只发现已经确认且仍有效的参考包，不能替作者审批。
3. `start_creative_writing` 只创建原指挥台任务，必须人工确认固定目标、模型参数和最多四段场景要求。它不是整书自动写作授权。
4. `read_creative_writing` 返回实际状态、已收到正文数量、错误和有限片段。`stop_creative_writing` 保留前缀；`resume_creative_writing` 重新确认后仅继续未完成步骤，不自行增加调用上限。
助手结果及已保存的本地历史还提供“查看创作任务”，可直接重开原指挥台检查状态、停止或继续，不会创建第二个任务。计划摘要受 1500 字符限制，完整作者要求单独保留，不因摘要而截断。

5. 任务结束后 `stage_creative_writing` 保存原有 Diff 候选。助手结果和本地历史中的“查看正文候选”可进入原比较窗口；采用正文仍是独立作者操作。
6. `stage_chapter_draft` 支持逐段新候选和唯一原文锚点插入，旧版保留。作者已经编辑、处理、改动来源版本或来源为局部补丁时，不会冒充整章继续。

纯文本 Writer 在 SDK 初始化前关闭本就不使用的插件等集成；实际内存分配错误会说明草稿仍保留，并提示手动恢复。未将该改动宣称为已测量的内存降幅。MCP 进度只返回真实任务状态和脱敏的 SDK 阶段字段，不暴露本机路径或完整内部提示词。

## 边界

- 远端模型只获得明确确认的范围；模型、Provider 和权限不因 MCP 入口而扩大。没有任意 Shell、SQL、主机文件或密钥读取权限。
- 当前候选和较近候选有明确的文本上限与截取标识；未来章节、其他作品、已处理候选、变动基线和被排除的必要参考会被拒绝。无法容纳时失败，不悄悄放宽预算。
- 章节写作会创建候选，不自动改 Final、Canon、State、Knowledge 或提交剧情事实。软件不保证模型按目标长度写足，也不把模型 Turn 完成当作整书完成。
- 原创长篇试写与失败回执保存在开发私有目录，不在 Windows / Developer ZIP。正式作品没有作为试写材料发送。
- 开发中已实际使用 Codex 登录与本地 stdio MCP，已运行本地存储/协议检查和浏览器 Diff 交互。最终数据与验证范围见随交付生成的 `MCP-WRITING-VERIFICATION.json`。
- 原生 Windows 窗口、实体中文输入法、DPI 与完整长篇文学质量没有在本轮全面验收；保持 Preview / PARTIAL。
- 旧版与用户原有快捷方式保留；本次不自动发布 GitHub、不提交 Git，不把私人角色与试写内容打入公开候选。

## Developer notes

Actions are schema validated and pass through the existing Session permissions. Start/resume remain Level 3, staging Level 2, explicit read/stop Level 1. Approval is not a successful execution receipt. Candidate-reference fingerprints include the source version; an empty optional list keeps earlier context fingerprints compatible. See `web/backend/tests/test_mcp_chapter_drafts.py` for local protocol and safety regressions. These tests are not remote-model or native-desktop acceptance.
