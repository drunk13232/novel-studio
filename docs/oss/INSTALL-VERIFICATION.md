# Independent install verification — 2.24.0 Preview

The source ZIP and artifact-side VERIFICATION.json identify the precise candidate and current execution results. Do not use the older 2.22.2/2.23.x installation records as passing evidence for this candidate.

Procedure: extract the allowlisted source into a new isolated folder with no copied `.venv` or `node_modules`; create CPython 3.12 venv; install both requirements files over verified HTTPS; run pip check; npm ci from the lockfile; verify pinned CPython WASI resources; run the documented backend suite and frontend TypeScript/Vite production build; build PyInstaller and a universal NSIS installer. Dependency download caches may be used with normal integrity checks, never disabled TLS. A compiler installed separately is recorded as a build tool, not a hidden runtime dependency.

All application launch/test data and CODEX_HOME are isolated. No real novel or cloud inference is needed. Native GUI, physical IME/DPI, installed SAPI voices, optional external Skills and actual remote AI remain distinct evidence gates. Browser/headless checks or silent installer checks never stand in for native desktop interaction.

The documented CI command explicitly deselects five separately installed Screenwriting integration tests and the local SAPI synthesis case. Other failures remain failures. Opt-in print/symlink/platform tests may report SKIPPED with reasons; report actual counts. GitHub-hosted CI remains unexecuted until the owner creates and pushes the repository.

If any clean install/build fails, preserve the error and distinguish network failure from dependency/project failure. A partially passing suite is not a full PASS.
