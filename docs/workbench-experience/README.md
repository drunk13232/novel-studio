# Writing Continuity / 写作连续性

Version: 2.24.4 Writing Continuity Preview.

## 从正文继续工作

正文工具栏新增“本章工作”：在现有可调侧栏查看当前章节的计划目标、待处理候选、待办、修订事项与已绑定出处。待办直接使用既有计划/记录服务；完成或新增后按本地事件刷新，不轮询。出处按钮核对真实原文后定位；计划不等于已发生事实，相关资料不会因打开侧栏自动进入 AI 上下文。

“本次写作参考”“AI 场景导演”和“AI 创作指挥台”仍使用同一可调分屏。资料审核后返回所选工具，不自动执行模型。专注模式隐藏侧栏，退出后恢复同章节会话中的表单。尚未保存的材料、事实审核仍有直接返回入口与未保存保护。

## 暂存候选，再决定是否采用

在既有选段 Diff 或修订台中修改候选和说明后，900ms 无新改动会尝试暂存，也可点击“暂存候选”。状态区明确区分正在暂存、尚未暂存、已暂存但未采用，以及原文过期。

- 暂存只更新当前项目的既有候选记录，不修改正文、Canon、State 或 Knowledge。
- 不同生成候选分别保留编辑和说明；选段 Diff 还保留作者明确勾选的变更片段。修订台的采用按钮仍表示采用该处完整候选，请核对预览范围。
- “关闭比较，保留候选”不会拒绝建议。保存尚未结束时，可继续编辑或选择“暂存并关闭”；明确放弃只丢弃未暂存部分。
- 重新打开“本章工作”的候选或原有候选记录，即可继续。应用重启后从同一项目、同一候选恢复；既有项目备份包含这些字段，恢复为新项目后继续隔离。
- 两窗口修改同一候选时，后提交者会显示冲突并保留当前文本。可以先下载本地候选副本，再关闭比较并明确放弃未暂存内容，重新打开服务器上保存的版本。不会自动覆盖另一窗口内容。
- 原文变化后保留候选草稿，但禁止直接采用旧来源。下载副本不等于可绕过版本校验。
- 真正采用仍需作者点击既有确认按钮并通过原文版本、原选区与 Final 保护。正式稿采用后产生既有修订稿；不自动提交设定或人物事实。

候选最多沿用既有三个生成方向和 32,000 字符编辑边界；说明最多 4,000 字符。普通历史正文版本继续使用原有恢复流程，不会被当成待审核候选。

## 请求前检查

现有 AI 模型控件增加折叠的“本次请求预检”：计划模型、接收主机/协议、思考强度、当前功能提供的来源范围和参数覆写。Codex 登录默认模型在未发现具体 ID 时如实标为未知；已配置自定义模型不在目录中时，要求重新选择，不悄悄回退到 Codex。

此处是计划配置，实际请求的模型、参数、用量仍以执行回执为准。控件不会发送正文或产生推理请求；来源检查、作者授权、费用提醒和原有路由继续执行。未提供的来源数/字符数显示未知，字符数不当作精确 Token。

## English

Current Chapter combines existing planned goals, pending candidates, to-dos, revision tasks and linked evidence in the writing dock. Existing notebook records and scoped local events keep it synchronized. Opening a dock does not expand AI context or commit plans as facts.

Manual candidate text and notes save locally after 900ms of inactivity or with Save candidate draft. Each generated variant is independent. Selection Diff preserves explicitly selected hunks; the Revision Desk's adoption action still applies the full displayed candidate. Reopen the same candidate after closing or restarting. Existing project backup/restore includes this optional metadata.

Closing preserves a proposal; rejection and adoption remain explicit. Unsaved edits receive keep/save/discard protection. Conflicting windows cannot overwrite a newer saved draft: retain/download local edits, deliberately close without saving, and reopen the stored version. Stale manuscript sources retain draft recovery but block adoption. Existing Final revisions and project boundaries remain authoritative.

Planned request checks reuse existing model controls: concrete model, destination host/protocol, supported reasoning effort and caller-provided source scope. Unknown values remain unknown. Opening the controls does not call a model. Actual execution receipts and existing source/cost authorization remain authoritative.

## Verification boundaries

See [2.24.4 delivery evidence](DELIVERY-2.24.4.md). No new dependency, Agent, renderer or database migration. Windows native WebView2 interaction, physical Chinese IME and real remote AI are separate acceptance gates; local tests do not prove them. Large Monaco/PDF/timeline chunks remain lazily loaded and still trigger Vite size notices. No measured startup or memory improvement is claimed.
