# 2.25.1 Data Organization Quality Preview

This local update addresses four confirmed defect classes: unsaved raw JSON could bypass confirmation guards; unknown sort values overwrote missing-entity warnings; a successful retry retained a previous error; repeated entity references generated duplicate comparison rows.

Raw edits now invalidate the preview and confirmation and block save/navigation/reuse until explicitly validated or discarded. Supplemental details are visible/editable. Comparison views deduplicate stable IDs (including legacy repeated-reference receipts), preserve actual missing-record warnings and keep unknown values last. Retry/success/manual revisions clear the current error without deleting historical tasks.

Structure-only reuse requires the original revision and a new goal/source selection. It copies categories, fields and views, but not record values, old source snapshots, task/model receipts or AI consent. Current existing templates are revalidated. The new plan cannot overwrite the old plan or formal lore. Searchable, paginated history reaches earlier plans; existing sources can be filtered by name.

## Verification boundaries

- Related isolated backend, real HTTP/backup restoration, production build and real headless Edge checks are recorded in the delivery evidence.
- Browser checks exercise raw JSON failure/correction, new confirmation, pending descriptions, structure reuse, history beyond 50 items, search/reopen/empty state and the original numeric table/edit workflow.
- One fresh real Codex call on short synthetic material returned a valid editable proposal, without adoption; no actual manuscript or third-party paid API was used.
- Packaged native window/DOM/service/exit checks are distinct from browser interaction. Native mouse/keyboard, physical IME/DPI and long-term usage are not implied. Consult final delivery evidence for actual EXE results.
- This round does not commit, push, publish or modify global Codex configuration. Existing project/Canonical formats, model boundaries, backup and author adoption remain.

The product remains Preview. New source/material import types, arbitrary database/storage design, automatic Canon migration and direct chapter/document source pickers are outside this update. They are not advertised as implemented.

A final re-entry regression found that an already-consumed initial entity target was reapplied on every Bible list refresh. The existing view now consumes each route target once (still waits for available data and protects dirty edits), so saving a second plan does not jump back to an old entry. This is covered by the repeated real browser organization/original-edit flow.
