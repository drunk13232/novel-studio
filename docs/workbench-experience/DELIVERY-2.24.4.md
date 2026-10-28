# 2.24.4 Writing Continuity Preview — Delivery

Date: 2026-10-28 (Asia/Shanghai). Status: local/backend/browser verification; overall Preview PARTIAL because native Windows interaction and real remote AI were not revalidated.

## Delivered behavior

- Existing candidate JSON records gain optional project-local author drafts, independently keyed by generated variant. Text, notes and explicit selection-hunk choices survive reopening and restart. No second candidate store or database migration.
- Atomic compare-and-swap checks prevent two windows overwriting each other. Auto/manual saves are serialized. Conflicted local text remains editable/exportable; stale original sources cannot be adopted. Explicit author adoption continues through existing etag/selection/Final revision safeguards.
- Current Chapter reuses existing goals, notebook to-dos/revision tasks and evidence anchors in the writing dock. Counts update on scoped local events. No polling or automatic AI context expansion.
- Existing AI controls show planned model, host/protocol, supported effort, source scope and explicit parameter overrides. Missing custom models are not labelled Codex; unknown IDs and counts remain unknown. Actual model receipts, source and cost permissions remain authoritative.
- The selection Diff keeps a readable height instead of shrinking to one line in a smaller dialog. Only a diff computed for the current original/candidate pair can be selected/adopted; stale change lists during Monaco recomputation are disabled. Selected line changes retain EOF/newline boundaries, including a final empty line.

## Actual checks

- 52 distinct related backend checks passed: writing assist, creative spaces, creative boundaries, creative director and 11 final candidate draft cases. Real local storage/source/backup behavior was exercised with isolated synthetic/public sample projects.
- 17 existing AI-control tests passed. They inspect actual adapter request parameters through local MockTransport; this is MOCK protocol validation, not remote-AI acceptance.
- The candidate browser suite uses a real local backend and production frontend in headless Edge, with outbound requests blocked. It checks no-op opening, autosave, reopening, independent variants, hunk persistence, conflicts/recovery export, shared Revision Desk data and unchanged manuscript during previews.
- The follow-up suite checks genuine backend restart recovery, persisted concrete model/effort, chapter to-do refresh, selected-hunk adoption, read-only handled-history protection (stale proposed-source rejection is additionally covered by backend tests), ordinary Chinese text save/undo and narrow-window overflow. Both suites passed: 9 candidate-continuity scenarios and 7 follow-up scenarios, with no page errors or model inference requests. Exact evidence is recorded in the release verification JSON.
- New draft persistence tests use the actual Data Center backup, stage and restore-as-new-project path. Text, note and hunk metadata survive under the new project ID.
- 13 direct revision-hunk checks passed, including insertion/deletion at EOF, preserved trailing empty lines, empty source and partial selections. Actual UI adoption is also checked separately.
- Frontend production build passed. Large existing lazy Monaco/PDF/timeline chunks still trigger size notices; no startup/memory gain is claimed.

## Safety and limits

The private test server and data live under desktop/build and are excluded from packages. No real novel, Canon, State or Knowledge write is part of validation. Protected-file hashes and previous release artifact hashes are checked before delivery. No global Codex setting, credential, desktop shortcut, Git commit/push or publication is changed.

No real remote AI call is made. The UI model-catalog fixture is explicitly synthetic; it verifies configuration/preview behavior, not the model service. Adapter MockTransport tests do not establish remote entitlement or service availability.

The more-tools history entry closes its menu before displaying results. Revision Desk rejection also validates the candidate etag and read-only history notes cannot be edited.

No desktop control, native-window clicking, physical Chinese IME or real Windows DPI acceptance is performed. Packaged EXE local control-worker execution is a separate runtime smoke check and does not prove native-window acceptance. No dependency or new Agent was added.

Other temporary tool forms retain their existing current-session behavior; cross-restart persistence here applies to saved candidate drafts, not every open form or Monaco undo stack. Draft autosave is debounced and can fail: heed unsaved/error status, retain/download conflict text before deliberately closing it. Revision Desk adoption applies the entire shown candidate; Selection Diff applies explicitly checked hunks.

## Reproduce

Use the project Python venv and PYTHONPATH=web/backend with an isolated pytest temporary directory. Run the five related modules plus test_ai_controls.py, then npm --prefix web/frontend run build. Browser scripts require an explicitly isolated public-demo-only fixture; never point them at an author's personal workspace. The new generic check script is included with the developer snapshot; raw fixture data and private reports are excluded.

Existing releases remain available. New public/source candidates are not automatically published.
