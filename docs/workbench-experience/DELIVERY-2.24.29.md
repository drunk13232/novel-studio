# Novel Studio 2.24.29 — Daily Workflow Preview

Local delivery, Preview / PARTIAL. No publication, Git commit or shortcut change.

## Implemented

- Shared AI controls: selection and review use resolved immutable request snapshots, Director waits for the required commander/executor controls, and receipts distinguish requested/observed models and local checks. Unsupported parameters still use existing validation and capability rules.
- Chapter work: route pending to-dos/revisions/candidates to existing tools, refresh after review decisions, and offer evidence location only when the saved revision and exact UTF-16 excerpt match.
- Storage: reuse existing cache maintenance, show selected logical sizes and a second confirmation, expire stale previews, preserve source backups/verification evidence/old releases, and bind legacy project cleanup to an expiring single-use preview. Duplicate history requires separate explicit consent.
- Windows server cleanup: use the scoped loopback transport adapter documented in SERVER-TRANSPORT.md. No new dependency or global configuration change.

## Evidence before packaging

101 targeted local checks passed; one symbolic-link check is skipped because this account cannot create that fixture. Six additional isolated daily-workflow checks passed. These are local/mock protocol gates, not remote AI acceptance. The official MCP SDK's actual local stdio initialize/list/call round trip is included.

The actual headless editor scenario preserves the full 6,193-character model while only 822 characters are in the viewport DOM. Exact multiline paste, undo and unchanged disk bytes pass. A committed save with an unreadable receipt followed by a denied retry retains the unresolved state and navigation protection. No remote requests or page errors occurred.

## Limits

- Task source preflight is a feature-level scope summary, not a claim that the full Codex SDK internal prompt or exact token budget is visible. Execution still uses the existing source, privacy and cost checks.
- The original natural socket reset is not claimed deterministically reproduced. Controlled cleanup faults are labeled separately.
- Remote AI, native GUI clicks, real Chinese IME, DPI changes and an extended personal writing session are not certified by these checks.
- Final artifact paths, hashes and packaged-process checks are recorded in the release directory's final delivery report after packaging.
