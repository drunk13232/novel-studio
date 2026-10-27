# Narrative insight hardening — 2026-10-25

This pass repairs reliability and day-to-day use of the existing curve/reader
module. It adds no model, AI engine, runtime dependency, migration or navigation
API. Canon, State, Knowledge, Final and manuscript content remain read-only.

## Repairs

1. **History isolation and truthful status.** A damaged or unavailable panel file
   is reported separately and does not hide other profiles/history or stop the
   curve page from initializing. At most 100 recent valid history files are read.
   History derives current task status in memory, without rewriting every saved
   panel. It uses TaskManager's public status so a worker's unfinished terminal
   cleanup is not mistaken for completion.
2. **Conservative recovery.** A disappeared task or a task interrupted explicitly
   by backend restart may recover from an existing report only when project ID,
   report ID, persona ID and every frozen path/revision match. No inference is
   replayed. A missing success report becomes an explicit failed cell, not a
   blank “not run” result. A task without matching report is interrupted; explicit
   cancellation is not overridden by a late report. Damaged/missing old reports
   and stale evidence receive visible, separate messages. Existing retry limits
   and explicit confirmation remain unchanged.
3. **View/request fencing.** Switching history or comparison chunks invalidates
   older responses. A late task callback cannot overwrite another panel, show
   its results under the wrong chunk label, or start a request from that view.
   Retrying/starting a task keeps the selected comparison chunk even though the
   existing backend mutation reply defaults to chunk zero. Failed navigation
   leaves the previously visible panel usable. Project unmount still stops
   automatic batch advancement; an already running read-only task may finish.
4. **Whole-scope coverage.** Whole-book scope now lists unwritten planned chapter
   cards explicitly instead of dropping them before preview. They are unknown,
   not reader facts, and do not trigger model requests. Empty/unreadable/oversized
   text is likewise listed as blocked. A completed readable subset remains
   `PARTIAL_COVERAGE`; explicit selection of only written chapters can still be
   complete for that selected text. The preview and actual frozen inputs remain
   the budget authority. No prose is silently fabricated or truncated.

## Verification boundaries

Focused Python checks use actual isolated temporary manuscript/metadata/report
files. Only inference is an explicit capture adapter, so simulated task/report
checks are MOCK, not real model acceptance. The React check uses real React and
Radix with mocked transport/task/chart/model selection, including controlled
out-of-order response cases. It does not control a browser or Windows GUI. This
pass makes no AI calls, reads no personal novel, and does not touch user data,
Codex global configuration or existing releases. Native UI and real-model quality
are unverified. Evidence for this pass is in
`docs/creative-tools/private-checks/hardening-20261025-111630/` and remains private.
