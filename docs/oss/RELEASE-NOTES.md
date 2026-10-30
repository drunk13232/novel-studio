# Novel Studio 2.24.15 Candidate Session Reliability Preview

## 简体中文

本次更新合并 2.24.14–2.24.15 的候选编辑与保存回执修复，继续使用现有创作指挥台、候选 Diff 和安全保存通道。

- 候选文字和说明可在自动暂存等待期间继续编辑，后续输入不会被旧回执覆盖。
- 每个候选版本独立恢复勾选和说明；明确暂存也会记住所选版本，单纯查看不写入。
- 编辑某处修改后，已跳过的其他修改不会重新勾选；新增、扩大或无法可靠对应的变化保留给作者核对。
- 修复持续打字时的受控回写问题，保留实时文字、撤销和重做。
- 修复关闭后迟到回执误切换版本、误关闭新比较窗口的问题。已真正保存的原候选快照继续保留。
- 采用仍由作者明确决定，保留原文版本校验、EOL/BOM、接受前快照、项目隔离与 Canon/State/Knowledge 权限。

### 下载与升级

- Windows 安装程序：`NovelStudio-2.24.15-Preview-Setup.exe`。
- 便携 Preview：`NovelStudio-2.24.15-Windows-Preview.zip`，保留独立公开演示模式。
- 个人使用推荐安装程序，升级前备份作品，在安装器中明确选择原有数据目录。安装目录与作品目录应分开。
- `SHA256SUMS.txt` 用于完整性核对。程序尚未进行代码签名；PyInstaller EXE 可能出现杀毒软件误报，请先核对来源与校验值，不要盲目关闭安全防护。
- 源码在仓库；私人 Developer ZIP、审计记录、用户数据和角色资产不会上传为 Release 附件。

### 验证与限制

本轮 13 项实际 headless 浏览器流程和 45 项相关后端检查通过；使用隔离公开模板和合成正文，没有远端模型调用。受控延迟/错误是回执边界检查，不是真实 AI 能力证明。封包、静默隔离安装/卸载、EXE worker 与当前提交的 Windows CI 结果分别记录。

保持 **Preview / PARTIAL**。原生窗口交互、实体中文输入法、系统 DPI、真实语音、新远端 AI 和长期使用未在本轮验收。没有新增依赖、Agent、数据迁移或权限扩张。

## English

This Preview includes the local 2.24.14–2.24.15 candidate editing and save-receipt fixes.

- Keep editing candidate text and notes during autosave; later input remains pending rather than being overwritten by an old receipt.
- Restore each variant's choices and note independently. Explicit Save also remembers the active variant; viewing alone does not write.
- Keep skipped edits skipped after unrelated changes. New, expanded or ambiguous changes require author review.
- Preserve rapid typing, undo and redo by separating live editor input from deliberate replacements.
- Prevent late receipts from replaying cancelled variant switches or closing a reopened comparison. Legitimately saved old snapshots remain stored.
- Preserve explicit author adoption, source revisions, EOL/BOM, original snapshots, project isolation and Canon/State/Knowledge protections.

Use the Setup installer for personal installation and explicitly select the existing data directory after backing up. The portable Preview retains an isolated public demo mode. Source is in the repository; private developer archives, audit logs, author data and character assets are not Release attachments. SHA-256 checksums are supplied. Binaries are unsigned and PyInstaller executables may trigger antivirus false positives; verify origin/checksums rather than blindly disabling protection.

Thirteen actual headless browser workflows and 45 scoped backend checks passed on isolated public/synthetic data, with no remote-model requests. Controlled delays/errors are transport-boundary tests, not real-AI evidence. Packaging, silent isolated install/uninstall, executable worker and exact-commit Windows CI have distinct receipts. Native GUI, physical IME, system DPI, real speech, new remote AI and long-duration use remain **UNVERIFIED**. Product status stays **Preview / PARTIAL**; no new dependencies, agents, migration or permission expansion.
