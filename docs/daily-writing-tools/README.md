# Daily Writing Tools / 日常写作工具 — 2.21.8 Preview

This release extends the existing editor, focus mode, revision service, local
save-delta statistics and clue lifecycle. It adds no agent, alternative editor,
second clue database, remote telemetry or new frontend dependency.

## 专注与休息 / Focus and breaks

在正文界面的「专注与休息」打开小面板；也可从创作工具或设置的「写作与编辑」进入。
原有专注模式继续隐藏多余面板；番茄钟、打字机和音效可分别使用。

- 番茄钟：专注 1–180 分钟，休息 1–60 分钟。手动开始、暂停、继续或提前结束。
  到时仅应用内提示，不强制保存、切屏、锁键盘或开始下一轮。
- 打字机：真实输入或删除后将当前行居中，使用现有 CodeMirror 呈现扩展，
  不重新创建编辑器或撤销历史。输入法组合阶段不抢滚动，完成后再更新。
- 打字音效：默认关闭。音量、静音即时生效，离线 WAV 在首次实际使用时加载；
  至多两个音频实例，失败不影响文字。无网络声音资源。
- 设置为本机全局偏好；重开保留开关与时长，但不自动继续上次倒计时。
  同一运行中切换书架、项目和新建页面保留当前计时，统计仍属于开始时的作品。
- 小结来自现有正文保存事件：开始/结束时锁定事件边界，只计算区间内净汉字差。
  删除为负，重复保存为零；手动、AI 接受、恢复及未知来源分别显示。
  未保存草稿及旧版外部文件估算不计入。事件不可核实时明确不提供小结。
  这是作者主动设定的专注时段，不是被推算出来的实际写作时长。

Open **Focus and breaks** in the manuscript view, in writing tools, or in writing
settings. Timer, typewriter scrolling and sound are independent. Preferences
are global to this local client. The timer survives in-app navigation but does
not auto-resume after restarting the app. The saved-net summary is bound to the
original project and existing verified event boundaries, never unsaved drafts.

## 久坐与护眼 / Local wellbeing reminders

默认全部关闭。作者主动启用后，仅在应用可见、有焦点、正文编辑器可见，并在
最近 60 秒内发生实际输入/删除时，累计「应用前台活跃时长」。最小化、切走、
非编辑页面和长时间空闲不计入。这不是写作时长，亦不是健康或专注程度评估。

久坐可选 45/60/90 分钟，护眼每累计 20 分钟提示看约 6 米外至少 20 秒。
每个周期至多提醒一次，可确认已休息并重开周期，或「本次不再提醒」。
只用应用内提示，不调用系统通知，不暂停保存或 AI。所有设置、当日累计和
周期计算均在客户端；无后端、AI、网络上报。全部关闭时没有后台计时间隔。
清除客户端本地存储会重置这些偏好与累计值。

All wellbeing controls are opt-in and local. Counting requires a visible,
focused app with the manuscript editor open and real input within 60 seconds.
This is foreground active use, not writing time. Blur/minimization pauses
counting. Notices are non-blocking and deduplicated per cycle. No network or
OS notification is used. Clearing local client storage resets the preferences.

## 跨章节查找替换 / Cross-chapter replacement

从现有创作工具的「全文替换」进入。选择全书、当前卷或勾选稳定章节 ID；
每章使用当前正文版本，不把同一章的所有历史草稿一起替换。

支持纯文本、区分大小写、全字和正则，后两项可组合；全字为 Unicode
字母/数字/下划线边界，不是中文分词。正则支持数字或具名分组引用及换行等
有限转义，不执行脚本。空搜索和零宽匹配会被拒绝，错误或超时有中文/英文提示。

匹配显示章节与上下文；可以逐条替换/跳过、勾选替换或全部替换。真正写入前
必须确认数量；人物、地点和设定名及重叠匹配会分组提醒、默认跳过，可明确
选择仅查设定专名或同意处理专名。只改选定正文，不改设定集本身。

服务冻结预览、范围与修订版本，执行时重新校验。沿用正文保存与历史检查点；
Final 只产生新的手动修订副本。支持本次批量整体撤销，后来被编辑的文件会阻止
撤销，避免覆盖新稿；撤销也抵消对应净增，防止统计虚增。失败尽力补偿；若
外部文件同时发生变化，保留回执和 PRE_REPLACE 历史供人工恢复，不擅自覆盖。
AI Action 目录没有新增未确认全局替换权限。

查找限制明确显示：单正文沿用 2 MiB 编辑上限，全次至多 64 MiB、1,000 个文件、
2,000 处匹配、每章正则 150 ms，查找约 8 秒边界；不完整覆盖醒目标注，结果
按页显示。超大章节跳过并给原因；可缩小范围处理剩余章节。合集需分别打开各作品，
不会越过项目边界搜索。崩溃中断的批次不自动重放，按历史回执恢复。

Search a book, volume or selected chapters. Each match has context, explicit
replace/skip and count confirmation. Proper names are separately highlighted
and skipped by default. Safe saves, frozen revisions, pre-change checkpoints
and whole-batch undo are reused; protected Final files receive revision copies.
An intervening edit blocks stale operations. Search caps are disclosed, not
presented as complete coverage. See docs/writing-tools/global-replacement.md.

## 伏笔与线索看板 / Clue board

入口在创作工具的「伏笔与线索看板」，知识中心的现有伏笔标签也使用同一组件。
只投影已有 State、章节计划、文学内核 clue/clue_event 和知识证据锚点。
计划不是正文事实；明确区分来源证据状态和作者手动整理状态。

可筛选/搜索、查看埋设与计划回收章节、标记计划中/已埋设/部分回收/已回收、
关联回收章节和备注。手动整理仅写 metadata/studio/clue-board.json，带版本校验
与历史，不写正文、Canon、State、Knowledge 或正式时间线。

逾期阈值默认 20，可设 1–1,000；按全书稳定章节顺序跨卷计算，恰好 N 章
不逾期，超过 N 才提醒。进度使用实际正文/已提交章节，不使用未来计划。
证据可精确定位时跳转；来源改动或定位不可信则仅打开章节并提示，不制造锚点。
同号章节歧义、超大来源或缺失信息明确保留未知。空作品显示友好空状态。

The board reuses existing clues, plans, literary lifecycle events and source
anchors. Author tracking is metadata, not Canon. Overdue means strictly more
than N chapters after evidenced planting, using real progress across volumes.
Future plans cannot become planting/recovery facts. Stale anchors open the
chapter with a warning rather than an invented exact location.

## Integration and verification boundaries

- New UI strings: Simplified Chinese and English. Other languages use the
  existing fallback; no fabricated translation-coverage claim.
- Existing theme tokens, reduced-motion and RTL-aware spacing are retained.
- New backend dependency: regex 2026.9.29, bounded Unicode matching with timeouts;
  Apache-2.0 AND CNRI-Python notices included. No new frontend dependency.
- Automated checks use isolated projects, real local HTTP handlers and real
  React/CodeMirror in jsdom. Test clock/audio/transport adapters are labeled.
- At the author's request no computer, browser GUI or native desktop interaction
  is performed in this round. Real audio, physical IME, native minimize/restore
  and visual/DPI acceptance remain UNVERIFIED. Build/ZIP success is not GUI PASS.
- No real novel, Canon, State, Knowledge, credentials, private character asset or
  user history is part of the curated source or Windows archive.

## 2.21.6 使用细化 / Refinements

### 专注与提醒

到时标记和待查看提醒在面板关闭后仍可见。准备计时期间可取消准备而保留
其他开关；迟到响应不会自行开始。暂停/结束恰好发生在倒计时过零时也会
完成且只完成一次小结。Escape 返回入口，不抢正文焦点。

前台活动区显示暂停原因及下次提醒所需的剩余活跃时间。两类提醒独立记忆，
开启统计不会擅自开启提醒；本次静默可恢复。恢复默认不清空今日累计。
小结使用分:秒，明确：计时排除暂停，字数仍是起止事件之间全部保存的净差，
含暂停期间保存；不据此推算写作速度。

Expiry and pending reminders remain discoverable when the panel is closed.
Preparation cancellation is separate from disabling editor aids. Late replies
do not start the timer. Expiry is settled once even if pause/end precedes a tick.
Activity pauses and remaining active cycles are explicit. Reminder choices are
independent; session mute is reversible, and resetting preferences keeps today's
active total. The saved-net window includes paused-period saves and is not speed.

### 替换与正文跳转

分页加载和单处处理保留已加载结果及手动选择，不再强制回第一页。支持
按待处理/已替换/已跳过等状态查看、重新加入跳过项、查看批次条件与每章数量。
相同内容不算实际修改；待核对专名不冒充作者已跳过。专名保护在同一次冻结
预览中保守保留，并识别替换后新形成的专名；变更后需重新同意处理专名。

结果显示位置并可跳转真实范围，来源版本改变时提示重新搜索。删除后的
零长范围只在版本和上下文能验证时定位光标，不运行空字符串搜索。修改
其他章节不会重载当前编辑器或产生虚假的未保存冲突。

只读预览可停止等待；后台已开始的受限搜索可能继续结束并留下无害预览。
同项目在途搜索受限，不自动无限重试。搜索和只读专注小结不占正文写入队列，
本机会话校验仍存在；真正保存、应用替换及撤销继续串行，不提供含糊的中途取消。

Loaded results and manual selection survive per-match actions. Pending proper
names, skipped matches and unchanged text have distinct counts. Search is bounded
and cancellable as a preview; an already-started backend scan may finish safely.
Previews do not block the manuscript mutation queue. Actual writes retain token,
revision and confirmation gates. Navigation uses real UTF-16 spans and revisions;
unrelated editor tabs are not reloaded.

### 伏笔看板

按涉及卷、状态、逾期和未保存草稿筛选，按名称、埋设顺序或逾期程度排序。
逾期卡解释起止章节及阈值，计划窗口单独说明未定位、顺序不成立或超出计划，
不把计划错误当成正文事实错误。提醒参数折叠收纳，筛选条件按项目保留。

多条未保存追踪和备注保存在当前看板层，不会因搜索/筛选隐藏卡片而丢失。
刷新冲突保留输入并提示来源变化；慢回执不覆盖新输入。源线索被移除时保留
可复制的遗留草稿，允许显式丢弃。恢复来源状态仅清人工状态覆盖，保留备注
和关联章节，不改来源、Canon 或 State。

Filters and ordering are project-scoped. Unsubmitted multi-card drafts survive
search/filter changes and refresh conflicts. Orphaned drafts remain copyable and
explicitly dismissible. Resetting an author status override preserves notes and
chapter association; underlying evidence and story facts are never changed.


## 2.21.7 直接操控 / Direct controls

### 写作条与专注

正文上方直接提供开始、暂停、继续、结束，以及打字机、静音和原有专注布局开关。
番茄钟到时后可直接开始休息，不必打开长面板。低频时长、编辑体验和提醒设置各自折叠。
鼠标点击编辑辅助开关不会默认抢走正文焦点，键盘仍可访问。

提醒卡可就地选择“已休息”或“稍后”。稍后只推迟当前提示，累积新的 5 分钟前台
活跃使用后再出现；切后台、离开编辑器或空闲不推进，不重置正常提醒周期。
仍可关闭全部提醒，保留默认不打扰。

The writing strip exposes timer, layout, typewriter and mute controls directly.
Expired timers offer an explicit break action. Low-frequency settings collapse
independently. Snoozing a local notice waits for five additional foreground
active minutes; background time is excluded and the regular cycle is retained.

### 查找、出处与返回

写作条可直接打开查找替换、伏笔看板。Ctrl+Shift+H 只打开替换界面，
Ctrl+Enter 在替换面板中只查找，任何替换仍须独立确认；输入法组合与确认框不触发。

从替换匹配、伏笔或知识证据打开正文后，可点击“返回…”或 Alt+← 回到来源工具。
返回只绑定当前作品及当前正文，切换章节不继承别的来源；有未保存修改时仍走原有保护。
专注布局隐藏普通工具链接，只保留有效来源返回入口，可手动收起提示。

替换可一键只查当前章、按编号/标题筛选、选择当前筛选章节或清空。隐藏的章节勾选
不因筛选被悄悄丢弃。返回后恢复输入、分页及勾选，先向服务端重新核对正文版本、
专名和范围；过期或无法确认时仅保留输入并要求重新查找。

临时替换视图只保留在当前进程内，最多 5 部作品、2 小时，仅含预览 ID、控件和不透明
条目 ID，不缓存命中片段或完整正文；不恢复专名授权或确认。不在重启后自动重放。

Direct source-return links retain the existing unsaved-change guard and bind to
the exact project and file. Replacement inputs, loaded pages and selections can
recover within a bounded in-process cache, after server source revalidation.
No manuscript snippets, permission confirmation or automatic write replay are
cached. Closing/reloading the app, expiry or eviction requires a new search.

### 伏笔批量管理

可勾选多个线索并批量修改作者追踪状态、关联/清除回收章，或恢复来源状态。
多卡片独立草稿可一次预览差异并确认保存；若所选项存在未保存输入，不允许直接批量覆盖。

一次最多 200 项。服务先校验全部对象、章节范围和 etag，再生成一次检查点并执行一次
原子元数据写入；任一项无效则整批不写。重复或过期确认被拒绝，冲突时输入保留，
可关闭确认卡、刷新并重新核对。仅修改作者追踪，计划、正文事实与 Canon/State 不变。

Bulk clue edits reuse the existing board overlay. One confirmation previews all
changes; all targets validate before one snapshot and one atomic metadata save.
Up to 200 items are accepted per batch, with no silent splitting or partial
success. Unsaved card drafts and source facts remain separate.


### 码字看板的编辑与日期定位

目标、日记及在途保存接入已有离页保护；有未保存输入时不会静默离开。各自提供保存、
重置及当前状态。查看别的日期时可直接跳回尚未保存的日记，支持指定日期和回到今日。
保存只更新本次提交的基线，不覆盖请求期间继续输入的新内容；失败保留草稿。
数据仍只来自本作品的正文保存事件，不增添计时口径、后台轮询或 AI 上下文。

Dashboard goal and journal forms use the existing unsaved-change guard, with
independent reset/save state and draft-date shortcuts. Date navigation includes
today and a specific day. A successful response acknowledges only its submitted
snapshot; newer input remains unsaved and protected. Metrics semantics and local
save-event refreshes are unchanged.


## 2.21.8 便捷性收尾 / Final usability pass

码字看板、替换和伏笔页顶部有统一导航，可返回原章、切换工具、打开专注面板或查看说明。
跨页继续保留未保存保护，使用说明集中解释五项工具的口径和快捷键。

正文有不超过 300 字符的选区时，“查找选中文字”或 Ctrl+Shift+H 会一次性预填纯文本查找。
章节能唯一定位时默认只查该章，否则明确提示全书范围供核对。不自动搜索/替换，不恢复旧
确认或专名许可；晚到的响应不能覆盖新输入，返回原结果不重放。

结果可按章节和关键词筛选，但只改变已加载结果的显示，不改变冻结搜索范围。
隐藏勾选明确计数，可“只勾选可见待处理项”；“全部替换”仍指整次冻结预览，确认卡会再次说明。

热力图可直达所选日期日记，配速无目标时可直接打开全书目标。日记草稿预览标明未保存。
目标/日记表单支持 Ctrl+S、Ctrl+Enter 保存当前表单，保留 HTML 校验、输入法和在途保存保护；
普通回车仍可换行。伏笔可“保存所选草稿”，明确预览最多 200 项，未选输入保留，不自动拆批。

专注面板右上角 X 可关闭并恢复可用入口焦点。小结失败仅在起止事件都已冻结时提供手动重试，
固定原作品和范围；边界缺失时明确不能准确恢复，不重取较晚结束范围，不伪造零字数。
异常久坐间隔回退 60 分钟，不产生零除错误。

A shared toolbar switches daily tools, returns to the manuscript and opens a
bilingual guide. Explicit short selections prefill literal search once, without
running or applying it. Loaded-result filters never change the frozen scope;
hidden selections and whole-preview replacement are clearly labeled.
Dashboard links focus the journal or book target; form shortcuts retain numeric,
composition and in-flight guards. Selected clue drafts use bounded explicit
confirmation. Focus summaries retry only frozen project/event boundaries.

Release provenance: the original 2.21.7 developer archive was accidentally
overwritten by this pass's baseline script and is unavailable. The misplaced
hash record was quarantined outside releases. Earlier runnable EXE/Windows ZIPs
and author works are unchanged. See FINAL-ROUND-REPORT.md for details.
