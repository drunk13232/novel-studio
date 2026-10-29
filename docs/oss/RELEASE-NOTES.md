# Novel Studio 2.24.9 Writing Reliability Preview

**Preview / PARTIAL · Windows x64 · Apache-2.0 · Copyright 2026 drunk13232**

## 下载 / Downloads

- `NovelStudio-2.24.9-Preview-Setup.exe`: per-user Windows installer. Keep application installation and your existing data directory separate; back up your work before updating. No Python installation is required.
- `NovelStudio-2.24.9-Windows-Preview.zip`: portable Preview. Extract the entire folder including `_internal`; its default entry offers the original public demo. Select your own workspace/data explicitly for personal writing.
- `SHA256SUMS.txt`: verify both binary assets locally. Windows x64 and Microsoft WebView2 Runtime are required. The executable is unsigned; antivirus reputation/false-positive warnings are possible. Do not disable protection indiscriminately; verify provenance and hashes.
- Source is in the repository/tag. Private Developer ZIP, personal launchers, trial manuscripts, logs, user databases, credentials and character assets are not release assets.

## 本次更新 / Changes since 2.24.4

- 2.24.5–2.24.7: candidate/read-conflict recovery and chapter-work editing retain newer unsaved input while older save receipts arrive. Save/recovery remains bound to its original chapter; existing close/leave and author-adoption protection remain authoritative.
- 2.24.8: existing Director/Writer workflow is available through scoped MCP drafting, reading, staging, stop and resume. Candidate references carry real source/version checks and require context approval.
- 2.24.9: paired Codex SDK/CLI runtime, explicit prose/target/adoption states, fixed-step checkpoints, local budget preflight, scene intent/interfaces, exact-repeat review pointers and version-bound whole-book candidate checks. No new Agent framework, database migration or model-provider fallback.
- 字数目标不等于文学质量；模型完成不等于作者采用。所有候选仍需作者审核，正式作品与 Canon 不会自动变化。

## Verification / 验证边界

- Local: 72 related backend tests and production frontend build passed; 11 isolated headless-browser interactions passed.
- Real Codex/MCP: controlled original-fiction candidate generation reached 102,115 Han characters across 31 explicitly selected chapter candidates. Author-directed orchestration; not one autonomous model turn, not author-adopted prose and not a complete literary review.
- A failed task retained its 486-character prefix and continued only its remaining two steps, reaching 2,044 / 2,400 Han characters; the shortfall remains visible.
- One same-base-model review of a 5,214-character candidate verified 10 of 12 quotes and flagged the other two. This is not independent model consensus.
- Existing Data Center backup restored all 31 candidate chapters and pinned versions into a separate project. Frozen MCP/WASI entry points, bundled CLI 0.160.1, package integrity and silent isolated install/uninstall passed.
- Exact-public-commit hosted Windows CI is an additional release gate. Its actual result is linked on the published Release; older CI results are not substituted.
- Native WebView2 clicks, physical Chinese IME, system DPI, installed SAPI voices and long-duration personal use were not reaccepted this round. Browser, mock, worker and silent-install results do not stand in for these gates.

## Known limits / 已知限制

Generation may fall short of chapter targets or repeat/reinterpret prose; counters and review pointers expose this, without automatic padding, deletion or relaxed thresholds. Recorded four-step generation tasks took approximately 90.68–176.99 seconds; there is no same-condition speedup claim. SDK-paired runtime resources increase the portable ZIP by approximately 142.49 MiB versus 2.24.8. There is no new native-GUI memory/startup benchmark. External AI/ComfyUI/voice/Skills features still require their respective setup. No third-party paid AI service is enabled by installing this update.

User works retain their own rights. Apache-2.0 covers the original software; third-party notices remain applicable. Use GitHub private vulnerability reporting for security issues; do not attach private fiction, credentials or unredacted logs to public issues.
