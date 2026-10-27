# Development and isolated tests / 开发与隔离测试

Current candidate: 2.24.0 Preview. Use Windows x64, CPython 3.12 and Node.js 24 LTS/npm (CI uses these major versions). No Codex-bundled Python or existing development environment is required. A base interpreter may be installed normally; do not copy a developer venv/node_modules.

From the source root / 源码根目录：

```powershell
python -m venv web/backend/.venv
& ./web/backend/.venv/Scripts/python.exe -m pip install -r web/backend/requirements.txt -r desktop/requirements.txt
& ./web/backend/.venv/Scripts/python.exe -m pip check
Push-Location web/frontend
npm.cmd ci
npm.cmd run build
Pop-Location
& ./web/backend/.venv/Scripts/python.exe desktop/fetch_python_runtime.py
```

The lockfile/integrity and HTTPS checks remain enabled. The pinned CPython WASI artifact has a separate SHA-256 lock; an existing copied runtime must also verify. Installation needs network access; manual writing and local resources do not require cloud AI at runtime. Never use `--trusted-host`, disable TLS or borrow hidden dependencies to make a failure look successful. See [current independent verification](oss/INSTALL-VERIFICATION.md).

## Isolated backend

Use the original demo, not real works. The following environment is per process and must not modify global Codex settings:

```powershell
$taskSource = (Get-Location).Path
$taskScratch = Join-Path $env:TEMP ('NovelStudio-dev-' + [guid]::NewGuid().ToString('N'))
$taskWorkspace = Join-Path $taskScratch 'workspace'
$taskData = Join-Path $taskScratch 'application-data'
New-Item -ItemType Directory -Path $taskScratch | Out-Null
Copy-Item -LiteralPath (Join-Path $taskSource 'desktop/preview-template') -Destination $taskWorkspace -Recurse
$env:NOVEL_WORKSPACE = $taskWorkspace
$env:NOVEL_STUDIO_HOME = $taskData
$env:NOVEL_STUDIO_DATA = Join-Path $taskData 'workspaces'
$env:CODEX_HOME = Join-Path $taskScratch 'empty-codex-test-home'
$env:NOVEL_STATIC_DIR = Join-Path $taskSource 'web/frontend/dist'
$env:NOVEL_DEMO = '1'
$env:PYTHONPATH = Join-Path $taskSource 'web/backend'
& ./web/backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open the loopback page; a second terminal may run `npm.cmd run dev` in web/frontend (proxy: 8765). Do not broaden the listener or bypass local session protection.

## Tests and CI

With the isolated environment above (stop its backend if using the same temporary files), run:

```powershell
& ./web/backend/.venv/Scripts/python.exe -m pytest web/backend/tests -q -ra
```

The suite uses temporary fixtures and mock model adapters; it is not real cloud-AI acceptance. Some tests inspect local Windows SAPI or junction capability. Print integration requires explicit `NOVEL_VERIFY_PRINT=1` plus a supported local browser. The GitHub workflow uses the same dependencies and frontend build, but explicitly deselects only `real_local_sapi_through_application_audio_routes` because hosted runner voice/COM support is not guaranteed. It also deselects five exact character/planning/project integration cases that require separately installed Screenwriting Skills; their filenames are listed explicitly in the workflow, not hidden behind a broad file exclusion. No external plugin cache is copied or silently downloaded. Other explicit opt-in tests report SKIPPED, not PASS. Other failures are not waived. Native IME, DPI, microphone, real Codex and paid providers are not CI gates. Cloud workflow execution remains UNVERIFIED until the workflow is actually run after owner-approved publication.

No personal Codex login, API keys or paid service is needed for CI. Do not silently enable live services to fix a failing fixture. Save exact collection/install failures and test totals. The frontend command runs PDF resource verification, TypeScript and Vite. Build success does not prove native UI interaction.

## Structure and privacy

`web/frontend/src`: React; `web/backend/app`: services/API; `desktop`: launcher/build; `scripts`: existing workflow helpers; `python`: controlled application API; `engine/templates`, `templates`, `schemas`: initialization; `.novelforge`: attributed upstream MIT content.

Public source paths/hashes live in docs/oss/PUBLIC-ALLOWLIST.json. The only public test override is explicitly recorded under docs/oss/public-overrides; it substitutes an author-approved synthetic name without modifying the original private checkout's test. See PREPUBLICATION.md and CANDIDATE-AUDIT.md.

User data, `.git`, credentials, runtime logs, venv, node_modules and private model assets must stay out of source candidates. `.env.example` documents variables only; the app does not automatically load dotenv. Secrets belong in the application's credential settings.


## Public installer candidate

Build from a clean extracted public source snapshot, never the private parent Git history. Use a verified official NSIS 3.13 compiler with `desktop/build_installer.py --makensis <path>/makensis.exe`; omit `--data-default` for public builds. The default is the current user's LocalAppData folder. The Windows payload includes root LICENSE, NOTICE, COPYRIGHT and third-party notices. Keep Preview status and record native GUI, IME, cloud AI and hosted CI gates separately.
