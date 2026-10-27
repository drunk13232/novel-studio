# Rules, evidence and memory adapter contract

This extends the existing Bible entity, custom field and experiment contracts. It does not establish another Canon authority.

## Rule templates

The built-in category is `world_rule`. A copied custom category remains a rule when its saved template contains the stable `rule_strength` and `rule_scope` fields. Existing JSON template interchange and compatibility checks apply.

Relevant entity fields are `name`, `summary`, `valid_from`, `valid_to`, `source_references`, `writer_view`, `writer_public`, `writer_known_by`, `status`, `version`, and `locked_fields`. Structured rule values stay in `fields`: `rule_kind`, `rule_strength`, `rule_scope`, `scope_ids`, `conditions`, `exceptions`, `confidence`, `calendar`, `assumptions`, `formal_model`.

`formal_model` is a JSON string with only `solver`, `inputs`, `constraints`, `outputs`, `acceptance_rules`, `assumptions`, and `limitations`. It is validated with the existing World Logic Lab schema and restricted expression grammar. It is never evaluated as Python. See `web/backend/app/world_logic/resources/world-experiment-1.0.json` for the underlying portable experiment contract.

An example of a finite, explicitly fictional author assumption:

```json
{"solver":"z3","inputs":[{"id":"energy","name":"Available energy","value":100,"unit":"joule"},{"id":"cost","name":"Declared cost","value":20,"unit":"joule"}],"constraints":[{"id":"energy_cost","name":"Pay the declared cost","expression":"energy >= cost","meaning":"Conditional on the author's numerical model"}],"acceptance_rules":[{"id":"cost_possible","name":"Energy covers cost","type":"HARD","expression":"energy >= cost","basis":"Author-confirmed fictional inputs"}]}
```

Eight selected rule cards share inputs only when their explicit definitions are identical. Ambiguous variable definitions fail instead of being merged. Constraints are prefixed and mapped to source entity IDs. Soft rules are qualitative, unavailable premises remain unaccepted assumptions, and an empty applicable model is inconclusive.

## Story-time periods

`Entity.periods` retains the original fields and adds optional `calendar`, `confirmed`, `facts`, `writer_view`, and `source_references`. `facts` contains scalar author records, not arbitrary executable objects. Missing time or overlapping records is unknown/conflicting. Editing timestamps never establish story chronology.

`iso` accepts precise timezone-bearing instants or date-only intervals of matching precision. Custom coordinates use finite numeric values and an explicit calendar name. No automatic conversions, rounding, invented dates, or current-state backfill occur.

## Evidence

Existing reference notes add a `citation` snapshot with document SHA-256, unit SHA-256, source metadata, format and purpose. `location.locator` records the format-specific coordinate, alongside exact character offsets where available. Legacy notes without a receipt remain UNKNOWN.

New entity source references use `kind=reference_note` plus a current-project note ID, or `kind=manuscript` plus a validated manuscript path, revision and unique quote. Attached reference notes also retain the existing note-to-entity link. Actual sources are revalidated when binding and when used for AI design.

No HTTP crawler, external Schema resolver, credential reader or arbitrary path API is introduced.

## Query and impact

`/api/projects/{p}/world-model` is a coordination API over Bible, References, Knowledge.lookup and WorldLogic. The existing SQLite FTS is reused. Results are AUTHOR-only; only separately approved Writer summaries cross the Writer boundary.

`RULE_REQUIRES`, `RULE_ASSOCIATED`, `RULE_CONDITIONAL`, `RULE_AI_POSSIBLE` and `RULE_OVERRIDES` use the existing relation file and permission path. Impact traversal follows only confirmed `RULE_REQUIRES` edges. Explicit precedence cycles are unresolved. Ordinary cycles are not automatically rejected as causal contradictions.

## Dependencies and research

No new packages were installed. JSON/CSV use the [Python standard library](https://docs.python.org/3/library/json.html), EPUB/HTML reuse zipfile and the installed lxml with [external resource protections](https://lxml.de/FAQ.html#how-do-i-use-lxml-safely-as-a-web-service-endpoint), YAML reuses SafeLoader, and dependency paths use [NetworkX descendants](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.descendants.html). Existing pypdf, python-docx, JSON Schema, Pydantic, Z3, SymPy, Pint, OR-Tools, i18next and PyInstaller remain authoritative.

All imported data is untrusted. Parsing is size-bounded in the existing isolated worker. Public candidates exclude actual rules, private reference originals, author histories, test fixtures and credentials. The overall project license remains undecided by the author; this document grants no new asset rights.
