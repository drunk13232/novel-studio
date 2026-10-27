# Novel Studio 2.10.1 — Personal writing optimization

This release keeps every existing feature and data format. Enable **Settings → General → Personal writing layout** for the open work to reduce sidebar entries; More tools and quick commands retain the complete navigation. Existing focus/split layouts remain available.

Codex status is checked when the AI panel is opened or the user requests a check, not during app startup. No model or ComfyUI service is started automatically. The existing image queue wakes when jobs arrive, with a 30-second safety scan for externally queued records. Backup scheduling is unchanged.

Chapter planning scans only its own directory. Ledger parse results are immutable and keyed by exact source content. Display-only counts/title caches are bounded and keyed by project, file and revision metadata. Fresh source/etag/Final/Canon protection remains authoritative. The knowledge index verifies source stamps before queries instead of synchronously rebuilding during every save/recovery operation.

Recent CodeMirror Undo/Redo is restored only for identical document contents, within the same running application, using the official editor state serializer. A bounded eight-document cache evicts large states. App restart restores existing drafts/cursor/scroll, not serialized Undo history. It never replaces a newer disk revision.

All write checks use an isolated demo workspace. The report distinguishes real desktop interaction, local APIs and unverified Windows IME candidate input. No new framework/dependency, schema migration, AI architecture, plugin or simulated novel generation was added.

The optional personal-layout flag is stored inside the existing project workspace preferences. It is not written as a new top-level preference field, preserving the prior version’s strict preference reader.
