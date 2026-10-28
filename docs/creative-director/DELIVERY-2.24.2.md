# Flexible Director Preview 2.24.2

Local development delivery only. Previous 2.24.1/2.24.0 remain available; no GitHub publication or desktop shortcut promotion occurs.

## Implemented

- Author-selected single-step execution, independent model controls, per-step actual receipts, duplication, reordering and enable/disable.
- Stable per-step identity with compatibility for older ID-less records/clients. Identical copied content does not inherit a completed status.
- Independent local attempts retain the original and optionally preserve progress or start with an empty candidate. No automatic model call on copying.
- Actual project/persona Python output can be explicitly returned as candidate-hash-bound author-only notes. Notes show stale-candidate warnings and may be removed while retaining original Python history.
- Up to 8 manually edited steps and 16 explicit call attempts; defaults remain unchanged. Existing Writer approval, model privacy/cost gates, task cancellation, project isolation and Diff continue to apply.

## Verification

LOCAL PASS: 59 distinct related backend checks passed across the scoped suite and targeted completion-toggle rerun. Includes actual OpenAI SDK serialization against an in-memory compatible transport (MOCK PROTOCOL), separate step models/parameters, single-step-only scheduling, disabled/important steps, legacy role/step compatibility, independent attempts, stale versions, idempotency, note removal and Writer exclusion.

LOCAL WASI PASS: genuine CPython/WASI execution obtains only the handed-off candidate. The authenticated note endpoint reads actual server run output, rejects another persona and rejects browser-supplied forged output. Notes do not enter Writer prompts or candidate snapshots.

BROWSER PASS: production headless Edge with the real isolated backend passed 12 scenarios: per-step model/effort edits and save, selected-step execution with MOCK model streams, copied-step identity, reordered completion, disabled steps, fresh independent attempt, real WASI output return, stale-note warning, note removal with retained Python history, important-step approval gate, all-disabled no-run controls, and 1366/960/600 layouts with reduced motion. No page errors or external requests were observed. A test initially inspected idle state before the scheduling response; waiting for the actual POST receipt corrected the test without a product change.

DATA: 1,213 protected real-data baseline files remained unchanged. All writes were in isolated public-demo copies.

Packaging/runtime checks are completed in the local CONSOLE-VERIFICATION.json receipt. Real remote Codex/API generation, native WebView window interaction, physical IME and Windows DPI remain UNVERIFIED for this version. Headless checks and protocol fixtures do not establish those gates.

No dependency, Agent, database migration, global Codex change or new host permission was added. Notes are opinions/output, not Canon or automatic Writer input. A single selected step appends; it does not rearrange old prose. Historical source revisions/Writer approvals are retained by copies; stale sources still require the existing author workflow. Existing history display limits remain. The public 2.24.0 Allowlist is not silently promoted; public updates require their normal review.

The final targeted check also confirms that disabling/re-enabling an already completed step retains its completion and candidate, with no extra model call.

Final fork regression confirms that saved author directions are retained, while old Python opinions are excluded from both the copied notes and its Writer prompt.
