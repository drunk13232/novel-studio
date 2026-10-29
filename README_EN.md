# Novel Studio · 2.24.10 Director Save & Navigation Preview

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
