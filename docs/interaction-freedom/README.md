# Interaction & Creative Freedom Preview

Novel Studio 2.19.0 improves the existing writing workspace. It retains the
sixteen themes, project appearance, authoring services, AI routing and protected
revision workflow. It introduces no database migration or new Agent framework.

## Read beside the manuscript

- Right-click a chapter to open it as a read-only reference without leaving the
  current chapter. Keyboard users can open the same context menu with Shift+F10.
- Ctrl+K / Ctrl+P still open the existing command palette and indexes. Search
  for a character, world entry or document, then right-click the result and choose
  **Open in right split**. Enter keeps its original open-in-main behavior.
- Tabs offer the same actions through their visible ellipsis button. Tabs can
  move left/right, be pinned, be closed and reopened. Close others acts on the
  selected menu target; pinned tabs remain. Existing unsaved-change guards apply.
- The reference split is read-only. A second view of the current manuscript is
  a live mirror, never a second writer. Reference visibility changes retain the
  main editor, undo history, selection and active writing-tool inputs.

## Arrange and restore the workspace

The **Layout** menu beside the navigation toggle provides daily writing,
manuscript/reference, AI co-writing and focused writing presets. No preset
starts a generation or a workflow. Opening AI controls may use the existing
on-demand local connection check.

Resize the existing panel separators with the pointer or arrow keys. Save the
result with **Save current as personal layout**. **Restore personal layout** is
also in Ctrl+K. Each novel retains its own current view and one personal layout,
including panel visibility, widths and split ratio. Existing pinned reference
and tab records remain in the same workspace preferences. Layout presets change
panels, not the active workbench or document; select the document normally.

The saved personal layout stores geometry and visibility. It does not freeze a
particular reference document; the current pinned reference remains independently
saved. Unsaved editable reference forms must be saved/cancelled before a layout
change can hide them. Restore default layout at any time. Fonts, themes, model
settings and manuscripts are unaffected.

## Organize inspiration, chapter tasks and revision items

The existing entries pages now support editing text, tags, linked character,
category, priority and notes. Content, tag and note search combines with status
filters. Search choices are temporary view state; records themselves are saved
in the existing project notebook and included in the existing backup mechanism.

Select up to 100 current results and complete, archive or recycle them. A batch
is atomic: a stale revision or missing record rejects the whole request. Undo
the latest state change while remaining on the page. Undo also uses the expected
revision and cannot overwrite a subsequent edit. The recycle bin persists across
restart and supports single or batch restore. There is no permanent-delete action.

Editing retains existing source/anchor metadata and checkpoints the previous
notebook through the existing revision service. Turning an idea into a chapter
task retains the source reference. Completing a task does not finalize a chapter,
pass Final Check, change Canon or commit State. The legacy “propose lore
organization” action records intent only; it truthfully reports that it has not
created a formal world entry.

## Writing and AI safety

Closing/reopening the writing AI panel keeps its current form and any permitted
read-only task subscription in the current project. It does not create a new
model call. Switching a project creates a fresh scoped panel. The existing task
manager remains responsible for persistent task results and cancellation. The
legacy Codex instruction buffer is also isolated per novel during this run.

The ordinary text assistant now displays the existing actual-request receipt
(model, effort, application context estimate, observed usage and timing). Controls
changed during generation explicitly apply to the next request. A completed or
retained interrupted result can be saved as an editable inspiration note by an
explicit author click, with task provenance. It never applies a manuscript edit.

Undoing all changes back to the saved manuscript also removes the recovery copy
created for those discarded edits in the current session. Recovery discovered
on opening a document still requires the existing explicit review decision.

Model IDs, supported effort levels, context settings, provider permission and
Writer-safe Diff continue to use the original controls and services. Unsupported
parameters are not silently enabled. Real AI verification is distinguished from
isolated protocol/model test fixtures in the delivery report.

## Technical basis and limits

- React state retention follows the [official state identity guidance](https://react.dev/learn/preserving-and-resetting-state).
- Object menus use [Radix Context Menu](https://www.radix-ui.com/primitives/docs/components/context-menu)
  2.3.8 (MIT), promoted from an already installed transitive dependency.
- Layouts reuse react-resizable-panels 4.14.4 and its installed v4 API, existing
  preference persistence and schema validation. No second command or search index.
- New UI strings are Simplified Chinese and English. Other languages use the
  existing genuine fallback; no duplicated English translations are claimed.
- Chapter/scene order is not changed by moving tabs. Existing planning and
  dependency protections remain responsible for actual story ordering.
- Personal-layout save/restore has one slot per novel. Batch undo is a current
  page affordance; persistent recovery is the recycle bin and revision backups.
- Physical IME and Windows system DPI validation remain separate from browser
  text input and application zoom checks. External AI availability varies.

Private tests, safety baselines and screenshots are excluded from developer and
Windows archives. This release does not decide the project's open-source license
or redistribute private character artwork, Live2D models, voice assets or keys.
