# Novel Studio 2.21.7 — Daily Writing Controls Preview

RESULT: PARTIAL — implementation and local checks completed; native GUI, audio,
physical IME and actual Windows minimize/restore are deliberately unverified.
The author asked us not to operate the computer UI. No AI or paid service was called.

## What changed

- Writing dashboard: existing leave-page guard now protects goals, multi-date
  journals and in-flight saves. Explicit dirty/saved/reset state, pending-date
  shortcuts, a date picker and Today reduce scrolling and accidental data loss.
  Responses acknowledge submitted snapshots and preserve newer input.
- Focus: writing-strip start/pause/resume/end, optional explicit break, existing
  focus-layout toggle, typewriter and sound switches. No editor remount or new
  undo stack. Low-frequency settings collapse independently.
- Wellbeing: immediate rest and snooze controls. Snooze requires five more
  foreground-active minutes, excludes background/idle time and retains the
  regular cycle. All opt-in, local and non-blocking.
- Replacement: current/filtered chapter selection; guarded source-return links;
  bounded per-project in-process view recovery. Recovery revalidates saved
  revisions, proper names, scope and expiration before enabling writes. It
  never automatically searches, applies, restores name permission or confirms.
- Clues: select several entries, review author tracking changes, save independent
  card drafts with one confirmation. All targets validate before one checkpoint
  and atomic overlay write. A single invalid target leaves the whole batch
  unchanged. Existing story facts and literary lifecycle sources stay read-only.
- Shared controls: direct replacement/clue links in the writing strip,
  Ctrl+Shift+H to open replacement, Ctrl+Enter to search in its panel, Alt+Left
  to return from the exact source chapter. Existing unsaved guards remain.

## Verification

- 100 relevant backend checks passed, including real isolated FastAPI routes,
  authenticated session handling, safe manuscript save, frozen replacement,
  overall undo, bounded restored-preview validation and atomic clue metadata.
- Focus / wellbeing: 195 LOCAL assertions against production runtime and
  React/CodeMirror, using explicit test clocks/audio adapters.
- Replacement: 125 LOCAL React/jsdom assertions; transport/dialog adapters are
  labeled and do not represent native UI.
- Clue board: 83 LOCAL React/jsdom assertions, including production Radix dialog.
- Dashboard forms: 48 LOCAL React assertions using production dirty registry;
  model/API responses are fixtures, not remote or native acceptance.
- Source-return buttons: 18 LOCAL production React control assertions.
- API scheduling: 28; targeted editor refresh: 13; UTF-16 location: 19;
  writing metrics notification/day-goal: 57 LOCAL assertions.
- Production build, package manifests, ZIP CRC, native regex dispatch and exact
  shipped frontend/resource checks are recorded separately after packaging.
- No browser, Windows window, speaker, physical IME or system DPI was operated.
  No live AI capability was tested or claimed in this round.

## Protection and scope

No new dependency, framework, database migration or event format. Global Codex
configuration is unchanged. Tests write only isolated local fixtures. Author
works and the three previous release candidates are hash-checked separately.

Clue edits target only the existing author overlay, never manuscript, Final,
Canon, State, Knowledge, formal timeline or original lifecycle facts. All
replacement writes retain author confirmation, version guards and safe history.
The release/source packagers retain curated allowlists and private-asset checks.

## Practical limits

- A clue batch accepts at most 200 entries and does not silently split. If more
  than 200 drafts are pending, save a smaller explicit selection first.
- Replacement view recovery is temporary: at most five projects, two hours,
  within the same running frontend. Reload, restart or eviction requires a new
  search. No text snippets or confirmation permissions are cached.
- Revalidation/search resource limits remain visible; unverifiable or changed
  previews cannot become writable. Very large scopes may require narrowing.
- Actual Windows visuals, audio, physical Chinese IME, native minimization,
  reduced-motion appearance and real end-to-end GUI clicks remain UNVERIFIED.

See README.md in this directory for bilingual usage. Old candidates are retained.
This is a preview candidate, not a claim of completed desktop visual acceptance.
