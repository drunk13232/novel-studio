# Novel Studio 2.24.0 Preview — Installation / 安装

Windows x64 and Microsoft WebView2 Runtime are required. Use the public Preview Setup.exe for a per-user installation. The default data folder is `%LOCALAPPDATA%\NovelStudio`; you may choose another separate folder. Setup does not download prerequisites or automatically open a demo. No Python or Vite command is required for the installed app.

Portable alternative: extract the complete Windows ZIP, keep `_internal` beside NovelStudio.exe. The Preview archive offers an original demonstration workspace. It contains fictional demonstration data only. Do not keep your only manuscript copy inside the program folder. Keep independent backups before upgrades; old versions are not removed.

Manual writing is offline and needs no AI account. Codex login, configured API/local-model services, ComfyUI, Pandoc, Windows voices and private Live2D assets are optional, separate requirements. No private character models or proprietary Cubism Core is redistributed. Do not upload private works, credentials or raw logs to Issues.

安装程序默认使用当前 Windows 用户的 LocalAppData 数据目录，不内置开发者的私人数据位置；可自行选择独立作品目录。不会自动进入演示项目。便携 Preview ZIP 与安装版的首次运行行为不同，均保留手动写作。

This remains Preview/PARTIAL. Physical IME, all DPI combinations and external AI services are not comprehensively verified. See [current verification](docs/oss/INSTALL-VERIFICATION.md) and [release notes](docs/oss/RELEASE-PAGE-NOTES.md). Unsigned/PyInstaller executables may trigger antivirus heuristics; do not disable protection or assume every warning is false.

[Development](docs/DEVELOPMENT.md) · [Windows build](docs/WINDOWS-BUILD.md) · [Apache-2.0](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md). Software licensing does not license user works.
