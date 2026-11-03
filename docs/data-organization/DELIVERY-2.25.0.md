# 2.25.0 AI Data Organization Preview — Delivery

## Implemented

Existing Worldbuilding Studio now contains Data Organization. Authors may design categories/fields manually or request a structured AI proposal, edit typed numeric tables, preview destinations and explicitly save pending Bible reference entries. Comparison tables read original fields rather than creating another editable truth store. Character/plot material remains supplementary; canonical domain schemas are reused, not redesigned.

Known values, unknowns, units, dates, source quotes, author input and AI suggestions remain distinct. Original entity references are reused without overwrite. Table references participate in existing validation/derived relations and survive actual Data Center restore-as-new. No new dependency or database migration.

## Actual evidence

- LOCAL PASS: 29 related backend checks, including existing WorldStudio regression and real isolated backup/restore. One pre-existing Pydantic fixture serialization warning remains.
- LOCAL PASS: production TypeScript/Vite build; CSV Unicode, quantities, null/zero/false, formula prefix escaping, quote/newline checks.
- BROWSER PASS: headless Edge against isolated synthetic workspace. Workbench entry, continuous decimal typing and retained focus, unit/text editing, saved proposal, no-write preview, explicit pending creation, reload/reopen, original-entity navigation and existing-editor save. A subsequent comparison read returned the changed value 321.5. Viewports 1440 and 800 had no page horizontal overflow.
- REAL AI PASS: existing Codex login / SDK 0.160.1; observed model gpt-6-astra. A small synthetic country input returned one template and one record in 50.95 seconds. Population 500 and copper stock 12 tons were source-quoted; missing military budget stayed null/UNKNOWN. No receipt/adoption, no real manuscript sent and no third-party paid API.
- An earlier real-AI response incorrectly encoded a quantity as a scalar. Validation rejected it without writing entries. Explicit wire-format guidance was added; a single post-fix attempt passed. This is a useful guard, not proof every future model output will validate.
- PACKAGED WINDOWS STARTUP PASS: release EXE opened a visible owned WebView2 window, loaded the demo shelf, served the frozen organization API, created a synthetic draft and exited via the existing bridge with code 0 and clean-stop log.

## Not verified / limits

Native mouse/keyboard, physical Chinese IME, system DPI, long-term use and real third-party API behavior were not tested. Browser interactions are not native interaction acceptance. No claim of literary or extraction accuracy follows schema/quote checks. One small Codex generation does not establish a latency benchmark.

The UI supports two new locales (zh-CN/en), existing fallback elsewhere. No table formula execution or automatic Canon adoption. Limits: 8 templates, 24 records, 16 columns and 200 rows per table. Plan snapshots are read-only after apply; edit original entries for live values. Existing template upgrade/adoption remains a separate author action. Do not edit new table schemas with an old application version.

## Delivery and publication

Version: 2.25.0 AI Data Organization Preview. Old local and public releases retained. New EXE, Windows Preview ZIP and curated Developer ZIP are local artifacts. This round does not commit, push or publish. The historical public Allowlist remains intact; the new module has a separate review queue for a future refreshed audit.
