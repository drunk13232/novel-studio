# Novel Studio · 2.24.0 Custom Workflows Preview
## 2.24.0 update

My Workflows in the existing Director and World Studio supports ordered editable steps, enable/disable, exact models, request controls, scoped sources and author checkpoints. Save, copy, import and export world/chapter recipes; retain versioned run snapshots, actual results and cancelled candidate prefixes. AI can propose a recipe but never automatically executes or adopts manuscripts/settings. See the [guide](docs/custom-workflows/README.md) and [verification boundaries](docs/custom-workflows/DELIVERY.md). Still Preview: local protocol fixtures are not real remote-AI or native desktop acceptance.

[![CI](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml)

> Planned repository: `drunk13232/novel-studio`. This is a local review candidate, not a published repository. GitHub-hosted CI has not run; the badge is not a passing result.

A local-first personal AI fiction workspace. Manual writing needs no AI connection. Authors retain final authority over manuscripts, settings and revisions.

**Status: Preview / PARTIAL; a pre-publication candidate, not a published open-source release. Apache-2.0; Copyright 2026 drunk13232.** [简体中文](README.md)

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

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Current prepublication review](docs/oss/PREPUBLICATION.md). Never upload private prose, API keys, login settings or unsanitized logs to Issues/PRs. No user/download/community statistics are invented.

## License

[Apache-2.0](LICENSE) · Copyright 2026 drunk13232. See [NOTICE](NOTICE), [COPYRIGHT](COPYRIGHT) and [third-party notices](THIRD_PARTY_NOTICES.md). Dependencies retain their own terms. The software license does not automatically license users' manuscripts, references, images or private character models.
