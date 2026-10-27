# Creative Workflow Reliability · 2.22.1

This pass deepens the eight existing tools. It adds no AI engine, dependency, database migration or new manuscript authority.

## Practical changes

1. **Curves and reader simulations.** Bad reader history is isolated rather than preventing curve/reader initialization. Unwritten chapter cards remain explicitly uncovered. Missing tasks recover only from a persisted report whose project, profile and frozen sources match; no AI request is replayed. Missing reports, stale evidence and interrupted/cancelled work are distinct. Late history/task replies cannot replace another viewed batch or chunk.
2. **Writing ritual.** Unsaved goal and journal inputs participate in existing close/navigation protection. A goal update compares `expected_daily`, changes daily only and preserves other goal fields. Saving while typing does not overwrite newer input or unexpectedly advance the ritual. Defaults and skip behavior remain optional and local.
3. **Annual report.** Core values, project and selected year are checked. Invalid/duplicate optional month/hour/day entries are omitted with partial-data disclosure; an incomplete 24-hour record is not drawn as a complete hourly chart. Long names and large totals fit their own sharing-card regions. Manual/AI/restored/unknown accounting is unchanged.
4. **Reader personas.** The existing ReviewCenter, Provider and budget confirmation remain the only inference route. Recovery does not manufacture a report, override cancellation or infer that a model read unwritten chapters. Model quality remains unverified in this pass.
5. **Maps.** Bounded local undo/redo, buffered decimal coordinates, pin labels/rebinding, route point undo/cancel, map search, shape renaming and explicit map removal. Unsaved/conflicting maps can be downloaded locally, including unfinished drawing points; internal map switching confirms their discard. Thumbnail backgrounds load first, originals only on request. Derived map notes never write story facts.
6. **Print.** Request IDs bind fixed payloads. Cancellation reaches queued/running local rendering without waiting behind prose writes; cancellation-before-start is retained. Existing Windows job cleanup owns the renderer process. Cached success is revalidated against PDF SHA. Source versions are checked after save/restore, focus and manual refresh; uncertain/stale snapshots require explicit export consent. Preview and download still use one immutable PDF.
7. **Parallel chapters.** Interrupted transactions have a read-only recovery preview. Explicit confirmation rolls back only exact known before/after states using existing checkpoints; later work, missing evidence and Final/committed protection block it. Historical switch Diff is frozen. Damaged logs are isolated, and unsaved alternatives can be downloaded without a mutation. No force-recovery mode is added.
8. **Audio.** Reopening follows an active project export. Failed progress reads can be retried without synthesis. Scope search/selection and local history warnings are explicit. Completed same-project, same-voice/rate samples may provide a labelled approximate estimate once at least 500 characters exist; otherwise estimates remain unknown. Resume preserves externally edited WAVs and uses a new filename. Hashing is streamed. Cancellation bypasses only the mutation queue, never origin/session checks.

## Resource and safety boundaries

- Map undo is limited to 40 local snapshots. It is unsaved UI history, while saved changes retain existing revision checkpoints.
- Audio history examines at most the 200 newest metadata candidates and returns at most 50 valid records. Damaged records stay on disk. Streamed hashing does not load an entire WAV.
- Same-project saved-source revisions, confirmation payloads and idempotent receipts remain authoritative. No result is automatically adopted into Canon, State, Knowledge, Timeline or Final.
- Print has at most four queued/running jobs globally and one per project, 60-second process timeout and existing PDF/character limits.
- No background remote requests, cross-provider fallback, new external service or GUI automation is introduced.

## Remaining limits

Curves are still rough local lexical signals, not semantic literary judgment. Reader chunks are independent simulations, not a human readership study or complete long-book memory. Old interrupted undo records without required snapshots need manual recovery; later author work is never force-overwritten. PDF needs installed Edge/Chrome and available system fonts, and orphan/widow locations are not reliably auto-diagnosed. Duration estimates are voice/text-dependent, not promises. Native GUI, physical IME, playback listening and real remote model quality remain outside this run.

Technical basis: [Python streamed file digest](https://docs.python.org/3/library/hashlib.html#hashlib.file_digest) and [Windows non-replacing rename behavior](https://docs.python.org/3/library/os.html#os.rename). Existing local SAPI, Chromium, React, Recharts, PDF.js, Pydantic and revision mechanisms are reused.
