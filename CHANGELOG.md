# Changelog / 更新记录

## 2.24.28 — Shutdown Admission Preview (2026-10-31)

Preview / PARTIAL. Stop admission for main/project/draft/known-reference managers before service waits, prevent queued work from starting after closure, continue other owners after stop/close errors, drain real runners and preserve failures. 64 unique targeted local checks, two real loopback save/shutdown cases and five final headless recovery cases passed. Final isolated service exit still logged WinError 10054 and the existing 30-second graceful-shutdown timeout; root cause remains unresolved. One initial browser non-success response was not status-recorded and did not recur on follow-up. Neither issue is claimed fixed.

Preview / PARTIAL。关闭服务前停止主、项目、草稿与已有文献任务入口；排队任务不会在关闭后启动。单个中断或关闭失败不再跳过其他任务/服务，等待真实 runner 并保留错误。64 项不同的相关本地检查、两项真实回环保存/关闭场景及五项最终 headless 恢复场景通过。最后隔离服务退出仍出现 WinError 10054 和 30 秒 graceful-shutdown 超时，根因未确认；另一次浏览器首轮非成功响应未记录状态码，后续未重现。未宣称这些问题已修复。

[Final verification / 最终复核](docs/workbench-experience/DELIVERY-2.24.28-PUBLICATION.md). Existing bundled delivery notes preserve the earlier build-time snapshot; this addendum corrects the subsequent exit observation.

## 2.24.27 — Recovery Integrity Preview (2026-10-31, local)

Local Preview / PARTIAL. Cleanup compares the actual recovery-copy revision and late receipts only clear still-owned caches. Confirmed manuscript saves finish waiting for cleanup after ten seconds with a retained warning. Rejected retries retain prior uncertainty; busy workspaces do not create fake disk conflicts. Old recovery actions are hidden during chapter reads and remain available after cancellation. 26 current isolated headless cases, 15 real local API tests and 56 simulated transport assertions passed; no AI calls. See [2.24.27 notes](docs/workbench-experience/DELIVERY-2.24.27.md). No publication or shortcut update.

本地 Preview / PARTIAL。恢复副本清理核对实际副本版本，迟到回执只处理自己仍拥有的缓存；正文已确认保存时，副本清理超过 10 秒会结束等待并保留明确提示。被拒绝的重试继续保护先前未确认状态，工作区忙碌不冒充新的磁盘版本冲突。章节读取期间收起旧恢复操作，取消后仍可检查并恢复。26 个本轮隔离 headless 场景、15 项真实本地 API 检查和 56 条模拟传输断言通过；没有 AI 调用。见 [2.24.27 说明](docs/workbench-experience/DELIVERY-2.24.27.md)。本轮不发布、不改快捷方式。

## 2.24.26 — Bounded Chapter Opening Preview (2026-10-30)

Local Preview / PARTIAL. Cancellable chapter/recovery reads use a 10-second header/body deadline, retain existing content on failure and never bypass recovery or replay saves. Workspace restore resolves its target first; two measured scenarios reduced four reads to two, without claiming a matching startup-speed improvement. Thirty-nine isolated headless cases passed, including unsaved text, undo/redo, cancellation with an enabled writing ritual, save/format and snapshot regressions. See [2.24.26 notes](docs/workbench-experience/DELIVERY-2.24.26.md). No publication or shortcut update.

本地 Preview / PARTIAL。章节正文和恢复副本读取可取消，10 秒时限覆盖响应头与正文；失败时保留原有内容，不跳过恢复检查，也不重放保存。恢复工作区先确定最终目标，两项实际对照由 4 次读取降为 2 次，不据此夸称启动时间减半。39 项隔离 headless 检查通过，包括未保存文字、撤销/重做、启用仪式后的取消、保存与格式回归。见 [2.24.26 说明](docs/workbench-experience/DELIVERY-2.24.26.md)。本轮未发布或更新快捷方式。

## 2.24.25 — Recovery Progress Preview (2026-10-30)

Local Preview / PARTIAL. Successful author reload of a changed revision after an uncertain save refreshes actual saved-event progress without creating events or word counts. Unconfirmed saves expose existing compare/reload controls; read-only snapshots support empty files, cancellation, explicit retry and a deadline. 28 isolated headless cases passed. See [2.24.25 notes](docs/workbench-experience/DELIVERY-2.24.25.md). Public release remains 2.24.23; no automatic publication or shortcut change.

本地 Preview / PARTIAL。保存结果不明后，作者成功重载不同磁盘版本时同步刷新真实码字进度；不补造字数或保存事件。未确认状态直接提供现有比较/重载入口，空磁盘文件可明确查看；比较读取支持关闭取消、失败重试和时限。28 个隔离 headless 场景通过。见 [2.24.25 说明](docs/workbench-experience/DELIVERY-2.24.25.md)。公开版仍为 2.24.23，未自动发布或更新快捷方式。

## 2.24.24 — Bounded Save Verification Preview (2026-10-30)

Local Preview / PARTIAL. Post-save read-only verification has a 10-second deadline covering headers and JSON body. Timeout stops the browser read, retains edits/unconfirmed state and never cancels or replays the submitted write. 18 isolated headless cases passed. See [2.24.24 notes](docs/workbench-experience/DELIVERY-2.24.24.md). Public release remains 2.24.23; no automatic publication or shortcut change.

本地 Preview / PARTIAL。保存回执不明后的只读核对设置 10 秒时限，覆盖响应头和 JSON 响应体；超时停止此次浏览器读取，保留编辑与未确认状态，不取消或重放已提交的正文写入。18 个隔离 headless 场景通过。见 [2.24.24 说明](docs/workbench-experience/DELIVERY-2.24.24.md)。当前公开版仍为 2.24.23；本轮未自动发布或更新快捷方式。

## 2.24.23 — Verified Save Feedback Preview (2026-10-30, local)

- Distinguish confirmed manuscript writes from recovery cleanup/update failures, preserving real saved counts and visible warnings.
- Validate save receipts; ambiguous failures use one read-only verification, never an automatic write replay. Accept only the exact requested version and format.
- Preserve newer input and recovery snapshots; unknown/conflicting saves stay protected through undo, navigation and safe exit.
- Allow explicitly chosen manual recovery for comparison while automatic recovery remains off.
- Statistics read-back handling invalidates existing views only; event format and honest net-count rules remain unchanged.
- 47 isolated headless-browser flows passed, including LF/CRLF/BOM, empty/mixed input, uncertainty/undo, and previous leave/exit regressions. Controlled faults and desktop doubles are labelled; native GUI, physical IME/DPI, voice and cloud AI not newly verified. No new dependency, migration or permission.

## 2.24.22 — Safe Exit Reliability Preview (2026-10-30, local)

- Give exit preparation a scoped owner; cancellation, newer content or scope changes cannot silently continue into the desktop exit boundary.
- Recheck actual saved/recovered input and preference completion. Show real phases, duplicate-submit protection, in-dialog errors and explicit retry.
- Keep the desktop-handoff state visible until native disposal; do not offer a false cancellation after dispatch.
- Guard native preparation, keep accepted closure idempotent and recheck owned tasks after exit backups. Restore retryability if the close worker cannot start.
- Preserve the existing reply-worker join before window disposal.
- 27 isolated headless-browser flows and 9 local launcher/readiness tests passed. Desktop boundaries/windows in those tests are controlled doubles; native GUI, physical IME/DPI, voice and real cloud AI are not newly verified. No new dependency or permission.

## 2.24.21 — Author Navigation Reliability Preview (2026-10-30, local)

- Fix cancelled Save-and-leave / Keep-recovery-and-leave navigation resuming after delayed write receipts.
- Revalidate intent ownership, live document/page/load and input after asynchronous preparation. Preserve current input when cancelled, superseded or changed.
- Show real pending-write state, prevent duplicate submissions and keep Continue editing / close / Escape available.
- Surface write failures inside the leave dialog; explicit retries clear earlier errors. Explain disabled recovery-only navigation.
- 31 unique isolated headless-browser flows passed; actual local save/recovery APIs and byte checks, no AI calls. Native GUI/physical IME/DPI remain unverified. No new dependencies, data format, migration or permissions.

## 2.24.20 — Selected-Text Task Safety Preview (2026-10-30, local)

- Validate live selected text, range, source revision, model/style and context at real dispatch, not only before asynchronous preparation.
- Add bounded preparation cancellation and truthful waiting/submitted/uncertain-receipt feedback, including queue and auth/privacy-retry boundaries.
- Reuse existing Session/token/project validation at candidate-task creation; reject cancelled, expired, mismatched and repeated operations.
- Reuse existing owned-child task cancellation for assistant/Python entry points. Never persist the transient origin in candidates or model prompts.
- Distinguish frontend failures from author refusals; current confirmed-execution cancellation remains authoritative after a completed planner turn.
- Preserve canonical data, source/adoption guards and legacy manual requests. No added dependencies, Agent framework or database migration. Local Preview / PARTIAL; no native GUI or real-provider claim.

## 2.24.19 — Assistant Navigation Safety Preview (2026-10-30)

- Recheck project, page, document load, newer navigation and unsaved input after delayed assistant-result lookups.
- Report actual file-read success/failure; superseded or failed reads cannot continue candidate/director display.
- Apply live guards to existing character, world entity, reference and report lookups.
- Clear result-button errors for an explicit retry; ignore errors from older request/scope owners.
- Preserve existing Actions, author approvals, source versions and recovery. Local Preview / PARTIAL, without automatic publication or native GUI/real-model acceptance claims.

## 2.24.18 — Candidate Open Reliability Preview (2026-10-30, local)

- Share a scoped candidate-read owner across history and existing external requests; cancel/ignore stale success and failure callbacks.
- Recheck live unsaved input and document scope before opening a response; keep existing save/adoption protections.
- Show read progress, cancellation and explicit retry; clear obsolete history-list state and abort its reads on scope changes.
- Preserve the existing safe initial-read close behavior and window-local recovery guards.
- No dependencies, storage migration, remote-model call or automatic publication. Native GUI/IME/DPI/speech, real cloud AI and long-duration use remain unverified.

## 2.24.17 — Candidate Recovery Protection Preview (2026-10-30, local)

- Retained genuinely unsaved local copies keep existing exit/navigation protection after a conflict reload, including handled candidate receipts.
- Export the retained local buffer separately from the current stored buffer; downloading does not imply project persistence.
- Require explicit recovery or discard before editing/saving/adopting/switching unresolved copies; keep handled candidates locked.
- Apply the same recovery controls and explicit close/switch discard to the existing Revision Desk.
- Reuse existing etags, storage and author-only adoption. No new dependencies, migrations, AI calls or automatic publication.
- Recovery remains window-local; crash persistence, native GUI, physical IME/DPI, real speech and new remote AI are not claimed.

## 2.24.16 — Candidate History Reliability Preview (2026-10-30, local)

- Reset transient notes and choices between distinct candidate generations and after closing a decided comparison.
- Expose saved author text/notes in read-only history without equating saved edits with actual adoption.
- Do not restore editable draft content into a stale read-only variant preview.
- Retain same-text diff readiness and existing independently saved variants.
- Reuse existing storage/permissions. No dependency, migration, remote-model call or automatic publication.
- Native GUI, physical IME/DPI, speech, real remote AI and long-duration use remain unverified.

## 2.24.15 — Candidate Session Reliability Preview (2026-10-30)

- Includes the local 2.24.14 candidate editing improvements below.
- Require exact candidate-session ownership before a completed save can continue a UI operation.
- Prevent cancelled variant switches and save-and-close actions from affecting a reopened comparison with matching IDs/text.
- Keep legitimately committed snapshots; isolate stale failures from a newer view.
- No dependency, data migration, permission expansion or new remote-model request.
- Local browser, domain and packaged-worker verification remain separate from native GUI/IME/DPI, speech and real remote AI.

## 2.24.14 — Candidate Editing Reliability Preview (2026-10-30, local)

- Preserve explicit hunk choices across newline representation changes, variant switching and later candidate editing.
- Retain consent by immutable original-line coverage; new/expanded or ambiguous merged changes stay unchecked.
- Separate live editor input from deliberate replacement props to prevent rapid input echoes from reverting characters/caret.
- Continue candidate/note editing during autosave; retain initial-read, incoming-conflict and actual-decision locks.
- Explicit save updates the existing active-variant marker even when text is unchanged; plain viewing remains read-only.
- Keep the existing draft schema, source guards, EOL/BOM and author adoption authority. No dependency, migration or new AI call.
- Native GUI, physical IME/DPI, voices, new remote AI and long-duration use remain unverified.

## 2.24.13 — Selection & Save Reliability Preview (2026-10-30)

- Map normalized textarea UTF-16 selections back to exact raw source positions; preserve source/candidate text and reject mismatched or unrepresentable ranges.
- Repair evidence navigation, retain-to-cursor, local rewrite and literary-scoring selection for CRLF/CR/mixed text.
- Preserve the original document EOL and UTF-8 BOM on explicit candidate adoption, keeping raw proposal history and the original byte snapshot.
- Initialize existing Diff readiness from the real editor, compare logical newlines consistently and preserve actual selected-hunk text.
- Recognize accepted candidates when only the editor newline representation differs; content or terminal-newline changes remain significant.
- Retain mixed-source write protection, revision conflicts and author-controlled Diff acceptance.
- No new dependency, data migration, background polling or remote inference; native GUI/IME/DPI and real-AI quality remain unverified.

## 2.24.12 — Review Evidence & Recovery Preview (2026-10-30, local)

- Apply historical-report marking at the existing guarded record write point for AI append, rewrite, cancellation retention, restart recovery and author-basis changes.
- Derive candidate report validity from existing hashes and project/path/version provenance; no project migration or report rewrite.
- Keep recoverable prose visible when optional saved reports are missing/corrupt.
- Display verified evidence only, with guarded UTF-16 selection into matching candidate text; distinguish repeated quotations and changed source versions.
- Accept owned terminal receipts after background record cleanup while rejecting events for another record or newer execution.
- Preserve existing save, Diff, project isolation and author-confirmation authorities. No new dependency or remote inference.
- Local Preview; native GUI, physical IME/DPI and new real-AI acceptance remain unverified.

## 2.24.11 — Task & Review Reliability Preview (2026-10-30, local)

- Preserve local text, goal, plan and directions on author takeover; restore input focus safely.
- Ignore obsolete record/report receipts and retain current task status.
- Add scoped saved-report loading/errors and GET-only retry; mark historical reviews clearly.
- Check execution identity before stop/pause/terminate.
- Keep read-only Codex health probes independent of author-write serialization and leases.
- Recover checking state after probe exceptions while retaining real error reporting.
- No dependency or data-format change; all writing remains candidate-only.
- Preview boundaries: controlled local checks are not native GUI, physical IME/DPI or real-AI acceptance.

## 2.24.10 — Director Save & Navigation Preview (2026-10-30)

- Preserve target drafts and focus while visiting nested workflows.
- Acknowledge submitted target values without discarding later typing; protect pending saves and local undo/close.
- Apply existing discard protection to context, world lab, Diff and Python handoffs.
- Suppress late UI handoffs after close while retaining valid staged proposals.
- Refuse stale record revisions before staging, review and rewrite.
- Add isolated real-service browser regression scripts; no new dependency or data migration.
- Retain Preview boundaries and all existing author/project protections.

## 2.24.9 — Writing Reliability Preview (2026-10-29)

- Use the installed SDK-paired Codex CLI by default, retaining explicit runtime overrides.
- Separate model/step completion, prose delivery, length goals, Diff staging and author acceptance.
- Retain partial prose and fixed pending steps across interruption/restart; review unknown timing before continuing.
- Add local input-budget preflight and author-selected whole-book delivery checks inside the existing Director.
- Strengthen optional scene interfaces, explicit step position and exact repeated-passage review pointers.
- Preserve current-draft versus historical candidate/review distinctions.
- All generated prose remains proposed; no writing statistics, manuscript or Canon commit is performed by these checks.
- Preview validation boundaries remain explicit; no native GUI, IME or literary-quality pass is inferred from build success.


## 2.24.8 — MCP Writing Workflow Preview (2026-10-29)

- Reuse existing Quick Writer, TaskManager, approved Writer Context, fixed confirmations and Diff through MCP; expose real status and bounded result reads.
- Preserve model-phase request budgets across tool results; distinguish pending approval from tool failure.
- Persist versioned chapter candidates, exact-anchor additions and safe history pointers; protect original manuscript and author-edited candidates.
- Explicit draft references remain non-Canon, freshness checked and budgeted; empty optional choices preserve prior approval fingerprints.
- Scoped real-AI drafting is private acceptance material. Native desktop and physical IME remain unverified for this iteration.

## 2.24.7 — Record Editing Preview (2026-10-29)

- Retain newer input in existing to-do, revision and inspiration editors when a previous save finishes.
- Rebase local deltas, tags and expected revision on the actual acknowledged record; prevent stale-version self-conflicts and false dirty metadata.
- Protect close/leave during pending edit saves, preserve undo intent, and skip redundant unchanged saves.
- Add Chinese/English pending/retained-edit guidance and a guarded local regression helper; no new dependency, Hook, backend API or data migration.
- Local candidate only; desktop shortcut preferences are separate local actions and are not automatically changed by this candidate.

## 2.24.6 — Save Integrity Preview (2026-10-29)

- Avoid redundant clean manuscript saves; fence delayed save and recovery callbacks to their captured document scope and generation.
- Clear submitted entry text only when the current composer still matches the submitted snapshot. Preserve edits and field choices made while a previous save is pending.
- Same-version candidate inspection preserves normal autosave while retaining an existing conflict/error/manual-recovery pause.
- Existing backend persistence, writer protection and author decisions remain unchanged; isolated delayed-receipt/failure checks are distinguished from real AI or native desktop acceptance.

## 2.24.5 — Writing Recovery Preview (2026-10-29)

- Retain current-chapter to-do/revision composers and selected fields when switching tabs or closing author tools, with direct return and existing unsaved navigation protection.
- Retry failed candidate reads and fence cancelled/late responses without authorizing stale adoption.
- Preview local/stored candidate conflicts before loading; keep a window-local recovery copy and pause automatic saving after local recovery until explicit author save.
- Show accepted/rejected history as read-only; disable hunk editing and remove false unsavable close prompts.
- Refresh Current Chapter immediately after explicit rejection through a project-scoped event.
- Keep short-window author-tool entry points clickable and allow dock actions to scroll clear of sticky headings and the floating assistant.
- Chinese/English copy and responsive comparison layout, no new dependency, API, Agent or data-format migration. Local delivery only; verification boundaries are version-specific.

## 2.24.4 — Writing Continuity Preview (2026-10-28)

- Save edited candidate text, revision notes and explicit hunk choices locally per generated variant; reopen from the existing selection history or Revision Desk.
- Reuse existing candidate records and Data Center backups, with scoped compare-and-swap protection and no database migration.
- Keep stale/conflicted edits available for recovery without adopting them into manuscripts; serialize auto/manual saves.
- Bring existing chapter goals, tasks, proposed revisions and bound evidence into the writing dock, with scoped event-driven refresh.
- Show planned model, receiving host/protocol, supported effort and caller source scope through existing AI controls; reject missing-model readiness and retain real execution receipts.
- Prevent the comparison editor shrinking to one line in smaller windows; fence late chapter candidate reads and disable adoption until the current Diff is computed.
- Local/backend/browser and package validation are reported separately from native Windows interaction and real remote AI; see the version-specific delivery note.

## 2.24.3 — Workbench Experience Preview (2026-10-28)

- Dock existing author tools in the resizable reference split; preserve manuscript height, scoped input, focus restoration and independent scrolling.
- Open the Director directly, with an explicit context-review return path and no automatic model execution.
- Save once through the existing etag/recovery channel before preparing tools; reject failed, switched or outdated source snapshots.
- Guard unaccepted revision text and notes; closing a comparison preserves proposals, while rejection remains explicit.
- Fence scoped revision reads, serialize author decisions and navigate only after the unsaved guard clears.
- Direct return links for unsaved material/fact review, Chinese/English copy, no dependency or data-format change. Preview verification boundaries are recorded separately from older releases.

## 2.24.2 — Flexible Director Preview (2026-10-28)

- Explicit single-step execution with independent supported model controls; no automatic following steps.
- Stable step identity, duplication/reordering and compatibility for older ID-less plans.
- Independent attempts retain the original; choose retained progress or an empty candidate.
- Return actual Python output to source-bound author-only notes; stale warnings and removal preserve Python history.
- Opt-in bounded capacity up to 8 plan steps and 16 call attempts; defaults remain 6 calls, 600 seconds, 16,000 candidate characters. No new dependency, permission or Agent.

## 2.24.1 — Director Console Preview (2026-10-28)

- Independent task-local planner/writer controls, actual model/context receipts and persisted step progress.
- Explicit fixed-candidate handoff to existing WASI Python Control: load, manually run, return and unlink.
- Search/filter chapter history, preserve unsaved edits, reject stale handoffs and export private task reports.
- No new dependency, Agent or data migration. Real remote AI and native desktop interaction remain unverified for this update.

## 2.24.0 Custom Workflows Preview · 2026-10-27

- Ordered, project-local world/chapter workflows reuse existing domain tasks; concrete per-step models, source controls, manual checkpoints and bounded retries.
- Versioned configuration-only JSON templates; frozen run snapshots, pending-step edits and actual domain result receipts.
- Interrupted writing retains its prefix; restart/backup recovery never replays model requests automatically. Existing author adoption, Writer isolation and Diff remain authoritative.
- Existing model control component supports non-persistent editing inside a template; no changes to global/provider preferences.
- Preview: designated step kinds only, no arbitrary code, unrestricted branches or automatic Canon/State adoption. Local fixtures and native/real-AI gates remain separate.

## 2.23.1 World-First Creation Preview · 2026-10-26

- New world-first entry reuses the existing creation wizard: direct editable world proposals, without character, plot or literary prerequisites.
- World-only context and model routing, explicit adoption and creation without placeholder cast or story facts.
- Existing world designer starts from one simple overview; advanced design and story workflows remain available.
- Preview: local checks and browser fixture-model tests are distinguished from real AI and native GUI acceptance.


## 2.23.0 · 2026-10-26 · Daily Reliability & Planning Preview

- Existing author todos/revision entries gain optional dates, manual progress and checklists, with calendar/backlog and chapter links; no migration or automatic execution.
- Read-only unfinished tasks and explicit entity-link impact previews use existing services.
- Frozen, one-use cache cleanup previews and a shared build/cleanup exclusion marker; no original data or release deletion.
- Actual task receipts, bounded reconnect, late-response guards, no image-service probe on storage view.
- Compatible DOMPurify/Zod patch overrides; actual verification and limits in docs/daily-reliability/DELIVERY.md.


Current application version: **2.24.0 Custom Workflows Preview**. All listed builds remain Preview/PARTIAL unless a version-specific report states a narrower verified gate.

The entries below are reconstructed from retained release version manifests and `desktop/version.json`. They describe declared implementation changes, not proof that all features passed runtime/AI acceptance. Repeated cumulative lines are deduplicated; 2.10.3 had multiple suffixed candidates, not invented new semantic versions. Historical dates are recorded as declared, without correcting unsupported history. See `docs/oss/CHANGELOG-SOURCES.json` for hashes and provenance.

## v2.22.2 — Narrative Insights Preview (2026-10-25)

- Narrative curves retain unaffected per-series caches and current-source author corrections, with explicit known/unknown coverage and protected unwritten plans.
- Simulated readers require source-verified summary and reaction evidence; unsupported claims are withheld before persistence and in read-only legacy views.
- Actual isolated profile/curve/history backup restore and production chart interaction samples; no added dependencies, real manuscript changes or automatic AI calls.

## v2.22.1 — Creative Workflow Reliability Preview (2026-10-25)

- Creative workflow reliability: conservative reader recovery from matching reports, explicit missing/unwritten coverage and fenced asynchronous comparison views.
- World maps: bounded undo/redo, exact buffered coordinates, draft downloads, conflict and unfinished-drawing protection, missing-location rebinding and on-demand original backgrounds.
- Print preview: per-request cancellation and fixed payload binding, immutable result hash checks, source-status refresh and explicit old-snapshot export consent.
- Writing rituals: conditional daily-goal updates and integrated unsaved input/close protection; annual charts reject inconsistent years and duplicate optional records, and sharing fits long text and totals.
- Chapter alternatives: explicit frozen interrupted-transaction rollback, immutable historical Diff, corrupt-record isolation and local download of unsaved alternatives; Final remains protected.
- Offline audio: recover active jobs, retry status without resynthesis, source-bound calibration estimates, streaming WAV hashes and no replacement of user-modified audio files.
- No new dependency, migration, remote-model auto-call, global Codex change or personal manuscript modification; old releases and desktop entry are retained.

## v2.22.0 — Creative Workflow Preview (2026-10-25)

- Project-local chapter tension/emotion signals, source-bound author corrections, multi-line comparison and configurable low-tension reminders; local signals are explicitly rough.
- Optional skippable writing rituals reuse project goals, focus controls and daily journal; annual reports reuse saved-event net deltas with source separation and local PNG sharing.
- Simulated reader personas reuse ReviewCenter, selected Provider, frozen range/model/budget and verified source quotations, without mixing literary scores or changing prose.
- Local world maps bind existing draft Bible locations, author-provided assets, routes, regions and child maps, with normal full-backup recovery.
- Immutable A5 / pocket PDF artifacts share preview and export bytes through installed offline Chromium and the existing chapter assembler; page rendering is lazy.
- Named chapter alternatives remain in revision history. Explicit editable-draft main-version switches support safe undo; protected Final only receives review candidates.
- Offline SAPI per-chapter WAV export supports explicit scope confirmation, cancellation, verified completed-file reuse and source-version checks.
- No new dependency, schema migration, remote service auto-call, global Codex change or real author-content modification. Native GUI and remote inference remain separately unverified.

## v2.21.8 — Daily Writing Tools Final Preview (2026-10-24)

- Shared daily-tool pages provide guarded manuscript return, direct switching and a bilingual contextual guide.
- Explicit short manuscript selections prefill a literal chapter-scoped search when uniquely located, never automatically searching or applying; consumed intents cannot replay or be overwritten by stale reads.
- Loaded replacement results support chapter and keyword display filters with explicit hidden selections and whole-preview confirmation semantics.
- Dashboard journal and book-target links reduce scrolling. Ctrl+S and Ctrl+Enter save only the current validated form, retaining IME and in-flight/new-input protection.
- Selected clue drafts can be saved as an explicitly reviewed subset; 201 pending drafts no longer require individual saves and hidden selections remain visible.
- Focus panels close explicitly with safe focus return; failed summaries retry only frozen project-bound event boundaries. Invalid sitting intervals fall back safely.
- No dependency, AI call, event-format change or data migration. See final report for native verification limits and a disclosed older developer-archive incident.

## v2.21.7 — Daily Writing Controls Preview (2026-10-24)

- Writing-strip controls start, pause, resume and end focus sessions directly; layout, typewriter and offline sound switches remain independent and preserve the editor.
- Local wellbeing notices support immediate rest acknowledgement and a five-active-minute snooze without advancing in the background or resetting the normal cycle.
- Project-bound return links and guarded shortcuts connect the manuscript, frozen replacement results, clue evidence and knowledge sources.
- Replacement controls select the current chapter or filtered chapter set; a bounded memory-only view cache restores inputs and selections after source navigation, subject to server revision revalidation.
- Clue tracking supports multi-select edits and one confirmed atomic save of independent drafts; all targets validate before a single metadata checkpoint and write.
- The writing dashboard protects unsaved goal and journal input through existing leave-page guards, with explicit reset and save feedback.
- No new dependency, AI call, event-format change or data migration. Previous versions and author content remain protected; native GUI/audio/physical-IME checks remain unverified.

## v2.21.6 — Daily Writing Tools Refined Preview (2026-10-24)

- Focus expiry now settles exactly once even when pause/end beats the next tick; preparation can be cancelled independently and late responses stay inert.
- Foreground reminder state, remaining active cycles, reversible session mute and default restoration make opt-in local reminders clearer without changing writing metrics.
- Cross-chapter replacement preserves pagination and selections, distinguishes unchanged/pending/skipped text, refreshes proper-name protection and exposes version-bound source locations.
- Only authenticated local search previews and read-only focus summaries bypass the manuscript mutation queue; actual writes remain serialized and cannot be mislabeled as cancelled.
- Editor refresh affects only the changed manuscript; deleted revision undo resolves within its own chapter, and zero-length source carets cannot trigger an empty-string search loop.
- Clue filters retain independent unsaved drafts, explain overdue and planned windows, and allow clearing author status overrides without changing source facts.
- No new dependency or data migration. Previous releases, user works and global Codex configuration remain protected. Native audio, physical IME and desktop visual acceptance remain unverified.

## v2.21.5 — Daily Writing Tools Preview (2026-10-24)

- Opt-in Pomodoro, typewriter scrolling and a tiny offline keyboard sound integrate with existing focus mode and preserve editor history.
- Focus summaries read project-bound existing save-event boundaries; manual, AI acceptance and restoration deltas stay separate.
- Client-only opt-in sitting and eye reminders count visible, focused editor activity after recent real input; no AI, network or system notifications.
- Cross-chapter author-confirmed replacement reuses frozen previews, revision checks, safe saves and whole-batch undo; proper names are grouped and protected.
- Clue board projects existing State, plans, literary clues and source anchors; editable author tracking never commits story facts.
- Simplified Chinese and English controls; no new frontend dependency. Bounded Unicode regex runtime includes its license notices.
- Preview: no desktop or browser GUI was operated in this round. Real audio, native minimization, physical IME and visual acceptance remain unverified.

## v2.21.4 — Model Control and MCP Preview (2026-10-24)

- Writing dashboard extends existing save-delta records with a 365-day heatmap, streaks, previous-week summary and 24-hour save-event distribution.
- Seven-calendar-day pace forecasting and daily, weekly, volume and book goal progress retain explicit net Chinese-character semantics.
- Manual writing, AI accepted text, restorations and unknown sources remain separate; legacy file-observation estimates are preserved but excluded.
- Read-only metadata progress feeds bookshelf today badges and an editor mini dashboard; successful save events refresh them without polling.
- A non-blocking daily goal notice is deduplicated per project and date; save refreshes preserve unfinished goal and journal input.
- Statistics reads no longer manufacture historical events or probe Pandoc and image libraries. Existing event format and all creative content remain unchanged.
- Simplified Chinese and English UI strings; other languages use the existing fallback. No new frontend or backend dependency.
- Preview: this delivery uses local API and in-memory component checks; no computer or desktop UI operation was performed at the author request.

## v2.21.3 — Model Control and MCP Preview (2026-10-24)

- Concrete Codex models can be saved as global, project and task routes; workflow and file tasks remain Codex-only.
- Unified assistant model picker with official on-demand catalog, real effort options and guarded parameter initialization.
- Codex MCP threads receive the explicit model and stop on a mismatched model; same-scope sessions reuse only identical permissions and context controls.
- Desktop startup probes the owned loopback HTTP service directly, independent of ambient URL handlers and proxy setup.
- The dynamically dispatched assistant MCP server is explicitly included in Windows binaries, preserving the real Codex-to-Action chain.
- Preserve the vendor CPython public CA rejection policy in Windows packages; TLS verification and distrust rules stay enabled.

## v2.21.2 — Art Refinement Preview (2026-10-21)

- Editorial bookshelf with grouped catalog search, readable book cards and full-ratio existing covers.
- Refined daily writing navigation, folio heading, tabs, reference and assistant surfaces using existing theme tokens.
- Existing themes, focus mode, editor, save and data protection retained; no new runtime dependencies or artwork.

## v2.21.1 — Plugin Hub Preview (2026-10-21)

- Refined settings layout with reachable small-window search, category scroll restoration and visible-field search targeting.
- Compact plugin cards and dedicated detail dialogs with scoped styles, contextual errors and in-flight operation feedback.
- Localized service cards, executable example downloads and clear empty/loading states; existing Action and WASI protections retained.

## v2.21.0 — Plugin Hub Preview (2026-10-21)

- Unified Plugins and Integrations entry with reviewed local packages, opt-in activation, non-sensitive configuration and recoverable uninstall.
- Versioned declarative commands and data resources reuse existing Actions; Python contributions reuse the bounded WASI worker and scoped TaskManager.
- Per-plugin Action allowlists, version and configuration checks are enforced in execution; disabling revokes pending confirmations and owned tasks.
- Working downloadable examples and JSON Schema, with existing AI/ComfyUI/Codex settings kept separate from credentials.

## v2.20.0 — Character Agents & Python Control Preview (2026-10-21)

- Desktop worker startup skips home, configuration and UI initialization; Python, logic and MCP use early dispatch.
- Idle external Python grants no longer lock the built-in console; running and pending actions retain serialization.
- Character assistants, Python SDK and Codex MCP reuse one typed Action Registry and existing domain services.
- On-demand Python Control uses genuine CPython WASI in a bounded owned subprocess, without host project mounts, network or shell.
- Real frontend receipts support chapter navigation, pinned references, layouts and actual editor state.
- Project/persona-scoped scripts, output history, AI task provenance and explicit read-only result handoffs.
- Existing Codex login, concrete models and supported effort/context controls; real task events, result reading, cancellation and supported live steering.
- Frozen author confirmations remain valid after a model or Python turn ends; scripts are never automatically replayed.
- Source and binary candidates exclude private manuscripts, credentials, conversation history and character assets.
- Preview: the action catalog covers designated workflows, not every application operation; new controls primarily support Chinese and English.

## v2.19.0 — Interaction & Creative Freedom Preview (2026-10-18)

- Closing the writing AI panel retains its current scoped task and input; actual request receipts remain separate from next-turn settings.
- Author-approved text results can be saved to the existing inspiration inbox with task provenance, without changing manuscript or Canon.
- Undo to the saved manuscript clears this session's superseded recovery copy without discarding unreviewed recovery found on open.
- Reference split changes retain the existing editor, scene instructions and AI controls instead of remounting the writing surface.
- Per-novel layout presets and a saved personal layout reuse existing bounded preferences and resizable panels.
- Object context menus and the shared command palette open chapters, characters and references beside the current manuscript.
- Inspiration, chapter tasks and revision items can be edited, searched, batch organized, undone and restored from the recycle bin with revision guards.
- Tab movement, target-aware close-others and guarded reopen preserve pinned tabs and unsaved-content protection.

## v2.18.1 — Soft UI & Visual Refinement Preview (2026-10-18)

- Role-based rounded controls, quiet cards, refined shadows and consistent focus/hover states across all sixteen existing themes.
- Bookshelf, chapter navigation, tabs, assistant, model controls, world entries, evidence cards and floating surfaces receive a coherent desktop finish.
- Literary scoring history is expandable without permanently narrowing the active form; existing records and comparisons are preserved.
- Theme search accepts surrounding whitespace; author-defined radius and zero-motion settings remain authoritative.
- One original editable book-and-botanical SVG is loaded by actual shelf and empty-state components. No new dependency or business-data migration.

## v2.18.0 — Autonomous Product & Art Evolution Preview (2026-10-18)

- Writing-first navigation and a searchable shared creative-tool catalog retain every existing guarded workflow.
- The bookshelf continues the advertised chapter from the first screen, with compact cover-and-metadata cards and clear empty search results.
- Project-specific themes and palette choices reuse bounded application workspace preferences, separate from global appearance and author data.
- A slim manuscript header makes more text visible; dossier cards, selected chapters and tool dialogs receive theme-aware finishing.
- An original editable book-signet SVG joins existing on-demand artwork; no new dependency, AI framework or database migration.
- Optional untranslated workbench namespaces no longer block a valid UI language switch; core-resource failures retain the current usable language.

## v2.17.0 — Visual Renaissance & Theme Expansion Preview (2026-10-18)

- Sixteen preserved and extended themes with distinct illustration, typography, bookbinding and component treatments.
- Live theme atelier with search, collections, favorites, cancellable previews and previous-theme recovery.
- Bounded per-theme personalization, contrast checks and safe JSON import/export through existing preferences.
- Six original on-demand WebP illustrations and eleven editable SVG resources; private character assets remain isolated.
- Shared visual refinement for the writing desk, AI/evidence, worldbuilding, literary evaluation, timelines and settings.
- No new dependency, database migration, AI call or author-content modification is required to use themes.

## v2.16.2 — Daily Experience Preview (2026-10-17)

- A focused writing toolbar keeps every existing AI tool in an on-demand shared dialog.
- Continue writing opens the chapter advertised on the bookshelf, retaining other workspace tabs.
- Incomplete numeric context edits no longer submit invalid intermediate settings.
- Codex model discovery is available beside the model selector; reasoning labels show readable names and actual values.
- Collapsed idle read-aloud controls stop polling; active playback remains controllable.

## v2.16.1 — Advanced AI Controls Preview (2026-10-17)

- Exact model IDs and on-demand Codex model/effort metadata with per-request provenance.
- Verified generation parameter mapping, scoped preferences and reusable control presets.
- Bounded selected-source context previews in creation, world design and software assistant, with history pins and explicit trimming.
- Portable visible discussion, retained cancelled prefixes and concurrent author editing without stale AI overwrites.
- Preview limitations: native Gemini/Claude protocols and provider-internal Codex context remain outside complete application control.

## v2.16.0 — World Model & Memory Preview (2026-10-17)

- World rule cards reuse Bible entities and versioned templates, with hard/soft distinction, scope, conditions, exceptions and explicit precedence.
- Format-specific citations reuse the existing bounded reference parser and notes; original hashes and exact locations detect stale evidence.
- Author-confirmed story-time periods and existing FTS provide traceable world memory without current-state backfill or another projection engine.
- Rule mappings create version-bound drafts in the existing World Logic Lab; Z3, SymPy/Pint, scenarios and reports retain source provenance.
- Existing Writer approval uses released, time-applicable summaries; counterfactual branches and unknown historical states cannot enter as facts.

## v2.15.0 — Long-Form Narrative Intelligence Preview (2026-10-17)

- Worldbuilding Studio extends existing Bible categories, entities, relations, revisions and Writer Context
- Composable country, city and organization templates with typed field metadata, safe JSON interchange and preserved per-entry template snapshots
- Author world blueprint, encyclopedia hierarchy, selected evidence provenance and explicit template upgrade preview
- Bounded, resumable per-template AI design batches reuse Codex / API routing, TaskManager and the existing worldbuilding method
- Editable per-item proposals, explicit formal adoption, stable IDs, guarded existing-entry revisions and relation confirmation
- Writer uses only explicitly selected, author-released summaries scoped to public or approved POVs; raw encyclopedia secrets remain excluded
- Existing World Logic Lab and counterfactuals remain the only solver workspace; no new database, Agent framework or dependencies
- Simplified Chinese and English UI additions with existing fallback and logical RTL layouts
- Preview: encyclopedia-level automated histories, map authoring and broad remote-provider validation remain outside the implemented scope

## v2.14.0 — Long-Form Narrative Intelligence Preview (2026-10-17)

- Temporal narrative views reuse committed Ledger and Proposed inverse patches, explicit end-state time anchors and original source revisions
- Existing FTS retrieves within disclosure boundaries before ranking; no new database or embedding service
- AI chief editor extends existing evaluation reading DAG with bounded full-text groups, evidence-bearing observations, priorities and optional revision tradeoffs
- Existing ReviewCenter, revision todos, guarded Diff, project presets and batch checkpoints remain authoritative
- Cross-chapter style observations use existing local statistics; author interpretations and planned clue nodes never become Canon

## v2.13.0 — AI Writing Quality Preview (2026-10-17)

- Writer context prioritizes current intent, knowledge and confirmed style before distant reference prose
- Explicit boundaries distinguish established facts, scene-level creative freedom and author-confirmed consequential settings
- Existing Creative Director delivers compact selected-method applications to the actual writer, including Quick mode without another planning call
- Editable scene stop conditions and deferred outcomes, exact execution receipts and source-bound task brief inspection
- Low-certainty past-reference pointers and existing evidence-based candidate reviews; no automatic manuscript or Canon edits
- Repeatable original-fixture A/B writing experiments reuse the existing Director, statistics and literary evaluator with anonymous labels and retained failures
- Targeted scaled-window Director layout refinement; existing visual system, themes, writing and private companions retained

## v2.12.2 — Visual Design Upgrade Preview (2026-10-17)

- Concept-led literary study visual system with semantic controls, editable original vectors and independent generated artwork
- Refined bookshelf, chapter navigation, paper workspace, tabs, reference columns and shared evidence/entity cards
- Real-data literary score medallion, dimension bars and chapter results chart; no fabricated sample ratings
- Unified existing literary, world, matrix, timeline, assistant and settings presentation without changing author data
- Existing themes, private character resources, focus layout, save, revisions and knowledge isolation retained

## v2.12.1 — Literary Evaluation Preview (2026-10-16)

- Opt-in literary evaluation inside the existing ReviewCenter: exact passage, chapter, arbitrary chapters, ranges and complete available manuscripts
- Editable versioned eight-dimension rubrics with evidence-bound scores and deterministic applicable-weight normalization
- Bounded full-text reading, chapter/range synthesis, per-model checkpoints and explicit batch resume without fabricated full-book coverage
- Actual source quotations, stale-version warnings, separate model judgments and qualified historical A/B comparison
- Existing author revision todos and Writer-safe Diff remain the only manuscript revision path

## v2.12.0 — Literary Core Preview (2026-10-16)

- Literary Core: evidence-bound style, ideas, clues and narrative logic over existing author notes and reviews
- Editable character stances, actions, costs and alternative literary readings without ideology or quality scores
- Clue lifecycle separates plans from current manuscript observations; multiple payoffs retain exact source evidence
- Author-selected positive literary directions enter existing scoped Writer Context and guarded candidate Diff
- Existing style profiles support manuscript provenance and optional character or scene scope
- Formal narrative dependencies reuse World Logic Lab, version locking and NetworkX rather than AI claims

## v2.11.2 — Core Reliability Preview (2026-10-16)

- Stable chapter-scoped State proposal pagination with existing semantic commit gates
- Author-only version-bound manual acceptance with immutable mathematical reports
- Project-scoped assistant conversations and persona preferences in existing backup/restore
- Protocol-aware Provider smoke tests with explicit diagnostics and no automatic paid retries

## v2.11.1 — Creative Workflow Reliability Preview (2026-10-16)

- Selectable commander and actual execution Provider with explicit privacy and budget checks
- Long-form stream checkpoints, exact retained-prefix intervention and manual takeover
- World and behavior hypotheses return through existing materials and refreshed Writer approval
- Semantic Final, Memory Keeper, reviewed State Diff and explicitly confirmed local State Commit
- Committed item Writer views included in the next chapter context; historical and future boundaries retained

## v2.11 — Professional Writing Preview (2026-10-16)

- Release directory and version metadata retained; no distinct incremental change is asserted from cumulative metadata alone.

## v2.10.3 — Creative Workspace Preview (2026-10-14 / 2026-10-15 / 2026-10-16)

- Optional private Live2D runtime with real model import, motion/expression mappings and focus-mode cleanup
- Character/project-separated companion conversations through existing Roleplay and AI providers
- Local SAPI5 speech with actual viseme events and controlled application action proposals
- AI writing: bounded source-visible Writer context with explicit safety review, exclusions, pins and story-time/POV receipts
- Scene director: distinct editable strategies and author-confirmed beat-to-paragraph candidates
- Selection co-writing: surroundings, task-specific models, multiple versions and existing guarded partial Diff acceptance
- Evidence-bound chapter fact candidates with per-item epistemic review and gated existing Memory Keeper handoff
- Writing quality: opt-in offline punctuation, selected-model Chinese proofreading and evidence-bound chapter/cross-chapter checks in the existing ReviewCenter
- Exact versioned evidence, protected project terms and scoped ignore decisions; no automatic literary rewrites or Canon writes
- Minimal per-issue candidates reuse Monaco Diff, history checkpoints and protected Final revision drafts
- Existing FTS now refreshes only changed manuscript files; related excerpts are bounded and source-verified
- Daily-use fixes: persisted/searchable assistant discussion isolated by persona, project and model; bounded history replay
- Exact single UI commands use the existing local Action permissions and receipts instead of cloud inference
- Offline Windows SAPI dictation, low-confidence manual review, optional reply TTS and real viseme synchronization
- Voice stop, microphone ownership, stale-response protection and orderly speech shutdown
- Numeric input hotfix: stable wizard focus, buffered saves, stale-receipt protection and editable bounded number fields
- Optional embodied interface to the existing software assistant and controlled Action Registry
- Persona/project-separated model preferences, permissions and in-memory discussion; no new agent permissions
- True task-driven avatar feedback, explicit confirmation, selected-text review and candidate-only revisions
- Character docks inside assistant panel; hidden/focus mode releases rendering; no autonomous AI calls
- Existing SAPI voices and actual viseme synchronization; optional browser dictation with explicit privacy notice
- Author workflow enhancement: per-document context choices persist in project preferences; every restored packet needs fresh Writer safety approval
- Reusable project-local writing actions save mode, positive instructions and candidate directions without changing provider or permissions
- Nearby co-writing history reopens existing candidates without regeneration; handled or stale versions are read-only and live acceptance retains guarded Diff
- Selected entity lookup uses existing exact names, aliases and indexes to open the pinned reference split; ambiguous names require author choice
- Context retrieval excludes current/future chapters, deduplicates earlier paths and reuses the existing HTTP mutation lease
- Standalone Codex SDK processes discard inherited desktop routing paths; credentials and global configuration remain unchanged
- AI Creative Director: real Codex plans with bounded existing professional methods; explicit chosen Provider writes candidate prose
- Author intervention pauses scheduling or interrupts current requests, retains streamed text, edits plans and rewrites only selected passages
- Project-scoped resumable checkpoints, exact source revisions, call/time/API budget limits and existing guarded Monaco Diff approval
- Focused candidate review reuses the existing evidence-bound ReviewCenter; reports never become unfiltered Writer input
- Daily reliability: actual-request Codex authentication without redundant account routing preflight; stage-specific monotonic diagnostics and truthful connection-probe errors
- The 48 new author-workflow UI strings are translated for all 26 locales, with existing fallback and native-review limitations retained
- Creative workspace: chapter excerpts enter the existing behavior and logic labs; author-selected hypotheses return through existing notes and fresh Writer safety approval
- Scene option handoff binds actual scene ID, option and manuscript revision to the existing director; literary review remains beside the current editor
- Optional visual references reuse ComfyUI workflows; trusted Blender templates use explicit CLI operations and standalone scene briefs without scripts or manuscript writes
- Transparent draggable Live2D companion over the workspace; click-to-chat, persistent position, size, click-through and focus-mode cleanup without reserving a writing column
- Configured companion visible beside the bookshelf and writing workspace; persistent hide/show, compact chat, and on-demand settings

## v2.10.2 — Preview (2026-10-13)

- Unified visual polish across the writing desk, bookshelf, settings and existing tools
- Optional Yoshino-inspired and Rem-inspired companion skins with original motifs and local replaceable resource slots

## v2.10.1 — Preview (2026-10-13)

- Personal daily-writing optimization: bounded ledger/display caches, scoped planning reads, passive image queue, on-demand AI status and simplified navigation
- CodeMirror native Undo/Redo restored for unchanged recent documents within the running app; existing backups, conflict checks and protected content retained

## v2.10.0 — Preview (2026-10-13)

- Goal-Driven Creative Preview: per-task AI routing, isolated actor dialogue, conditional behavior scenarios, evidence-bound literary review and existing Diff integration
- Existing World Logic Lab, user data authorities and 26-locale fallback retained. New UI has Simplified Chinese and English translations.

## Earlier recorded history / 此前记录

## v2.8.5 Preview

优化书架摘要、人物列表、重复搜索和关系数据读取。修复关系图并行边布局异常、候选弹窗关闭、助手失败状态和书架加载时的空状态。备份恢复先验证索引，失败不留下半恢复项目。改善存储故障的中文提示。

已进行有限桌面、真实 MCP 和隔离备份恢复验证；真实拼音 IME、系统 DPI、长期压力测试仍不完整。状态 PARTIAL。

## 开源准备（V2.9 任务，应用版本仍为 v2.8.5）

准备显式源码 Allowlist、脱敏公开文档、社区模板、第三方许可声明和 Windows 候选说明。保留原发行包与本地 Git 状态。不新增软件功能，不公开仓库，不提交申请。

## 此前开发记录

V2.8.x 完善受控软件助手、MCP、分段计时、确认持久化、主题与字体。更早阶段增加作者工作台、知识关联、修订、文献与成书中心。原始逐轮记录包含私人数据与机器路径，不作为公开历史打包；这些记录不能替代公开 Git 贡献记录。

## OSS release finalization — 2026-10-12

- 软件仍为 v2.8.5 Preview；没有新功能版本或公开 Release。
- 锁文件中官方不存在的 tslib 2.8.2 修正为兼容的官方 2.8.1；使用原完整性机制，不忽略 TLS。
- 为生产后端挂载已有 /pdf 资源，修复中文 CMap 404。
- 保留官方 PDF 字体及许可，补充完整 SFD 源码与来源/字形比对说明。
- 从公开 ZIP 在独立环境安装 Python / npm 依赖并构建，不复用开发 node_modules 或虚拟环境。
- Apache/NOTICE/版权信息继续为待确认候选，不自动生效，不修改用户作品权利。

## 2.9.1 International Preview

- 26 supported UI locale choices, offline namespace loading, persistence and explicit writing/AI language separation.
- Localized core interface, native startup prompts, structured errors, RTL and script-aware system-font fallback.
- Live CodeMirror label updates preserve editor state; existing World Logic Lab, Codex MCP and manual writing are retained.
- Translation completeness and browser/native verification remain separately documented. This is a Preview, not a full language certification or public release.

## 2.9.2 World Logic Lab Enhanced Preview — 2026-10-13

- Extend the existing versioned experiment system; retain schema_version 1.0 with optional compatible chronology, scheduling, evidence and condition fields.
- Add three challenge strengths, reviewed parameter counterexamples, rebuttal mode, explicit source mappings, and author-confirmed inspiration/PENDING choices.
- Separate strict chronology from causal feedback and associations; keep uncertain times and fictional calendar coordinates explicit.
- Add OR-Tools CP-SAT for finite resource scheduling with real witnesses and bounded optimization; preserve Z3/NetworkX/SymPy/Pint.
- Add three runnable templates and Baseline/A/B comparison without changing frozen criteria or story facts.
- Fix a masked worker exception and bound native numerical threads while retaining the existing 512 MiB worker budget.
- Focused deterministic, isolated service, real Codex and release-WebView checks passed. Full historical regressions, native IME/system DPI and all-language human review remain outside this preview verification.
