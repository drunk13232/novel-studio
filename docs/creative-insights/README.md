# Narrative curves and virtual reader profiles

This module extends the existing Plot Matrix and Literary Review Center. It does
not create a second AI engine, reader survey database, literary scoring system,
or manuscript/Canon authority. Frontend: `CreativeInsights`; backend integration:
`CreativeInsights(tools, plot_matrix, literary_review)` and `routes(service)`.

## Local emotion and tension curves

Analysis starts only when the author selects chapters and clicks **Analyze
selected text locally**. Opening the page does not start a model, connect to
Codex, or read every manuscript body. The existing Book Center supplies stable
chapter order and IDs. Final takes precedence when Final and draft coexist;
otherwise the available selected manuscript/draft is used. Anthologies require
opening a member project; a short continuous manuscript remains a single item.

The current method is `lexical-dialogue-signals-1`, an explicitly rough local
heuristic, not a semantic sentiment classifier or a quality score:

- `density = 1000 / max(100, number_of_characters)`.
- `tension = clamp(0,10, conflict_markers*density*0.9 + dialogue_ratio*2 - calm_markers*density*0.25)`.
- `tone = 5 + 5*(positive_markers-negative_markers)/(positive_markers+negative_markers+2)`;
  tone is unknown when neither positive nor negative markers are found.
- Dialogue ratio reuses the existing quoted-span measurement and counts Han
  characters within quotes divided by total Han characters. It is a text
  measurement, not proof of a conflict, emotion, pacing problem or writing time.
- No verifiable local signal means `null`, not zero. Unknown points break curves
  and sustained-low-tension spans. A low-tension span requires at least the
  configured number of consecutive known points **strictly** below the threshold.
  Quiet chapters are not automatically defects.

Character overlays use small contexts around actual name mentions (up to 20
mentions per chapter), selecting the strongest available local signal. They do
not establish a character's inner state. Plotline overlays use only existing
`TEXT_OBSERVATION` milestones whose path, revision and exact quote still match;
`PLANNED` milestones remain unknown and do not become story facts.

Author overrides (0–10 values and notes) are stored separately from measurements.
They affect display for the same source revision, never the original local score
or manuscript. Source or relevant overlay changes mark annotations stale; they are retained
and can be reviewed or cleared. Cache keys are per series, so adding a character
or plot overlay does not invalidate an unchanged book line or its author notes.
Unwritten plans cannot receive a measured author score. Coverage explicitly
counts known and unknown book-line points. Cached unchanged chapters are not reread. Inputs
are bounded to 1,000 chapter IDs, 6,000 points, 200,000 characters per analyzed
chapter, 20,000,000 newly read characters and 45 seconds per run. A limit leaves
remaining chapters unprocessed/unknown and the run `INCONCLUSIVE`; no silent
truncation is called complete. The time limit is cooperative between bounded
file reads, not an operating-system hard real-time deadline.

## Two distinct evidence limitations

1. Curve excerpts are actual exact manuscript substrings with full-document
   UTF-16 positions and revision hashes. They prove where a word/dialogue signal
   occurred, not the literary interpretation of that passage. An exact name
   match is not coreference resolution; plot plans are never textual evidence.
2. Reader quotations are checked with the existing Literary Review Center's
   locator. A persona reaction/finding is withheld when any required quote lacks
   a verified source location. Summaries also require `summary_evidence`; missing
   summary support displays an evidence-insufficient message. New reports are
   filtered before persistence. Legacy files remain unchanged but their API/UI
   view receives the same filter, without renumbering issue decision IDs. The UI
   independently rejects unverified reaction anchors. Changed source versions
   disable historical evidence navigation. Verifying a quotation does not prove
   that a subjective simulated reaction is correct or representative of readers.

## Reader profiles, consent and model routing

Profiles are project-local, persistent author assumptions: name, optional age
range, preferences, possible abandonment triggers, payment willingness and one
existing reader perspective. Payment and age are not demographic or market facts.
Up to four profiles may be compared. Removing a profile retains frozen snapshots
in old reports. Profiles and previous results remain usable without an AI service.

Preparing a panel reads only explicitly selected public manuscript paths from the
current project; it does not include Canon, hidden truth, character cards, private
references, style archives or other novels. The preview freezes exact paths,
source revisions, profile snapshots, the selected model/configuration and request
budget. Confirmation approves this exact manifest but does not start inference.
The author then runs one reading or explicitly enables sequential execution of
this approved batch. There is no provider fallback and unavailable models do not
automatically switch to Codex. Model configuration or manuscript changes require
a new preview before another request can start.

The existing Review Center runs **independent chunks of at most eight consecutive
chapters and 95,000 characters**. Non-contiguous selections, gaps and unreadable
chapters split chunks. A single oversized chapter is blocked, not silently
truncated. Whole-book selection means coverage across explicitly listed chunks;
it does **not** mean a reader persona remembers earlier chunks, read omitted
chapters or performed a full-book memory synthesis. Results from the same model
are not independent human consensus. Per-profile reactions, possible abandonment
points and moving passages remain model opinions with uncertainty and exact
quote verification; missing reactions are not invented.

Request limits include retries. Failed/cancelled/interrupted cells never retry
automatically; an explicit retry only makes the cell eligible and still needs an
explicit run. Closing this pane stops automatic advancement; an already-started
read-only task may finish through the existing TaskManager and can be reopened.
Budget estimates use selected text JSON, actual selected technique/profile UTF-8
byte upper estimates and a small request framing allowance, not a provider's
model tokenizer. Estimated cost is based on user-entered model prices and output
reserves, never an official invoice or server spending limit. Unknown prices are
shown as unknown. Exact final token use also depends on the selected adapter and
provider. Model-specific context limits can reject a request rather than truncate
it or expand authorized data.

Reports remain under the existing `reviews/literary` history. Their reader
manifest lives in `reviews/literary/reader-panels`. Local curve/annotation and
profile files are under `metadata/studio`; none writes prose, Final, Canon,
State, Knowledge or Timeline. Simulated reader output is not automatically passed
to Writer context or converted into accepted story facts.

## API integration

Base: `/api/projects/{project}/creative-insights`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/curve` | Metadata/cache view; no inference |
| POST | `/curve/analyze` | Explicit local bounded analysis |
| PUT | `/curve/override` | Revision-bound author judgment or clear |
| PUT | `/curve/settings` | Etag-protected low-tension reminder settings |
| GET | `/readers` | Current project profiles and up to 100 recent panels |
| PUT | `/readers/personas` | Etag-protected profile create/update |
| DELETE | `/readers/personas/{id}` | Explicit confirmed profile removal |
| POST | `/readers/prepare` | Freeze selected text/model/profile/budget preview |
| GET | `/readers/panels/{id}?chunk=0` | Saved batch and same-chunk persona comparison |
| POST | `/readers/panels/{id}/approve` | Confirm etag + exact preview hash; no AI |
| POST | `/readers/panels/{id}/next` | One explicitly authorized existing reader task |
| POST | `/readers/panels/{id}/retry` | Make one failed/cancelled cell eligible, within budget |

Typed bodies are in `app/creative/insight_models.py`; all definitions reject extra
fields. Existing project ownership, writable checks, workspace safe paths,
metadata etags, checkpoint snapshots, TaskManager and AI consent mechanisms are
reused. No arbitrary scripts, SQL, shell, new external services or dependencies
are introduced. Recharts is lazy-loaded; unknown points are not connected and
chart animation is disabled. Scope lists page at 50 chapters; full tables of
individual graph points are not rendered.

## Verification and limitations

`web/backend/tests/test_creative_insights.py` executes deterministic calculations
and real temporary-file persistence. Its capture adapter is explicitly **MOCK**
and validates the actual Review Center callback/schema/evidence path; it is not
a real model quality test. Existing public-reader secret isolation and contiguous
scope regressions were also checked. `web/frontend/scripts/check-creative-insights.mjs`
uses real React and Radix dialogs with in-memory mocked transport, task, chart and
model-picker boundaries. It is **LOCAL_COMPONENT**, not browser/desktop or visual
acceptance. No actual AI call, remote billing, GUI control or user novel access was
performed in this implementation pass. Real-model response quality and native
Windows interaction remain unverified. The 500-chapter isolated service sample
and timing details belong in ignored `private-checks`, not a public success claim
about desktop frame rate or memory.

The focused follow-up is documented in [DELIVERY-2.22.2.md](DELIVERY-2.22.2.md).
The actual production chart can be exercised with `node web/frontend/scripts/check-insight-chart.mjs --output docs/creative-insights/private-checks/NEW-CHART-RUN`.
It uses installed Edge headlessly, synthetic inputs, no model, and no native desktop interaction.
The service sample accepts `--output` and refuses to overwrite earlier evidence.
