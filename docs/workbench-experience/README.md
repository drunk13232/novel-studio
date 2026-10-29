# Writing Continuity / 写作连续性

Version: 2.24.7 Record Editing Preview.

## 编辑已有记录

已有待办、修订事项和灵感也支持保存中继续编辑。回执只确认本次提交；后续输入仍保留并标为未保存，下一次点击保存使用已确认的新版本。等待回执时不能关闭或离开，以免撤销到旧基线的意图被丢掉。所有字段与已确认版本一致时无需重复保存，可直接关闭；失败时编辑保留并显示原错误。

## 保存回执与新输入

保存回执只用于发起保存的同一作品、章节与加载会话；切章后的回执不再用当前章节内容生成旧章恢复副本。干净正文不重复保存。同一章节保存期间的新正文仍保留。待办、修订与灵感提交后只清空仍与提交快照一致的表单；等待期间继续输入的内容或改过的选项不会被旧回执清空。

正常检查同一候选版本后继续自动暂存；如果此前因为恢复、冲突或错误暂停，检查本身不会解除人工暂停。

## 从正文继续工作

正文工具栏新增“本章工作”：在现有可调侧栏查看当前章节的计划目标、待处理候选、待办、修订事项与已绑定出处。待办直接使用既有计划/记录服务；完成或新增后按本地事件刷新，不轮询。出处按钮核对真实原文后定位；计划不等于已发生事实，相关资料不会因打开侧栏自动进入 AI 上下文。

“本次写作参考”“AI 场景导演”和“AI 创作指挥台”仍使用同一可调分屏。资料审核后返回所选工具，不自动执行模型。专注模式隐藏侧栏，退出后恢复同章节会话中的表单。尚未保存的材料、事实审核仍有直接返回入口与未保存保护。

本章新待办和新修订输入在同章节会话内随页签、工具面板保留；徽标和直接返回入口可继续填写。切换章节或退出前仍需保存或明确清空。它们不是新的跨重启草稿存储。候选历史可从本章工作直接打开，已处理记录只读，不再显示“未采用”。

## 暂存候选，再决定是否采用

在既有选段 Diff 或修订台中修改候选和说明后，900ms 无新改动会尝试暂存，也可点击“暂存候选”。状态区明确区分正在暂存、尚未暂存、已暂存但未采用，以及原文过期。

- 暂存只更新当前项目的既有候选记录，不修改正文、Canon、State 或 Knowledge。
- 不同生成候选分别保留编辑和说明；选段 Diff 还保留作者明确勾选的变更片段。修订台的采用按钮仍表示采用该处完整候选，请核对预览范围。
- “关闭比较，保留候选”不会拒绝建议。保存尚未结束时，可继续编辑或选择“暂存并关闭”；明确放弃只丢弃未暂存部分。
- 重新打开“本章工作”的候选或原有候选记录，即可继续。应用重启后从同一项目、同一候选恢复；既有项目备份包含这些字段，恢复为新项目后继续隔离。
- 两窗口修改同一候选时，后提交者会显示冲突并保留当前文本。点击“检查已保存版本”可对比本地文本、已保存文本及说明；先下载需要保留的副本，再明确载入已保存版本。本比较窗口内可恢复刚才的本地编辑；恢复后自动暂存暂停，需作者点击“暂存候选”。关闭窗口或重启后不保留这个临时恢复副本。不会自动覆盖另一窗口内容。
- 原文变化后保留候选草稿，但禁止直接采用旧来源。下载副本不等于可绕过版本校验。
- 真正采用仍需作者点击既有确认按钮并通过原文版本、原选区与 Final 保护。正式稿采用后产生既有修订稿；不自动提交设定或人物事实。

候选最多沿用既有三个生成方向和 32,000 字符编辑边界；说明最多 4,000 字符。普通历史正文版本继续使用原有恢复流程，不会被当成待审核候选。

## 请求前检查

现有 AI 模型控件增加折叠的“本次请求预检”：计划模型、接收主机/协议、思考强度、当前功能提供的来源范围和参数覆写。Codex 登录默认模型在未发现具体 ID 时如实标为未知；已配置自定义模型不在目录中时，要求重新选择，不悄悄回退到 Codex。

此处是计划配置，实际请求的模型、参数、用量仍以执行回执为准。控件不会发送正文或产生推理请求；来源检查、作者授权、费用提醒和原有路由继续执行。未提供的来源数/字符数显示未知，字符数不当作精确 Token。

## English

Existing-record editors keep later typing while a submission is saving. The receipt becomes the new baseline; subsequent edits remain unsaved until the next explicit save. Pending saves protect close/leave and undo intent. Unchanged forms need no extra write.


Save receipts remain tied to the original project, chapter and load generation. A late receipt must not use another chapter’s content for recovery. A clean document is not saved again. Entry submissions clear text only if the current composer still matches the submitted snapshot; newer typing and field changes survive. Inspecting an unchanged candidate preserves normal autosave without clearing an earlier manual pause.


Current Chapter combines existing planned goals, pending candidates, to-dos, revision tasks and linked evidence in the writing dock. Existing notebook records and scoped local events keep it synchronized. Opening a dock does not expand AI context or commit plans as facts.

Current-chapter to-do/revision inputs and selected fields survive tab/dock switches within the same chapter session. Save or explicitly clear them before leaving; these unsaved forms are not a new persistent store. Open read-only candidate history directly from the dock.

Manual candidate text and notes save locally after 900ms of inactivity or with Save candidate draft. Each generated variant is independent. Selection Diff preserves explicitly selected hunks; the Revision Desk's adoption action still applies the full displayed candidate. Reopen the same candidate after closing or restarting. Existing project backup/restore includes this optional metadata.

Closing preserves a proposal; rejection and adoption remain explicit. Unsaved edits receive keep/save/discard protection. Conflicting windows cannot overwrite a newer saved draft: inspect local and stored text/notes, download any copies to keep, then explicitly load stored state. The previous local edit can be recovered within this comparison window. Recovery pauses autosave until explicit manual save; this temporary copy does not survive closing/restarting. Stale manuscript sources retain draft recovery but block adoption. Existing Final revisions and project boundaries remain authoritative.

Planned request checks reuse existing model controls: concrete model, destination host/protocol, supported reasoning effort and caller-provided source scope. Unknown values remain unknown. Opening the controls does not call a model. Actual execution receipts and existing source/cost authorization remain authoritative.

## Verification boundaries

See [2.24.7 delivery evidence](DELIVERY-2.24.7.md). No new dependency, Agent, renderer or database migration. Windows native WebView2 interaction, physical Chinese IME and real remote AI are separate acceptance gates; local tests do not prove them. Large Monaco/PDF/timeline chunks remain lazily loaded and still trigger Vite size notices. No measured startup or memory improvement is claimed.


## 2.24.8 · MCP 写作闭环

[本轮入口、使用方式与验证边界](DELIVERY-2.24.8.md)。复用已有 Writer、上下文确认与 Diff；未采用候选可明确选择为有限参考，历史记录可重开。模型回合结束不等于全书写足，仍显示实际生成与保存回执。


## 开发中：全书交付目标的回执保护（尚未发布）

等待保存回执期间，新输入的目标与作者说明会保留；回执只确认已提交的版本。选择/清除交付候选、手动刷新核对结果不会清掉无关的目标草稿。并发冲突后，可先刷新基线再明确保存，未保存输入保持可见。

等待交付修改回执时暂不能关闭指挥台；未保存目标与说明纳入既有离开保护。仅修改说明但尚未提交时，可以明确放弃本地编辑，保留最后核对到的已保存目标。输入标签与保存反馈提供简中/英文。

本地真实服务+无界面浏览器覆盖9项流程；保存失败分支使用明确注入的503。无真实模型调用，不代表Windows原生窗口/输入法验收。现有已发布2.24.9包、用户数据和快捷方式未更新。

### In development: book-target receipt protection (unreleased)

A receipt acknowledges only its submitted target/reason; newer edits stay local and visible. Candidate selection and explicit refresh preserve unrelated drafts. Conflict refresh adopts the current etag without silently retrying. Pending mutations protect closing; unsaved forms use the existing leave guard. Explicit local discard handles reason-only edits. Nine isolated real-service/headless-browser scenarios passed, including one clearly injected save error; no model or native-desktop acceptance is claimed. Published 2.24.9 artifacts remain unchanged.


## 2.24.10 — 工作台交接 / Workspace handoffs

查看流程时保留交付表单；真正离开时使用原保护。关闭后的迟到回执不会重新弹出界面，旧记录版本不能静默用于新请求。详见 [2.24.10](DELIVERY-2.24.10.md)。

Nested workflow viewing retains the delivery form; real exits use existing protection. Late receipts cannot reopen closed views, and unseen revisions cannot silently power new requests. See [2.24.10](DELIVERY-2.24.10.md).


## 未发布：作者接管与任务刷新 / Unreleased: author takeover and task refresh

“停止生成，作者接管”保留本地未保存的候选文字、目标、计划与补充要求，并在表单恢复可编辑后将焦点交回候选区。任务结束后的读取回执会重新检查本地输入；其他窗口改变了闲置记录时，接管不静默覆盖。停止、暂停、终止核对当前执行轮次，旧视图不能误取消新任务。保存候选仍不等于采用正文。

Author takeover retains unsaved candidate text, goals, plan fields and directions, and restores focus after editing is enabled. Terminal read receipts recheck local edits. Unseen idle revisions are rejected instead of silently replacing the form. Stop/pause/terminate verify the execution identity so a stale view cannot cancel a newer task. Saving remains candidate-only.

### Scoped development check

Run from the engine root with existing development dependencies and a built frontend. These helpers copy only the public demo template into an explicitly owned directory. They use real local services/TaskManager with a controlled executor; they do not run an AI model or access personal works. A running fixture can be stopped with Ctrl+C in its own terminal. Do not point the fixture at personal data.

```powershell
.\web\backend\.venv\Scripts\python.exe web/frontend/scripts/start-director-fixture.py --root desktop/build/director-ui-fixture --port 8917
```

In another terminal at the engine root:

```powershell
node web/frontend/scripts/check-director-takeover.mjs desktop/build/director-ui-fixture
node web/frontend/scripts/check-director-handoffs.mjs desktop/build/director-ui-fixture
node web/frontend/scripts/check-delivery-receipts.mjs desktop/build/director-ui-fixture
```

The checks mutate synthetic candidate metadata only. Delays and controlled completion are test inputs, not evidence of real Codex, native desktop or physical IME acceptance. Do not run the fixtures concurrently in the same directory.


## 2.24.11 本地 Preview：状态、报告与连接检查

较早发出的刷新晚到时不会覆盖已接收的新状态；已结束任务不会被旧快照退回执行中。定向复核报告跟随当前记录和报告 ID，读取失败可明确重读，不重新发起模型评审。手动编辑候选后旧报告保留为历史参考。连接探测独立于作者写入队列和数据锁；错误后可重试，更新的已验证连接结果不被旧失败覆盖。作者确认、真正写入的锁、来源和会话校验均保留。

In this local Preview, ordered reads retain newer task state, report receipts stay with their record/review ID, and explicit report retries are GET-only. Manual candidate edits label old reviews historical. Connection probes do not serialize author writes; failures release the checking state and preserve later verified connection evidence. Author confirmation, actual-write leases, origin and nonce guards remain intact.

Additional scoped checks, using the same owned public-demo fixture:

```powershell
node web/frontend/scripts/check-director-records.mjs desktop/build/director-ui-fixture
node web/frontend/scripts/check-probe-write.mjs desktop/build/director-ui-fixture
```

Probe comparison can use `--published-baseline` with the retained 2.24.10 package; that mode serves its immutable public frontend assets for the controlled queue test. This is not a remote-model latency benchmark. See [2.24.11 validation boundaries](DELIVERY-2.24.11.md).


## 2.24.12：候选报告有效性与证据定位

See [2.24.12 local validation boundaries](DELIVERY-2.24.12.md). Reproduce with a dedicated `desktop/build/<owned-directory>` public-demo fixture and `scripts/check-director-review-basis.mjs`; controlled model doubles and synthetic reports are not real-AI acceptance. Run focused `test_director_review_basis.py` with an isolated pytest `--basetemp` if the machine default cache is inaccessible. Never point fixture startup at user data. No native desktop input or publication is required.


## 2.24.13：选区坐标与采用格式

See [2.24.13 boundaries](DELIVERY-2.24.13.md). `check-textarea-coordinates.mjs` compares the shared mapping to real browser controls. `check-director-textarea.mjs` requires an owned public-demo fixture started with `--local-writer`; its responses are fixed MOCK text, never remote AI. `check-evaluation-selection.mjs` uses an owned `--mixed-source` fixture for local range preview only; optional `--baseline-22412` serves the retained package's immutable frontend assets in the test browser. All output roots must be dedicated children of `desktop/build`. Keep raw per-run JSON separately when chaining older helpers that share `after-report.json`.
