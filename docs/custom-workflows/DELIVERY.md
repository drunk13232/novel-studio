# Novel Studio 2.24.0 · Custom Workflows Preview

Status: PARTIAL / Preview. Implementation uses existing domain services and task execution, not a new Agent runtime.

## Implemented

- Ordered project-local world/chapter templates with stable step IDs, disable/reorder/add/remove, concrete models, request-local controls and bounded selected sources.
- Explicit confirmation, default author checkpoints, bounded continuation, cancellation and unfinished-step retry; no automatic formal adoption.
- Frozen versioned runs, retained pending-step snapshots, source-version checks, cancelled writer prefix and bounded attempt history.
- Configuration-only JSON import/export, template history and copy; schema-validated optional AI design creates an editable template only.
- Existing Data Center restore remaps this control metadata to the restored project, retains source bytes and disables active/automatic replay.
- Lazy UI entry in existing Director / World Studio, Simplified Chinese + English, fallback for other locales and logical RTL layout. No new dependency.

## Actual verification boundary

- LOCAL PASS: 48 targeted workflow, backup, Director and model-control cases in the final grouped run. Production TypeScript/Vite build passed. Earlier focused runs overlap and are not added as unique totals. Actual source requests use httpx/loopback fixtures marked MOCK, not real remote AI.
- A real full Data Center backup/restore retains templates and completed run checkpoints. Existing curve/reader backup regression is separately checked.
- BROWSER PASS: headless Edge against the actual isolated backend and local loopback mock covers template editing, exact model choice, disable/reorder, explicit run, author pause, pending-step edit, completed result, import/export, close/reopen history and narrow/RTL layout. No page errors, business error notifications or external requests occurred in the final browser run. Final archive/install results are recorded separately in release-side verification; this source document is not rewritten after sealing.
- Existing lazy editor/PDF chunk size warnings remain. One existing world relation fixture serializer warning is outside this change.
- No new real Codex, paid third-party AI, physical IME or native-window interaction acceptance is claimed. A build or silent installer check is not native UI verification.

## Limits

Seven designated step kinds only; sequential steps and checkpoints, no open-ended branching or arbitrary scripts. World challenge is an AI opinion workflow, not a mathematical solver invocation. Local proofreading checks the saved chapter, not an unadopted AI candidate. Large input/handoff or insufficient budget fails explicitly. Restored chapter authorizations may require a fresh approved Writer context and new run.

Windows, Setup and developer archives retain old versions and exclude personal data, credentials and private character assets. Project license/copyright and public publication remain owner decisions. See release-side SHA256SUMS.txt and WORKFLOW-VERIFICATION.json for final archive/install checks and protected-file integrity observations.
