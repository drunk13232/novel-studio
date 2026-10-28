# 2.24.3 Workbench Experience Preview — Verification

Date: 2026-10-28 (Asia/Shanghai). Status: LOCAL PASS / overall Preview PARTIAL.

## What changed

1. Existing context, scene, lookup, author material and fact-review controls use the existing resizable reference split. The manuscript keeps its vertical editing area; tool/reference tabs and focus retain current-session inputs.
2. The Director is a direct writing-toolbar entry. It returns after the existing explicit context approval without starting a model call. Pending navigation is visible and cancellable.
3. Source-dependent tools save through the original etag/recovery path once and reread the saved source. Failed saves, newer edits and changed/late source scope block outdated continuation.
4. Revision text and notes receive keep/discard protection. Closing a preview preserves the proposal; rejecting is explicit. Busy decisions are fenced, late reads are scoped, and adoption returns only after clearing the unsaved guard.
5. Unsaved material/fact-review return links shorten recovery. Feedback text does not intercept tool clicks; close/diagnostic actions remain active. Concrete revision conflict reasons remain visible.

No dependency, author-data format, database migration, Agent or global Codex configuration change.

## Actual local evidence

- 41 related backend checks passed in the project venv after resuming: writing-assist, creative-spaces, creative-boundaries and creative-director. Fixtures use isolated public/synthetic data; generated model outputs in those unit tests are not real remote-AI validation.
- 24 production-page browser scenarios passed in an independent headless Edge with the real local backend. This is browser interaction, not the Windows native container.
- One additional material-catalog UI scenario used an explicitly synthetic intercepted GET response to check the direct return button and retained form input. It does not validate persistent material storage and is reported separately as MOCK_CATALOG_UI_PASS.
- No remote model request was made by these UI checks. Context preview/approval and domain saves used real local endpoints; no paid request, real author prose or global Codex configuration was used.

### Reproduced before fixing

At 1366x768 the earlier context panel reduced the visible manuscript-editor height from approximately 330px to 160px. Switching from an edited candidate A to B lost the local edit without a keep/discard decision. The combined close/reject button marked a proposed candidate as REJECTED.

### Checked after fixing

- Manuscript-editor height stays approximately 330px with the context dock open at the same viewport. The split uses horizontal space and remains adjustable.
- Save-then-preview with one click; typed numeric context input; reference/tool switching and focus restore preserve inputs.
- Explicit context approval opens the requested Director without running a model.
- Save failure preserves input; editing while a save is pending blocks an older snapshot. Edits during approval prevent stale continuation; saving and reapproval can continue normally.
- Undo/redo after dock changes and reload of saved text work in CodeMirror. This programmatic text input is not a physical Windows Chinese IME test.
- Dirty candidate text/notes, switch/close/discard, proposal preservation and single-candidate rejection; none of these preview/reject actions change manuscript text.
- A stale candidate is rejected with a precise conflict explanation and no overwrite. Explicit author acceptance of an edited, current-source fixture writes once and returns to the manuscript even on a double click.
- A delayed candidate read cannot reopen a discarded scope after chapter navigation; the formal sample chapter remains read-only.
- Writing layout has no horizontal page overflow at 1366, 1024 and 900px when using the existing collapsible navigation. English and Arabic RTL dark-theme dock samples passed; untranslated new strings use the existing English fallback and are not counted as translated Arabic.

## Remaining verification boundaries

- Windows native WebView2 clicking, physical Chinese IME, actual system DPI, real remote Codex/custom-provider generation and end-to-end external services were not revalidated in this update.
- Local control-worker execution inside the packaged EXE, package CRC/manifest/resource checks and artifact hashes are recorded in the release verification JSON after packaging. They do not prove native-window acceptance.
- Large lazy chunks (Monaco, PDF and timeline) still produce Vite size notices. This update adds no library and does not claim measured startup/memory gains.
- Unsaved Diff edits remain session-local until author acceptance. This update protects switching/closing, but does not invent persistent revision-draft storage or automatic adoption.
- Tool-side form state survives switching/focus within the current chapter session. Cross-restart context scope uses the existing explicit remember action; other temporary form values are not all persisted.

## Reproduce safely

Run the backend's four related pytest modules with an isolated temporary directory and build the frontend using the existing npm build script. `web/frontend/scripts/check-workbench-experience.mjs <audit-directory>` requires an explicitly isolated loopback fixture configuration with `fixture: public-demo-only`; never point it at a personal workspace. The private test server, identities, screenshots, injected data and raw runtime evidence remain outside the source package.

Previous releases are retained. No desktop shortcut replacement, Git commit/push or publication is part of this update.
