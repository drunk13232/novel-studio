# World template format 1.0

The envelope is JSON data, not executable code:

```json
{
  "format": "novel-studio-world-template",
  "schema_version": "1.0",
  "template": {
    "id": "custom_economic_organization",
    "name": "Economic organization",
    "group": "Custom",
    "description": "Separate resources, authority and unknown conditions.",
    "version": 1,
    "modules": [],
    "fields": [
      {"id":"structure","name":"Decision structure","type":"longtext","options":[],"required":true,"group":"Institutions","help":"Who decides, who pays, and who can object?"},
      {"id":"stock","name":"Reserve","type":"quantity","options":[],"minimum":0,"unit":"kg","group":"Resources"}
    ]
  }
}
```

`value_schema` may be included by the exporter. It is informative; the importer rebuilds the accepted Draft 2020-12 schema from the bounded Category model. It never follows user-supplied remote `$ref` or interprets imported schemas as executable code. No YAML tags, scripts, eval, shell, SQL or dynamic installations are provided.

Stable category IDs use lowercase ASCII letters, digits, `_` and `-`; field IDs use lowercase letters, digits and `_`. Entity instances keep their own stable ID, template version and full snapshot. Template files do not contain entity instances. Restoring a historical template is done by reviewing/copying a compatible version, never destructive replacement of old values.

Field types are `text`, `longtext`, `number`, `quantity`, `calendar`, `date`, `select`, `multiselect`, `boolean`, `image`, `entity`, `entities`, `tags`, `list`, `group`, `rule`, `evidence`. `quantity` is `{"value":12,"unit":"kg"}`; `calendar` is author-defined text. `evidence` is `{"path":"chapters/chapter-1/draft.txt","revision":"<SHA-256>","quote":"<exact excerpt>"}`. Evidence is resolved only in the current work. A rule is plain language until explicitly formalized in the existing World Logic Lab.

Optional metadata: `help`, `group`, `order`, `required`, `primary`, `ai_allowed`, `author_only`, `locked`, `default`, `minimum`, `maximum`, `unit`, `target_types`, `visible_when`, `children`. Conditions match a sibling field's exact value and do not evaluate expressions. Groups support at most three nested levels and 150 fields in total. Enumerations and lists are bounded. Formal adoption checks visible required fields; a draft may preserve unknown inputs.

Nested entity references remain project-scoped. Image references must resolve in the existing asset store. Numeric values must be finite. Unknown is null or empty, never an invented zero. Default values do not automatically populate Canon. AI is barred from author-only or locked fields, including nested groups.

Design batches use the existing TaskManager and typed Result model. Candidate values are serialized JSON values with an explicit epistemic label. Only exact selected-source quotations are verified mechanically. Editing a candidate changes its label to author input but does not make it confirmed Canon. Existing entity revisions require an explicit selected target ID and the existing Bible conflict/lock checks.

HTTP mutations retain the existing cross-process OS lease. Synchronous handlers borrow the exact live stream from trusted request state to avoid acquiring the same Windows lock twice. This stream is never accepted from JSON. Direct callers and background completions acquire their own existing lease. Cancel tokens and stable adoption IDs prevent late writes and duplicate creations; GET reconciliation rereads the saved record under the lease before changing interrupted status.

Source files and tests: `app/library/world_templates.py`, `world_studio.py`, `bible.py`, `tests/test_world_studio.py`. Project backup and restore continue to include the original Bible tree. Public packages must exclude all author design records and test workspaces.
