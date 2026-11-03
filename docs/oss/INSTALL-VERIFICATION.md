# 2.25.2 Preview publication verification

The new public source is exported from the reviewed Allowlist; the private Developer ZIP is not a public asset. Local 2.25.2 evidence covers 37 scoped backend checks and 26 real headless-browser scenarios, plus packaged Windows window/API/startup/clean-exit verification. It does not mean a fresh standalone dependency installation or the entire suite was rerun locally for this publication.

The exact public commit must be checked by the existing Windows CI: isolated Python/npm dependencies, pip check, the documented backend suite and TypeScript/Vite production build. Consult Actions for actual counts and completion; historical passing runs are not evidence for this commit. An installer is built from the verified immutable payload and independently checked using isolated silent NOINTEGRATION install/uninstall. Native installer GUI, physical IME/DPI, external Skills/voices and cloud AI are separate gates.

## Historical procedure and evidence

# Independent install verification — 2.24.9 Preview

The source ZIP and artifact-side VERIFICATION.json identify the precise candidate and current execution results. Do not use the older 2.22.2/2.23.x installation records as passing evidence for this candidate.

Procedure: extract the allowlisted source into a new isolated folder with no copied `.venv` or `node_modules`; create CPython 3.12 venv; install both requirements files over verified HTTPS; run pip check; npm ci from the lockfile; verify pinned CPython WASI resources; run the documented backend suite and frontend TypeScript/Vite production build; build PyInstaller and a universal NSIS installer. Dependency download caches may be used with normal integrity checks, never disabled TLS. A compiler installed separately is recorded as a build tool, not a hidden runtime dependency.

All application launch/test data and CODEX_HOME are isolated. No real novel or cloud inference is needed. Native GUI, physical IME/DPI, installed SAPI voices, optional external Skills and actual remote AI remain distinct evidence gates. Browser/headless checks or silent installer checks never stand in for native desktop interaction.

The documented CI command explicitly deselects five separately installed Screenwriting integration tests and the local SAPI synthesis case. Other failures remain failures. Opt-in print/symlink/platform tests may report SKIPPED with reasons; report actual counts. Two further integration tests read the optional, separately installed `novel-writing` Skill and its two writing references; when absent they explicitly report SKIPPED and do not claim real Skill validation. All original test assertions still run when those resources are installed. No missing Skill is replaced by a fabricated resource.

Hosted Windows CI is now active at [GitHub Actions](https://github.com/drunk13232/novel-studio/actions/workflows/ci.yml). Consult the run for the exact source commit and actual result; a previous failed run or a local PASS is not evidence of the current hosted result. Windows checkouts preserve audited bytes with `.gitattributes`, and per-run test paths are initialized inside a runner step.

If any clean install/build fails, preserve the error and distinguish network failure from dependency/project failure. A partially passing suite is not a full PASS.

The 2.24.9 local delivery ran 72 related tests, 11 isolated headless-browser checks, frozen-worker integrity checks, and a silent isolated installer/backup round trip. These are not a claim that the previous full suite ran unchanged on this new public snapshot. The exact public commit must pass the hosted Windows workflow above before its Preview Release is published. Real Codex evidence is limited to the controlled original-fiction trial described in the version guide; no user manuscripts are distributed.


## 2.24.10 publication scope

The Director UI patch is checked with the retained development dependencies and isolated real-service browser fixtures. A fresh public-candidate installation is not repeated in this patch. Exact-commit GitHub Windows CI installs its own Python/npm dependencies and runs its configured backend/build checks; consult that run for its actual status. Local packaging and isolated silent installation are recorded separately in the release receipt, and do not constitute native GUI/IME/DPI acceptance.
