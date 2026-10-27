# Novel Studio 2.14 — Long-Form Narrative Intelligence Preview

This release extends the existing Writer Context, ReviewCenter, literary
evaluation, author notebook, revision todos and guarded Diff. It does not add a
second story database, score engine, Agent service or automatic State writer.

## Use

Open **文学评审 → 长篇叙事记忆** to query an already committed chapter boundary,
optional explicitly zoned story time, a character and up to four exact-text
queries. The inspector is AUTHOR-only. Its raw response must not be forwarded to
Writer: character knowledge still enters through the existing approved Context
Builder, where secrets and unapproved future material are filtered again.

Open **文学评审 → AI 总编辑** for chapter, selected chapters, a volume's range or
the complete available manuscript. Describe the author's intent and choose
editorial dimensions and up to four existing methods. Preview the exact scope,
model and estimated call count, freeze the record, then run a bounded batch.
Incomplete reading or synthesis remains `PARTIAL_COVERAGE`. A batch never
automatically approves a revision or a State commit.

Short chapters share bounded full-text units (at most six distinct chapters and
12,000 text characters). Long chapters are split using the existing paragraph
boundaries. The existing dependency DAG and checkpoints track every supplied
character; synthesis consumes source-quoted reading observations and editorial
findings. Coverage means the target text was processed by successful requests,
not that an AI has perfectly understood or exhaustively verified the work.

An edit letter declares its lens, optional priorities, evidence, alternative
readings, revision choices and costs. It produces no literary total score.
Ordinary literary scoring remains available separately. A selected finding can
become the existing revision todo or a local Diff workflow; rejection does not
modify the manuscript. Saving an editorial preset uses project preferences and
never restores a frozen scope or authorization automatically.

The local style observation button reuses existing statistics in bounded batches.
Mean sentence length, dialogue proportion and exact repeated sentences are
descriptive, not judgments of quality or reliable speaker attribution. Exact
cross-chapter repetition samples the first 160 bounded sentences per chapter;
this is disclosed and is not a complete semantic repetition detector.

## Temporal evidence and uncertainty

Runtime history is a disposable projection of the existing committed Chapter
Ledger and original Proposed records. Proposal hashes, chapter/body bindings,
source revisions and inverse-patch lineage are verified. Explicit chapter-end
time anchors are conservative end-state boundaries, not invented exact times of
individual actions. Narrative disclosure order and story time are independent.
Attributed speech, beliefs, flashbacks and author interpretations are not
automatically objective facts. Plans do not grant character knowledge.

Superseded runtime fields can be reconstructed when their original evidence
chain exists. Missing history, changed evidence or mismatched patches produces
an unknown historical view; today's profile is not used to fill past gaps. Old
projects without complete receipts remain readable and explicitly retain the
limitations of their legacy views. No migration or automatic repair runs.

Changed manuscript files invalidate derived facts and review records. In-memory
bounded caches reuse unchanged proposal/source hashes. Existing SQLite FTS5
refreshes changed files only and applies the numeric chapter boundary before
ranking. Queries never load all private books. Dependencies are checked with
existing NetworkX algorithms only when the author declared strict precedence;
ordinary associations and social feedback are not causal proof.

## Developer reproduction

From the repository root with the existing Python environment:

```powershell
python scripts/long_form_fixture.py --output docs/long-form/private-checks/my-fixture --chapters 40
```

This explicitly creates an isolated original-fiction fixture from the public
preview template. Synthetic author records test retrieval and temporal behavior;
they are not real AI semantic commit validation. Existing personal projects are
never used. The output must be new; `--resume` only accepts a recorded fixture.

Add `--run-ai` to opt in to the existing Codex login for this original fixture.
`--calls 2` bounds each batch; a run uses at most four explicit batches.
`--resume --run-ai` resumes saved successful units. `--new-evaluation` preserves
the old job and creates a separate version after a method change. No third-party
paid Provider is selected automatically. Unknown usage/cost remains unknown.
Keep all generated logs, texts and task records in `private-checks`; the Developer
package includes this utility and tests, not their outputs.

## Compatibility and limitations

No new dependency or database schema is required. Existing JSON review records
remain readable; new optional editor fields and metadata do not alter Canon or
manuscript formats. Old editorial method versions are preserved but cannot be
mixed silently into a new run. Chinese and English cover the new interface;
other locales use the existing explicit fallback policy.

This is a Preview. AI interpretations can miss a contradiction or misread a
literary device; mathematical or deterministic claims need their own evidence.
Millions of words, physical IME/DPI combinations and remote Provider behavior
require separate validation. Actual test coverage and remaining issues belong
to the delivery report, not a blanket reliability claim.

## Technical references

- [SQLite FTS5 query and ranking documentation](https://www.sqlite.org/fts5.html)
- [NetworkX directed acyclic graph algorithms](https://networkx.org/documentation/stable/reference/algorithms/dag.html)

The current installed implementations are reused. Third-party notices and the
project's pending license decision are unchanged. Private experiments, novels,
documents, API keys and character resources are excluded from public packages.
