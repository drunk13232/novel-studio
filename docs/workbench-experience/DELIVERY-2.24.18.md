# Candidate Open Reliability — 2.24.18 Local Preview

## 简体中文

历史候选按钮与现有外部候选入口复用同一个只读加载函数。最后一次通过安全检查的读取请求才可应用结果；取消或过时响应不会覆盖较新的候选，也不会留下旧请求错误。

- 点击历史候选时显示“正在打开候选”，可取消这次读取；取消不取消生成任务或已经提交的写入。
- 读取失败会显示本次错误，可再次点击原候选明确重试。
- 请求返回时重新检查当前输入、暂存、任务、作品与章节。等待期间新增的未保存编辑不会被响应覆盖；请先暂存或通过关闭确认明确放弃，再重试打开。
- 关闭比较、切换版本、开始新任务和离开章节作用域会取消或失效旧的候选读取。
- 已处理候选、原文过期、版本核对、上轮的本地副本保护与作者明确采用继续使用原有通道。

读取不是生成，也不是采用。候选加载不会自行写正文或 Canon。没有新增 Agent、依赖、存储格式、迁移或权限。

## English

History buttons and existing external candidate requests share one scoped, cancellable read function. Only the latest request that passes safety checks may apply its result. Obsolete successes or errors cannot overwrite a newer comparison.

Opening shows real read progress and can be cancelled. This cancels the read, not generation tasks or submitted writes. A genuine current failure is displayed and can be explicitly retried by clicking the candidate again. Before applying a response, live unsaved input, saves, tasks, project and chapter are checked again. Save or explicitly discard current input through the close confirmation before retrying a blocked handoff.

Closing, switching variants, starting a task or leaving the document invalidates pending reads. Existing read-only history, source revisions, etags, retained-copy guards and author adoption remain. Loading is neither generation nor adoption; manuscripts and Canon are not written by a read.

## Verification boundary

Actual headless browser tests use isolated public/synthetic projects and real local APIs. One background-handoff check invokes the existing history button DOM handler behind an open modal, then uses normal input; it is a controlled renderer integration check, not physical clicking or real MCP/Codex proof. Controlled late/error responses and fixed local MOCK generation are identified separately from AI capability. The initial-draft-read close guard already worked and is retained as a regression.

Package/source alignment, the executable worker and silent isolated install are separate gates. Native GUI, physical IME, system DPI, real speech, new remote AI and prolonged use remain UNVERIFIED. Recovery copies remain window-local. This version is local only; public GitHub remains 2.24.16 and shortcut changes are separate.
