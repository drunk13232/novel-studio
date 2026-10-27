# Cross-chapter find and replace

This extends the existing Author Workbench, `BookCenter` catalog,
`StudioTools.doc`, `NovelWorkspace.save`, and revision checkpoints. It does not
create another manuscript store or grant replacement permissions to AI tools.

## Author workflow

Open the existing replacement entry in the writing/review tools. Choose the
book, a volume, or stable chapter IDs; enter literal text or a Unicode regular
expression. Case sensitivity and whole-word matching can be enabled separately.
Whole-word matching uses Unicode letter/number/underscore boundaries, not Chinese
linguistic segmentation. Regex replacements support numbered/named group
references and newline/tab escapes. Empty and zero-width matches are rejected.

Search uses one preferred manuscript per chapter: Final first, otherwise draft,
otherwise the newest manual revision. It includes the whole eligible text rather
than relying on a truncated FTS snippet. Anthology entries do not silently expose
other projects. A manuscript larger than the editor's existing 2 MiB limit is
omitted with an explicit coverage error; it is not silently truncated or changed.

Matched character, place, and world-setting names/aliases are grouped separately
and skipped by default. The author can also search only names. Replacing a name
requires reviewing the warning and enabling inclusion. This never renames Canon
entries. Per-match replacements and batches both show an in-application
confirmation; a skip only changes local preview tracking metadata.

## Safety and recovery

The server freezes query, replacement, match locations, source hashes, and the
current proper-name list in a project-local two-hour preview. Application accepts
only opaque match IDs and a confirmed count. Client-supplied text, offsets, or
paths never authorize a write. Every file hash is checked before a batch starts,
then rechecked by the existing save channel. Unselected chapters are not saved.
Finals and committed manuscripts produce separate manual revision drafts.

PRE_REPLACE checkpoints and batch receipts preserve recovery information. Whole
batch undo checks every target version first. If any has been edited afterwards,
undo refuses the whole batch; it does not overwrite the later work. Failed apply
or undo operations compensate completed writes only when the expected hashes
still match. If an external edit prevents compensation, the batch is marked as
requiring recovery and the historical versions remain available. A process crash
during a batch may require reviewing its receipt and PRE_REPLACE/PRE_REPLACE_UNDO
history manually; the tool does not silently replay interrupted mutations.

Net-save statistics use the existing save events. Undoing a created revision
reverses only the replacement delta as RESTORE; deleting the duplicate revision
does not invent a deletion of the whole copied manuscript.

## Bounds

At most 2,000 matches, 1,000 files, 64 MiB aggregate input, eight seconds of
cross-file search, 150 ms regex work per file, 64 Ki characters per expanded
replacement, and 8 MiB aggregate replacement expansion. Results load in pages of
100 (maximum 200 per request). Reaching a bound explicitly marks partial coverage.
"Replace all" always means all eligible matches in that frozen preview, never
unscanned portions of a book. Narrow the scope to continue.

The timeout-capable `regex` dependency is pinned to 2026.9.29. It is used through
its maintained Unicode matching API; no expression executes Python or shell code.
The package's license files must accompany distributions (see third-party notices).

## Local verification

`web/backend/tests/test_global_replace.py` runs isolated real filesystem saves,
revision history, Final protection, atomic prechecks, conflict handling, Unicode
positions, CRLF/BOM preservation, failed-write compensation, scoped matching,
regex errors/timeouts, oversize omission, and complete-batch undo.

`web/frontend/scripts/check-global-replace.mjs` runs the actual React component
in jsdom with clearly identified local transport/dialog adapters. It checks
input focus, options/scopes, confirmation gating, name warnings, skip and batch
summaries, undo, and localized failures. This is not native desktop or browser
interaction evidence. No computer UI was operated for this work.


## Refinement: reviewing and continuing a preview

The result toolbar separates loaded matches from all matches in the frozen
preview. Authors can select loaded pending results, clear selections, skip a
selection, return a skipped result to pending, or filter statuses. Loading another
page or handling a second-page match retains existing pages and explicit
checkbox choices. A skip only updates the preview and does not create an empty
undo batch. Identical replacements are marked UNCHANGED, not counted as writes.
Deferred proper names are reported separately from author skips.

Results carry line/column and UTF-16 selection locations, a document revision,
and available exact text/context. After an edit, locations track the saved output,
including a zero-length caret for a deletion. Navigation must check the revision
and cannot run an empty-string fallback search. The parent editor provides the
existing location/highlight adapter.

Name protection is recalculated after each write. A newly formed name is added
to pending candidates; original protection is never silently removed during the
same preview after a partial rename. The UI clears permission to include names
after a write so subsequent changes require another review. Batch details show
search settings, per-chapter replacement counts, and original-to-revision paths.
Undo explains when a separate revision will be removed while keeping its Final.

Replacement line breaks are normalized internally and emitted using the original
file format. A bare carriage return is rejected before a write; CRLF escapes do
not create CRCRLF/mixed-line-ending files that cannot be undone. Invalid group
references are validated even when the search finds no matching text.

Stopping a read-only preview cancels the HTTP wait and discards late UI results.
A bounded backend search already running may finish and retain a harmless local
preview. At most one search per project can be in flight. A duplicate gets
REPLACE_SEARCH_BUSY with manual retry guidance; no automatic replay is scheduled.
The in-flight marker is released on success and exceptions, and no manuscript
save lock is held during a search. Apply and undo remain confirmed serialized
mutations and do not falsely advertise mid-write cancellation.

A failed history/page refresh after a successful receipt is displayed separately
from the mutation result. The interface retains only freshly loaded pages and
safe selections, and explicitly warns against repeating an already completed
operation. These refinements have isolated filesystem, concurrency, and jsdom
checks; they are not desktop or browser interaction acceptance.


## Returning from the editor

Opening a match keeps a bounded, project-keyed view record in module memory only.
It contains the opaque preview ID, loaded-page count, match IDs selected by the
author, last-opened match ID, and form/filter controls. It contains no hit,
manuscript excerpt, result, receipt, confirmation, or permission to include names.
There are at most five project records, expiring after two hours. Nothing is
written to localStorage/sessionStorage or another application store, and closing
the application loses this temporary record.

Returning reloads the frozen preview from the existing backend endpoint. The
first GET uses revalidate=true: expiry, proper-name revision, selected manuscript
paths, and saved file hashes are checked using the existing project services.
Revalidation retains the 1,000-file, 64-MiB and eight-second resource bounds.
Unverifiable, changed, missing or expired previews do not become actionable;
inputs remain where possible and the author must explicitly search again.
Ordinary pagination does not rescan all manuscript text. No search or mutation is
replayed by restoration. Loaded pages and valid pending selections are restored,
and the last-opened match is marked without animated scrolling. Name inclusion
always requires a new review; author confirmation is never restored.

The chapter picker offers current-chapter-only, title/number filtering, selecting
visible chapters, and clearing all chapter selections. Filtering never clears
hidden selections; the interface shows both selected and visible counts. The
existing 2,000-ID request limit remains. Ctrl+Enter inside this tool performs
search/preview only. It does nothing during IME composition, pending operations,
or an open confirmation dialog and can never execute a replacement.
