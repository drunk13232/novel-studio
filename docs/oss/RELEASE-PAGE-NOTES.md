# Release page safety notes — 2.24.0 Preview draft

- Target: Windows x64 with Microsoft WebView2 Runtime. Install the complete package, keep user data separate and retain backups/old versions.
- Setup.exe and the portable app are currently unsigned. PyInstaller executables may trigger antivirus heuristics. A warning can also indicate a genuine problem: verify the published hash/source and investigate; never instruct users to disable protection or assume every warning is false.
- Manual writing works without AI. Codex login, API credentials, local model services, ComfyUI, Pandoc, browser print engines, installed Windows voices and private dynamic character assets are optional feature-specific dependencies, not promised bundled services.
- Native IME, all DPI combinations, external model quality and prolonged use remain Preview limitations. Actual checks are recorded per artifact, never inferred from compilation alone.
- Never attach private novels, API keys, raw configuration, databases or unsanitized logs to public Issues.
- Security channel selected: GitHub private vulnerability reporting at `drunk13232/novel-studio`. It still needs owner enablement/verification when the repository is created. If the private form is unavailable, do not disclose vulnerabilities publicly.
- Original software: Apache-2.0; Copyright 2026 drunk13232. Preserve LICENSE, NOTICE, COPYRIGHT and all third-party notices. This does not license users' creative works.
- These notes are for owner review; this task does not publish a repository or Release.
