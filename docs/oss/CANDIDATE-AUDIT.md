# Public candidate audit method — 2.24.9

The current allowlist is refreshed against 2.24.9, not the historical 2.22.2 RC2. Export excludes all parent Git objects; this does not declare the private parent history safe to publish. Do not push it.

Checks: allowlist bytes/SHA-256, export CRC, prohibited filenames/directories, local user paths/private project identifiers, credential-shaped strings and Gitleaks 8.30.1. Raw findings are retained locally with redacted summaries; scans do not prove absence of secrets. Binary/visual provenance and independent build verification are separate gates. The matching artifact-side AUDIT.md/VERIFICATION.json records actual results, exact hashes and unresolved items.

Prior explicit owner dispositions are retained narrowly: exclude the old private-ID script; public synthetic fixture names differ from the original local test; CPython upstream documentation sample paths, two isolated fake-key fixtures and five public stdlib SHA-256 hits are reviewed false positives. New hits are not automatically waived. User data, global Codex settings, runtime logs and private assets do not enter the allowlist. Historic pending-license drafts and private audit records are omitted.

The owner selected Apache-2.0 and drunk13232 attribution on 2026-10-27. Third-party notices/source obligations remain. No repository publication, settings change or application submission is authorized by an export.

For 2.24.9, the independent source snapshot excludes every long-form trial, model transcript, private report, personal launcher and global user configuration. New Codex runtime LICENSE/NOTICE and bundled component notices are explicitly included. Publication receipts and current scan dispositions are retained separately; old audit results do not validate new bytes.
