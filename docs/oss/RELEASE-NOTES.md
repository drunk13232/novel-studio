# Novel Studio 2.24.31 Director Usability Preview

**Preview / PARTIAL.** This update includes 2.24.29, 2.24.30 and 2.24.31 after the previously published 2.24.28.

## Highlights / 更新

- Saved Codex-login director and concrete API-writer configuration; candidate review, evidence-bound rework, explicit author approval and separate adoption remain distinct.
- Six visible operation stages, primary controls first, report-first results and folded diagnostics.
- Exact quoted/paragraph rework previews with occurrence and line labels, context and editor location. Authors may explicitly reject rework without calling a writer.
- Retry a failed acceptance review without replaying the writer. Record actual reviewer receipts and preserve author direction.
- Daily chapter work, persisted per-request AI controls and existing guarded recovery/cache operations from 2.24.29.

## Verification boundaries / 验证边界

- 2.24.31: 66 distinct related local backend checks; scoped browser checks use real local HTTP/storage/task execution with **MOCK model responses**, including narrow layout, RTL and reduced motion.
- The packaged EXE actually started with a visible Windows window and WebView2 bookshelf, then exited safely. This is startup evidence, **not native click/IME/DPI acceptance**.
- Prior real Codex verification belongs to 2.24.30; no new real-cloud AI calls in 2.24.31. Official DeepSeek still requires the author's configuration and remains **UNVERIFIED**.
- Exact-public-commit CI is checked separately in GitHub Actions. External optional Skills/voices and native hardware-dependent cases retain the documented exclusions.
- This release does not guarantee literary quality or automatically adopt text, Canon or State.

## Install / 安装

Use the versioned Preview Setup EXE, or extract the portable Windows ZIP and run `NovelStudio.exe`. Keep existing author data separate and select the existing data directory when needed. The public installer does not embed anyone's local data path and does not automatically launch the application.

安装程序适合普通使用；便携版解压运行。已有用户继续选择自己的原数据目录，先保留备份。无需独立安装 Python 或 Node。Codex、API、ComfyUI 和外部 Skills 按需配置；离线手动写作不依赖它们。

## Checksums / 校验

See the attached `SHA256SUMS.txt`. Source is Apache-2.0 with existing third-party notices retained; private character assets, novels, references, user databases and credentials are excluded.

Unsigned PyInstaller executables may trigger antivirus reputation warnings. Check the source and SHA-256; never disable security software to install a suspicious file. Report security issues using GitHub private vulnerability reporting.
