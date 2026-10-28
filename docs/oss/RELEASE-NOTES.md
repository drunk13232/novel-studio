# Novel Studio 2.24.4 Writing Continuity Preview

**Preview / PARTIAL · Windows x64 · Apache-2.0 · Copyright 2026 drunk13232**

## 下载 / Downloads

- `NovelStudio-2.24.4-Preview-Setup.exe`：当前用户安装；默认使用独立的本地数据目录，不自动进入演示项目。
- `NovelStudio-2.24.4-Windows-Preview.zip`：完整解压后运行，保留 `_internal` 等同级文件。便携 Preview 提供原创演示环境。
- 已有用户请备份作品并选择原有数据目录。安装目录与作品数据保持分离，旧发行版继续保留。
- 需要 Windows x64 和 Microsoft WebView2 Runtime；不要求单独启动 Python 或 Vite。
- 校验值见附件 `SHA256SUMS.txt`。源码在本仓库与该版本标签中，不上传本机 Developer ZIP、私人启动脚本或用户配置。

## 2.24.1–2.24.4 的改进 / Highlights

- AI 创作指挥台：任务书、候选、结果与回执更清楚；指定步骤可单独执行、使用独立模型参数，支持独立候选尝试和明确的 Python 只读结果回传。
- 正文工具接入原有可调侧栏，保留正文高度、表单输入和专注模式恢复；上下文审核后返回所选工具，不自动启动模型。
- 新增“本章工作”：在正文侧栏查看目标、待办、修订事项、待处理候选和真实出处。
- 候选文本、修改说明和选段变更选择可在项目内暂存，按候选版本独立恢复；支持关闭、重启与既有备份恢复。
- 两窗口暂存冲突、原文过期、关闭与拒绝建议明确区分；正文采用继续经过作者确认及现有 Final/Canon/State 保护。
- 修复小窗口 Diff 被压成一行、重新计算期间旧变更列表仍可采用、末尾选择性修改丢失换行等问题。
- 现有 AI 控制显示计划模型、接收服务、有效思考档位和资料范围。未知值明确标记，实际请求以执行回执为准。

Existing writing tools now preserve manuscript space and source approval. Candidate edits/notes can be saved per variant and resumed after reopening or restarting. Current Chapter links existing tasks, proposals and evidence. Model preflight reuses existing routing, permissions and receipts. No new Agent framework, runtime dependency or database migration.

## 实际验证 / Verification

- 52 distinct related backend checks passed, plus 17 local MOCK protocol/parameter checks.
- 13 revision-hunk boundary checks and 16 production-page headless Edge scenarios passed with an actual isolated local backend.
- Candidate recovery after backend restart, concurrent draft conflicts, explicit partial adoption, read-only handled history, ordinary text save/undo and narrow-window layout were checked.
- Packaged EXE local worker ran successfully without a window. Manifest/resource hashes and ZIP CRC passed.
- Silent install/uninstall used isolated directories and `/NOINTEGRATION`: original payload hashes matched; data and extra files were preserved. This did not modify desktop shortcuts or test native window clicks.
- Public source uses an explicit allowlist, excludes parent Git history and personal data, and passed privacy/secret review. Scanner matches were individually verified as synthetic test constants, upstream examples or pinned file hashes.

## 已知边界 / Known limits

- Still **Preview / PARTIAL**. Native WebView2 clicks, physical Chinese IME, full system DPI coverage, real remote AI/Codex, voices and long-term workloads were not revalidated in this release.
- Mock protocol checks do not establish remote model availability, entitlement or real AI quality. No paid model call was made for this update.
- Cross-restart recovery here covers saved candidate drafts; it does not promise persistence of every temporary form or the editor undo stack.
- Some existing lazy Monaco/PDF/timeline chunks retain Vite size notices. No measured startup/memory gain is claimed.
- GitHub Actions results are recorded only after they actually run; older version CI results are not treated as current validation.
- The unsigned PyInstaller installer may trigger heuristic antivirus warnings. Verify the source and hashes and investigate alerts; do not disable security protection on the assumption that all alerts are false positives.

Private character models/voices, Cubism Core, real novels, user databases, API keys and login credentials are not included. Optional Codex/API, ComfyUI, Pandoc and voice features require their own setup. Third-party licenses remain separate.

## 安全反馈 / Security

Use repository **Security → Advisories → Report a vulnerability** for private security feedback. Do not post private fiction, credentials or unsanitized logs in public issues.

## SHA-256

`NovelStudio-2.24.4-Preview-Setup.exe`

```text
69294ec867adb08e62848b996c66ea829c0c03f5ace65cfd24080ee56d5fb062
```

`NovelStudio-2.24.4-Windows-Preview.zip`

```text
ab10521d4be31c5bc1a4a6c37a9ea69d1bb96e9e002aba0f1abc31afda8f6f65
```

