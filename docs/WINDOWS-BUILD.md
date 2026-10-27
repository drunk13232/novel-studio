# Windows build / Windows 构建

Current candidate: **2.24.0 Custom Workflows Preview**. Use the existing PyInstaller + pywebview/WebView2 container; no Electron or additional resident service.

Install independent dependencies and build the frontend as described in [DEVELOPMENT.md](DEVELOPMENT.md). From the source root:

```powershell
& ./web/backend/.venv/Scripts/python.exe -m pip install -r web/backend/requirements.txt -r desktop/requirements.txt
& ./web/backend/.venv/Scripts/python.exe -m pip check
./desktop/build.ps1 -Preview
```

The script verifies the locked CPython WASI runtime, collects dependency notices, executes `npm.cmd run build` (PDF resources + TypeScript + Vite), freezes the backend and writes the new versioned EXE/ZIP/source artifacts. It refuses an existing release application directory, preserving rollback versions. Do not delete old releases to make a rerun pass; extract the public candidate into a different independent directory instead.

Output uses `release/v<desktop/version.json version>/NovelStudio/` and the Windows Preview ZIP. Keep `_internal` beside the EXE; a standalone copied EXE is incomplete. Windows x64 and WebView2 Runtime are required. No WebView2 installer, personal Codex login/CLI, Pandoc, ComfyUI or private character model is bundled. External feature requirements remain explicit.

The public locator is `desktop/data-location.public.json`. Do not copy a developer's data-location.json or real application data. Use `--demo --demo-data <isolated-test-data>` for owned candidate runtime checks. Never open real author works for build acceptance.

There is no signed or automated public-release claim. See [release-page notes](oss/RELEASE-PAGE-NOTES.md) for unsigned/PyInstaller antivirus handling without disabling protection. Fonts, PDF resources, CPython/WASI and third-party notices have separate terms. Original project software is Apache-2.0, Copyright 2026 drunk13232; preserve LICENSE, NOTICE and COPYRIGHT.

The CI workflow validates backend tests and frontend compilation; it does not run this complete desktop packaging/native-UI path. Current independent installation/build evidence and any missing gates are in [INSTALL-VERIFICATION.md](oss/INSTALL-VERIFICATION.md). Historical results cannot be substituted for this candidate's results.

A standard per-user installation wizard is also available; see [desktop/INSTALLER.md](../desktop/INSTALLER.md). It wraps the same manifest-verified application without changing the sealed portable ZIPs. Personal default-data builds are separate from public-source clearance.


## Public installer candidate

Build from a clean extracted public source snapshot, never the private parent Git history. Use a verified official NSIS 3.13 compiler with `desktop/build_installer.py --makensis <path>/makensis.exe`; omit `--data-default` for public builds. The default is the current user's LocalAppData folder. The Windows payload includes root LICENSE, NOTICE, COPYRIGHT and third-party notices. Keep Preview status and record native GUI, IME, cloud AI and hosted CI gates separately.
