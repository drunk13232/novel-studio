# Novel Studio · 2.24.27 Recovery Integrity Preview

## Current public version: 2.24.27 Preview

Recovery integrity and safe saving: compare the actual stored recovery version before cleanup, separate confirmed manuscript saves from recovery maintenance, reject stale cleanup receipts, and guard recovery actions during chapter loading. [Release 2.24.27](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.27-preview) provides Setup, portable ZIP and SHA-256 checksums. Older releases remain available.

**Preview / PARTIAL**: the completed local delivery records 26 isolated headless cases, 15 real local API tests and 56 separately labelled local-transport assertions. Packaged workers and silent install/uninstall are separate gates. Native GUI clicks, physical Chinese IME, system DPI, voice and real cloud AI are not newly verified. One isolated Windows service-shutdown problem remains under investigation, not claimed fixed. See Actions and the Release for exact-commit CI.

The existing four-field recovery format needs no migration; recovery copies do not replace independent backups. New automatic cleanup checks the version; the old explicit unconditional-delete endpoint remains compatible. Public source uses the sealed 2.24.27 snapshot and excludes later shutdown diagnostics. Historical local-delivery notes below retain their original verification scope.

## 2.24.27

Local Preview / PARTIAL. Cleanup compares the actual recovery-copy revision and late receipts only clear still-owned caches. Confirmed manuscript saves finish waiting for cleanup after ten seconds with a retained warning. Rejected retries retain prior uncertainty; busy workspaces do not create fake disk conflicts. Old recovery actions are hidden during chapter reads and remain available after cancellation. 26 current isolated headless cases, 15 real local API tests and 56 simulated transport assertions passed; no AI calls. See [2.24.27 notes](docs/workbench-experience/DELIVERY-2.24.27.md). No publication or shortcut update.

The current public release is [2.24.26 Preview](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.26-preview). Local 2.24.27 is not published; both retain Preview verification boundaries.

## 2.24.26

Local Preview / PARTIAL. Cancellable chapter/recovery reads use a 10-second header/body deadline, retain existing content on failure and never bypass recovery or replay saves. Workspace restore resolves its target first; two measured scenarios reduced four reads to two, without claiming a matching startup-speed improvement. Thirty-nine isolated headless cases passed, including unsaved text, undo/redo, cancellation with an enabled writing ritual, save/format and snapshot regressions. See [2.24.26 notes](docs/workbench-experience/DELIVERY-2.24.26.md). No publication or shortcut update.

## 2.24.25

Local Preview / PARTIAL. Successful author reload of a changed revision after an uncertain save refreshes actual saved-event progress without creating events or word counts. Unconfirmed saves expose existing compare/reload controls; read-only snapshots support empty files, cancellation, explicit retry and a deadline. 28 isolated headless cases passed. See [2.24.25 notes](docs/workbench-experience/DELIVERY-2.24.25.md). Public release remains 2.24.23; no automatic publication or shortcut change.

## 2.24.24

Local Preview / PARTIAL. Post-save read-only verification has a 10-second deadline covering headers and JSON body. Timeout stops the browser read, retains edits/unconfirmed state and never cancels or replays the submitted write. 18 isolated headless cases passed. See [2.24.24 notes](docs/workbench-experience/DELIVERY-2.24.24.md). Public release remains 2.24.23; no automatic publication or shortcut change.

## Previous public version: 2.24.23 Preview

Includes the 2.24.20–2.24.23 selection-task cancellation, leave/exit and verified-save-feedback fixes. Download Setup, portable ZIP and SHA-256 checksums from [Release 2.24.23](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.23-preview). Older releases retained.

**Preview / PARTIAL**: 47 isolated headless scenarios cover save/recovery/leave protection. Native GUI, physical Chinese IME, system DPI, voices, real cloud AI and prolonged use are not newly verified. A desktop-bridge double is not native window acceptance. See the exact commit Actions and Release for CI.

Ambiguous receipts trigger one read-only verification, never automatic write replay. Recovery snapshots do not replace persistent backups.

## 2.24.23

Local Preview / PARTIAL. Manuscript receipts and recovery maintenance are separate. A failed recovery cleanup does not misreport a confirmed manuscript write. Ambiguous receipts use a bounded read-only verification without replaying writes; differing or unconfirmed versions retain input and navigation/exit guards, including undo to an old cache. Explicit manual recovery supports comparison without enabling automatic recovery. See the [2.24.23 guide](docs/workbench-experience/DELIVERY-2.24.23.md). Not automatically published or connected to shortcuts.

## 2.24.22

Local Preview / PARTIAL. Safe exit reuses existing save/recovery/preferences and the desktop bridge. Return to writing, close or Escape cancels preparation before handoff; late receipts cannot invoke closure. Real phases and retryable failures are shown, with a truthful non-cancellable state after native dispatch. Native preparation is guarded, idempotent, rechecks tasks after backups and recovers from close-worker preparation failure. See the [2.24.22 guide](docs/workbench-experience/DELIVERY-2.24.22.md). Not automatically published or installed into shortcuts.

## 2.24.21

Local Preview / PARTIAL. Pending Save-and-leave and Keep-recovery-and-leave operations now retain their own navigation owner. Continue editing, close and Escape cancel navigation immediately; late write receipts cannot revive it. Recheck the current content/page/scope before leaving. The dialog shows real write status, readable failures and explicit retry, with an explanation when recovery is off. See the [2.24.21 guide](docs/workbench-experience/DELIVERY-2.24.21.md). This local version is not automatically published; public downloads remain on [GitHub Releases](https://github.com/drunk13232/novel-studio/releases).

## 2.24.20

Local Preview / PARTIAL. Recheck selected-text source and scope during preparation, queued dispatch and retries. Existing assistant/Python bridges supply an ephemeral operation proof, and the existing backend Session rejects cancelled, expired or mismatched operations before creating a task. Accepted children retain existing ownership/cancellation; uncertain receipts direct authors to history without automatic replay. Chinese/English status and error copy is included. See the [2.24.20 guide](docs/workbench-experience/DELIVERY-2.24.20.md). Public downloads remain on [GitHub Releases](https://github.com/drunk13232/novel-studio/releases).

## 2.24.19

2.24.19 Preview. Recheck the live page, chapter, newer navigation and unsaved input after assistant-result lookups. Failed reads stop subsequent candidate/task display; explicit retries clear their own errors. Existing Actions and author approvals remain. See the [2.24.19 guide](docs/workbench-experience/DELIVERY-2.24.19.md).

Installer, portable ZIP and checksums: [2.24.19 Releases](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.19-preview).

> **Published 2.24.19 boundaries and limitations (later local fixes are described above):** native GUI, physical IME/DPI, voice and new real-model acceptance remain unverified. Selected-text AI preparation and cancellation still have a known delayed-dispatch boundary: a candidate task can start after an assistant receipt times out or is cancelled. Check task history before retrying and avoid this route with paid models until the follow-up is delivered. Adoption still requires the existing author Diff approval. Window-local recovery is not a persistent backup.

## 2.24.18

2.24.18 Preview. Scoped candidate reads prevent late responses from replacing a newer comparison; live unsaved input is checked again before applying a response. Real read status, cancel-read and explicit retry preserve existing Diff, revision and author approvals. See the [2.24.18 guide](docs/workbench-experience/DELIVERY-2.24.18.md).

Installer, portable ZIP and checksums: [2.24.18 Releases](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.18-preview).


## 2.24.17

Local iteration, included in 2.24.18 Preview. Protect unsaved local recovery after cross-window reloads in Selection Diff and Revision Desk. Export the actual retained copy and explicitly restore or discard it; handled candidates remain locked. Download is not project persistence, and recovery remains window-local. See the [2.24.17 guide](docs/workbench-experience/DELIVERY-2.24.17.md).

## 2.24.16

2.24.16 Preview. Fresh candidates no longer inherit prior notes/choices. Handled history exposes saved author text and notes separately; stale read-only previews retain the selected variant rather than restoring a different draft. Existing source and adoption protections remain. Installer and portable ZIP: [Releases](https://github.com/drunk13232/novel-studio/releases/tag/v2.24.16-preview). See the [2.24.16 guide](docs/workbench-experience/DELIVERY-2.24.16.md).

## 2.24.15

2.24.15 Preview includes the candidate-editing improvements from 2.24.14 and prevents late save receipts from replaying a cancelled variant switch or closing a replacement comparison. Already committed snapshots remain stored; source checks and author adoption authority remain intact. See the [2.24.15 guide](docs/workbench-experience/DELIVERY-2.24.15.md). Preview / PARTIAL remains: headless browser and worker checks do not establish native GUI, physical IME or real-model acceptance.

## 2.24.14

Local iteration, incorporated into 2.24.15 Preview. Repair selected-hunk persistence, independent variants and continuous candidate/note typing during autosave. Explicit save remembers the selected variant; new, expanded or ambiguous merged changes require author review. See the [2.24.14 guide](docs/workbench-experience/DELIVERY-2.24.14.md). Public artifacts follow Releases.

## 2.24.13

2.24.13 Preview release candidate, including the local reliability fixes from 2.24.11–2.24.12. Fix source-range mapping for candidate evidence, retain-to-cursor, partial rewrite and literary-scoring selection across newline formats. Explicit Diff adoption preserves document line endings and UTF-8 BOM, retains raw candidate provenance and the pre-adoption snapshot, and keeps existing mixed-source guards. See the [2.24.13 guide](docs/workbench-experience/DELIVERY-2.24.13.md). Local checks remain distinct from remote AI and native GUI/physical IME/DPI acceptance.

## 2.24.12

Local iteration, incorporated into 2.24.13 Preview. Reports become historical when AI append, rewrite, cancellation retention or restart recovery changes a candidate; missing provenance is explicitly unverifiable. Verified quotations can locate candidate text, while changed manuscript/reference sources are disclosed separately. Owned terminal receipts survive background record cleanup. See the [2.24.12 guide](docs/workbench-experience/DELIVERY-2.24.12.md). Native GUI, physical IME, DPI and new remote-AI acceptance remain unverified.

## 2.24.11

Local iteration, incorporated into 2.24.13 Preview. This update retains input during author takeover, orders task-state reads, scopes saved reports and adds read-only retries. Connection checks no longer block author saves and recover from unexpected failures. Existing author confirmation, project isolation and proposed-writing flows remain. See the [2.24.11 guide](docs/workbench-experience/DELIVERY-2.24.11.md). Native GUI, physical IME, DPI and new remote-AI acceptance remain unverified.

## 2.24.10

This update repairs input retention, save receipts and workspace handoffs in the existing Creative Director. Visiting My Workflows preserves book-target drafts; new typing survives a pending save; guarded exits cover Diff and Python; late receipts cannot reopen a closed view. Existing author confirmation and proposed-writing flows remain intact. See the [2.24.10 guide and verification boundaries](docs/workbench-experience/DELIVERY-2.24.10.md). Preview / PARTIAL remains: browser checks do not establish native GUI, physical IME or real-AI acceptance.

## 2.24.9

This iteration strengthens the existing Director with the SDK-paired Codex runtime, actual-prose delivery and length targets, durable same-task recovery, input-budget preflight, scene interfaces and author-selected book delivery checks. Writing remains proposed until author acceptance; length is not literary quality. Trial data is isolated original fiction. See the [2.24.9 guide and verification boundaries](docs/workbench-experience/DELIVERY-2.24.9.md). Versions 2.24.5–2.24.8 below are historical local iterations whose changes are included in this 2.24.9 Preview release. Browser and worker checks do not replace native GUI, IME or DPI acceptance.

## 2.24.8

This iteration connects the existing Creative Director and Writer to scoped MCP actions for chapter drafting, real progress, stop/resume and existing Diff candidates. Model phases honor the request timeout. Explicit candidate references are version-bound and require author context approval; they never become Canon automatically. Local assistant history retains validated candidate links. Original trial manuscripts and run records remain outside public packages. Preview / PARTIAL remains: native desktop, physical IME and complete literary quality were not reaccepted. See [workflow guide](docs/workbench-experience/DELIVERY-2.24.8.md).

## 2.24.7

Local Record Editing Preview, not publicly released. Existing to-do, revision and inspiration editors retain changes made while a save receipt is pending, then rebase on the acknowledged record for the next explicit save. Existing close/leave protection covers pending saves and undo. Chinese/English guidance separates the saved submission from newer unsaved edits. See the [guide](docs/workbench-experience/README.md) and [verification boundaries](docs/workbench-experience/DELIVERY-2.24.7.md).

## 2.24.6

Local Save Integrity Preview, not yet published to GitHub. Manuscript save/recovery receipts remain bound to their original chapter. Entry submission preserves text and field changes made while waiting for an earlier save. Checking an unchanged candidate resumes normal autosave without clearing existing manual pauses. Existing persistence and author-approval channels remain authoritative, with no new data format. See the [guide](docs/workbench-experience/README.md) and [verification boundaries](docs/workbench-experience/DELIVERY-2.24.6.md).

## 2.24.5

This is a local delivery, not yet a GitHub publication. Chapter to-do and revision inputs survive tab switches and dock closure. Failed candidate reads can be retried; conflicting local/stored versions can be inspected before an explicit reload, with window-local recovery of previous edits. Handled history is accurately read-only, and rejection immediately refreshes Current Chapter. Existing adoption, source-version and manuscript protection remain authoritative. See the [guide](docs/workbench-experience/README.md) and [verification boundaries](docs/workbench-experience/DELIVERY-2.24.5.md).

## 2.24.4

Manual candidate edits and notes now save locally for later recovery, independently for each generated variant. Closing a comparison preserves the proposal; author adoption remains explicit. The existing writing dock brings together current-chapter goals, to-dos, pending candidates and evidence. Existing AI controls show planned model/receiving host, supported effort and source scope before running. No model is called simply by opening these controls. See the [guide](docs/workbench-experience/README.md) and [verification limits](docs/workbench-experience/DELIVERY-2.24.4.md).

## 2.24.3

Writing tools use the existing adjustable sidebar instead of consuming manuscript height. Open the Director directly and return after explicit context approval without starting a model request. Unsaved prose uses the original save channel; failed saves and edits made while waiting prevent stale-context continuation. Revision previews distinguish closing from rejecting, protecting unaccepted text and notes before switching or closing. See the [workbench guide](docs/workbench-experience/README.md) and [verification boundaries](docs/workbench-experience/DELIVERY-2.24.3.md).

## 2.24.2

Run a selected Director step with independent model controls, duplicate steps and create independent candidate attempts. Explicitly return actual Python output as author-only notes with candidate-version warnings and note removal. Existing context approval, permissions, budgets and guarded Diff remain in force. See the [guide](docs/creative-director/README.md) and [verification](docs/creative-director/DELIVERY-2.24.2.md).


## 2.24.1

The Creative Director separates task briefs, candidates and execution receipts, with independent task-local planner/writer controls. Explicitly hand a saved candidate to existing Python Control for local read-only analysis and return to the same task. Loading never executes scripts, calls AI or adopts prose. See the [guide](docs/creative-director/README.md) and [verification boundaries](docs/creative-director/DELIVERY-2.24.1.md).

## 2.24.0 update

My Workflows in the existing Director and World Studio supports ordered editable steps, enable/disable, exact models, request controls, scoped sources and author checkpoints. Save, copy, import and export world/chapter recipes; retain versioned run snapshots, actual results and cancelled candidate prefixes. AI can propose a recipe but never automatically executes or adopts manuscripts/settings. See the [guide](docs/custom-workflows/README.md) and [verification boundaries](docs/custom-workflows/DELIVERY.md). Still Preview: local protocol fixtures are not real remote-AI or native desktop acceptance.

[![CI](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml)

> Public repository: `drunk13232/novel-studio`. Check the badge and Actions history for actual hosted-CI status. Local tests, cloud CI, native desktop and real AI are separate verification gates.

A local-first personal AI fiction workspace. Manual writing needs no AI connection. Authors retain final authority over manuscripts, settings and revisions.

**Status: Preview / PARTIAL; local development preview; public artifacts follow Releases; see [Releases](https://github.com/drunk13232/novel-studio/releases) for artifacts and verification limits. Apache-2.0; Copyright 2026 drunk13232.** [简体中文](README.md)

## Features and external requirements

|Capability|Implemented scope|Requirements and boundaries|
|---|---|---|
|Writing and safe revision|Short stories, novellas, novels and collections; CodeMirror writing, Monaco Diff, tabs, splits, autosave and draft protection.|Local|
|Writing dashboard and annual review|Saved-text net deltas, negative deletions and separate manual/AI sources; heatmap, streaks, save-hour distribution, goals and local share images.|Local; not writing time|
|Focus and writing ritual|Optional Pomodoro, typewriter scroll, offline typing sound, checklist, daily goal/journal; activity/eye reminders default off.|Local; non-blocking|
|Cross-chapter find and replace|Literal/case/whole-word/bounded regex, per-hit preview, protected-name warnings, explicit approval, revision guards and batch rollback.|Local; author approval|
|Characters, worlds and rules|Characters, locations, factions, rule cards, encyclopedia/templates, citations and explicitly released Writer summaries.|Local; optional AI design|
|Timeline, relations and plot matrix|Existing entity/event links, character and plot tracks; plans remain separate from committed facts.|Local|
|Clue board|Planned/planted/partial/resolved states, evidence and overdue reminders; annotations do not alter prose or Canon.|Local|
|Emotion/tension curves|Book/character/plot overlays, exact excerpts, author overrides, unknown coverage and flat-span reminders.|Rough local signals; not literary scores|
|Literary core, review and scoring|Style/ideas/clues/logic workbenches, staged evidence-based passage-to-book evaluation, history comparison and revision todos.|AI evaluation needs a selected model|
|Simulated reader profiles|Project profiles, comparison, frozen scope/budget, verified excerpts and separate history; unsupported results are withheld.|AI required; simulated, not real readers|
|References and style sources|Local import, PDF/document reading, citations, bookmarks, reference splits and source provenance.|Author-provided lawful sources|
|World maps|Local background or blank canvas, place markers, regions/routes, multiple maps, Bible links and backups.|No third-party maps bundled|
|World Logic Lab|Z3, NetworkX, SymPy/Pint and OR-Tools; locked criteria, counterfactuals, provenance and portable reports.|Basic solving local; not social forecasting|
|AI co-writing and Creative Director|Context previews, concrete models/supported parameters, candidate co-writing, Codex planning and selected-Provider execution.|On demand; no automatic paid fallback|
|Codex and controlled software assistant|Reuses login, official SDK, stdio MCP, Action Registry, receipts and durable human approval.|External authenticated Codex; not arbitrary system control|
|Custom APIs and local models|Chat Completions/Responses, streaming, task routing, system credential storage and usage records.|Configured API or running local service|
|Role workspace and embodied interface|Separate character sessions and the existing controlled assistant; dynamic models, runtime and voices depend on local setup.|No private models, voices or Cubism Core distributed|
|Chapter alternatives|Chapter-level draft alternatives, Diff, explicit mainline switches and guards; default statistics/export use mainline only.|Final/committed protection retained|
|Print preview and book export|Preview/export share the same PDF layout result; page size, numbering, fonts and chapter navigation.|Local browser/fonts; some formats need Pandoc|
|Read-aloud and audio export|Windows SAPI voices, chapter WAV files, progress, cancellation and completed-chapter reuse.|Installed voices; quality varies|
|Images and external visual tools|Assets, covers, ComfyUI workflows and optional trusted Blender-template integration.|Generation needs external services/models/software|
|Plugins, themes and languages|Local plugin entry, existing themes and 26 offline UI locales; newer advanced views primarily Chinese/English.|Translation/RTL and integrations remain Preview|
|Backup and restore|Manifest, hashes, SQLite indexes and restore as a new project; API secrets excluded.|Local; re-enter secrets on another machine|

## Use and development

Extract the whole Windows archive, keeping `_internal` beside the EXE. Choose a separate data directory or the original demo during first-run setup. Do not keep your only manuscript copy in the installation folder. Manual writing remains available without AI.

- [Installation](INSTALL.md) · [Independent development and tests](docs/DEVELOPMENT.md) · [Windows build](docs/WINDOWS-BUILD.md)
- [AI use and permissions](docs/AI.md) · [AI development guide](desktop/developer-guide/AI-DEVELOPMENT.md)
- [Changelog](CHANGELOG.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

`desktop/version.json` and `web/frontend/package.json` record the application version. Source candidates exclude development environments, private works, credentials and parent Git history. External Codex/Skills, ComfyUI, Pandoc and the WebView2 installer are not bundled. Some features need user configuration; ordinary text APIs do not inherit Codex file privileges.

## Verification boundaries and known limitations

Historical 2.22.2 focused evidence (not current-version revalidation): 28 isolated A/B backend checks, three shared-review regressions and 55 React component assertions; actual Data Center backup/restore and a 500-chapter three-line headless chart passed. Mock inference/components and actual services are labelled separately. An EXE command-line check is not native window acceptance.

- The [current installation report](docs/oss/INSTALL-VERIFICATION.md) is authoritative for this public candidate's independent installation, full backend suite, build and desktop checks. Older results are not current acceptance.
- Real remote-AI quality, every Provider parameter, physical Chinese IME, Windows system-DPI combinations and prolonged load are not comprehensively verified.
- Curves are rough local signals; virtual readers are model simulations. A verified quotation does not establish a literary judgment. Models that omit evidence may leave no displayable conclusion.
- A 500-chapter service sample measured 15.152s first analysis, 6.884s cached analysis and 3.023s cache view. These are not full-EXE timings, whole-book semantic understanding or a controlled speedup ratio.
- Actual Yoshino/Rem dynamic models, Cubism runtime and private voices are excluded. Public builds do not claim completed character-asset delivery.
- PDF needs a local browser/fonts; audio needs installed Windows voices. Passing selected samples does not certify every PDF, pagination issue or voice.
- The 26 UI locales need native review; advanced features may fall back. User works are never automatically translated.

## Demonstration, privacy and contribution

[Historical screenshot provenance and scope](docs/oss/SCREENSHOTS.md). Examples use the original demo; historical screenshots do not certify every current feature.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Candidate review record](docs/oss/PREPUBLICATION.md). Never upload private prose, API keys, login settings or unsanitized logs to Issues/PRs. No user/download/community statistics are invented.

## License

[Apache-2.0](LICENSE) · Copyright 2026 drunk13232. See [NOTICE](NOTICE), [COPYRIGHT](COPYRIGHT) and [third-party notices](THIRD_PARTY_NOTICES.md). Dependencies retain their own terms. The software license does not automatically license users' manuscripts, references, images or private character models.
