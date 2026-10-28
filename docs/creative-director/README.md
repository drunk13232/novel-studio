# AI Creative Director — 2.24.2 Flexible Director Preview

This extends the existing editor, WritingAssist, TaskManager, Providers and ReviewCenter. It is not a new agent runtime or a second data authority.

## Daily workflow

1. Open a saved chapter, then **本次写作参考**. Select the necessary POV, earlier excerpts and approved references. Review and explicitly approve the Writer-safe packet.
2. Open **AI 创作指挥台** in the writing toolbar. Choose the execution model already configured in **设置 → AI 接口**. A configured DeepSeek model uses the existing OpenAI-compatible adapter; no model ID is hardcoded.
3. Choose Quick (one direct text request), Director (one Codex scene brief), or Deep (at most four editable steps). Select up to four installed professional methods when creating the record.
4. In Director/Deep, request a Codex plan. Review the task brief, real method application, unknowns and optional model recommendation. Model recommendations require author selection and saving; no provider is silently changed. Mark important plot decisions approved only after checking them.
5. Confirm the brief to generate candidate prose. The current model, stage, stream and known usage remain visible. No file is changed by generation.
6. Pause stops subsequent scheduling; the current request can finish. Stop interrupts the current owned request and retains received text. Terminate closes the whole record but preserves its draft. Upstream costs may already have been incurred.
7. New author directions can interrupt and save in one operation. Save edited requirements before continuing. A new request uses the latest directions and retained draft; an interrupted upstream stream is never claimed to resume losslessly.
8. Select a passage in the candidate, enter replacement instructions and use local rewrite. Unselected text is retained. Authors can edit the candidate directly at any time and save it after interruption.
9. Optional focused Codex review uses the existing literary ReviewCenter and actual text evidence, scoped to the fixed candidate and approved Writer view. It does not constitute a full Canon audit. Checker reports are not automatically sent back to the Writer.
10. **进入现有 Diff 比较** opens the original Monaco comparison. Accept selected changes, retain manual edits, or reject. Final protection and version checks remain enforced; accepting a protected Final creates a separate revision draft under the existing policy.

## Existing methods and evidence

Eight method entries reference existing Context Builder, character/continuity/style/editor Skills and NovelForge scene, literary renderer and quality-inspector resources. Only selected method bodies are sent to the director. If installed, trusted Screenwriting scene/dialogue references augment the corresponding methods. Records retain delivered character counts, source names and SHA-256 receipts. An ordinary API executor receives the resulting bounded task brief and approved Writer context, not filesystem or Skill execution rights. External scripts are not executed and plugin caches are not bundled.

## Safety, recovery and cost

Records live in `metadata/studio/director/` inside the active project and enter existing project backups. They contain private goals, candidate prose and intervention history, so they are not public templates. No new database, persistent background worker, credentials or global Codex configuration is introduced.

Every request checks the source revision and fresh Writer view. Historical records remain viewable, but stale source/context cannot be used to overwrite newer text. Reopening does not restart old upstream work. In-flight partial text is checkpointed about four times per second; an abrupt process failure can lose the last unflushed fraction of a second, not be described as lossless recovery.

Limits are explicit: at most sixteen calls per record, one to eight manually edited steps, maximum accumulated model time 1,800 seconds, maximum candidate 32,000 characters and per-request output limit where the model supports it. Default limits are six calls, 600 seconds and 16,000 candidate characters. Plans have a 90-second bounded wait; focused reviews use the remaining budget up to 300 seconds and count as calls. Closing the panel does not cancel an approved task; Stop/Terminate and software shutdown target only owned requests. Completed buffers are released.

API budget enforcement requires configured input/output prices, matching currency and a supported token cap. The preflight uses a conservative UTF-8 byte bound, not an official bill or exact token estimator. Returned usage is recorded when provided; canceled or unavailable usage remains UNKNOWN. Codex subscription usage and billing are not invented. Requests are not automatically retried or redirected to another provider.

## Localization and packaging

The new director UI has Simplified Chinese and English catalogs. The other 24 existing languages explicitly fall back through the existing i18next mechanism; they are not counted as translated. The modal and its styles are lazy loaded. No new dependency is installed. Frozen resources include only curated existing method text and the original public demo. Personal projects, reference libraries, credentials and private character assets are excluded from release archives.

## Verification boundary

The delivery report distinguishes local contract tests, compatible protocol fixtures, actual Codex requests and actual Windows WebView interactions. A local compatible stream is not a real DeepSeek response. Lack of a configured, authorized DeepSeek credential is reported as UNVERIFIED. Physical Microsoft Pinyin candidate selection and broad Windows DPI testing are not established by this scoped feature check.


## Linked consoles (2.24.1)

The Director remains the primary creative workspace. Task Brief, Candidate and Results/Receipts are views of the same record. The progress bar counts enabled steps with persisted completion receipts. Model call attempts include failed requests; the waiting clock measures only this panel's observation interval, not writing time, inferred model progress or an ETA.

Planning and writing each expose the existing concrete model, supported parameters and context controls. Overrides are saved on this task, not as global preferences. Quick mode only uses the execution model. Older records retain their previous shared-control behavior until an author explicitly edits the role controls. Output caps remain bounded by the task/model limits. Small context budgets fail safely rather than silently removing the approved Writer packet.

1. Finish or stop the current request, then save candidate edits.
2. In Results/Receipts choose the Python local-analysis handoff.
3. Existing Python Control opens. Load the read-only sample; loading executes nothing.
4. Inspect the script and project/persona permissions, then explicitly Run. Suggest mode retains existing confirmations.
5. `get_director_result` returns only the author-selected fixed candidate version. The sample counts characters/paragraphs locally. It cannot select other Director IDs or read the Writer packet. Other actions retain their normal permissions.
6. Return to the same record or explicitly unlink. A changed candidate invalidates the old handoff; return and hand off the new version.

This binding grants no external Python token, arbitrary host paths, Shell, SQL or model call. Scripts are never automatically replayed. Handoff provenance stores the selected ID, revision, source path and candidate hash. Candidate content remains private project metadata and uses existing backups.

History supports goal/model search and task-state filters. JSON report export includes the current goal, plan, candidate, receipts and usage: check privacy before sharing. It omits the Writer packet and raw source document. Manuscript adoption still requires existing guarded Diff; saving a local candidate is not adoption.


## Flexible author control (2.24.2)

- Run Only This Step executes exactly the selected enabled, pending step, appending its result at the end of the candidate. It does not rearrange old prose or execute following steps, even when whole-plan auto-continue is enabled. The ordinary Run button follows the next pending step.
- Each step can inherit task defaults or use its own concrete model and supported controls. Advanced controls initialize on expansion. Changing to another model without explicit controls discards the previous model's parameters while retaining the task context policy. Every run rechecks the actual model, approved Writer view, privacy and budgets.
- An ordinary earlier step may run before an important later step. Scheduling pauses before that important step until the author approves it. Disabled steps do not require approval or execute.
- Duplicate and reorder steps with stable IDs. Identical text does not imply that a copied step has already completed. Disabling/re-enabling an already completed step retains its completion; it does not repeat work. Editing the content of a completed step makes that changed step pending. Earlier ID-less plans and clients match unchanged instances once; no project migration is required.
- Independent Attempts copies local configuration without calling a model. Keep Candidate preserves existing progress; Start Fresh clears only the new attempt's candidate/completion. Original tasks remain intact, including terminated tasks. The original source revision and Writer reference stay bound; a stale source/context must be resolved through the existing author workflow before execution/adoption.
- Explicit Python analysis return reads the actual project/persona run record, not browser-supplied output. Notes record the candidate hash and run provenance. Candidate changes mark an older note stale. Notes never enter planning prompts, Writer context or a candidate snapshot automatically. Removing a task note preserves the original Python history and allows an explicit reattachment.
- A task can retain 20 analysis notes. The task view stores the first 8,000 output characters and a full-output hash; full output remains in Python history. Private JSON reports include these notes and must be inspected before sharing.

Capacity remains bounded: 8 plan steps and 16 call attempts are maxima an author can choose, not default automatic work. Default plans still ask for at most four AI-proposed steps, with six call attempts, 600 seconds and 16,000 candidate characters. No automatic retry, model fallback or formal adoption was added.

Independent attempts retain saved author directions as well as the plan/model configuration. Prior Python analysis notes are not inherited into the new attempt or Writer prompt.
