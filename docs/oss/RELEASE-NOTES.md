# Novel Studio 2.24.16 Candidate History Reliability Preview

## 简体中文

本次更新完善现有候选编辑和历史展示，没有增加依赖、Agent、迁移或权限。

- 新候选、已结束比较不会继承上一轮临时说明或勾选；重新打开待处理候选恢复它自己的暂存。
- 已处理历史可以单独查看各版本作者暂存的文字和说明。暂存可能包含未采用修改，不冒充正式正文或采用回执。
- 原文变化后的只读历史保持所选原始候选，避免被另一版本暂存覆盖。
- 同文版本切换继续使用有效差异，避免等不到计算事件而一直加载。
- 保留明确采用、原文版本、原始候选、接受前快照、项目与 Canon/State/Knowledge 隔离。

### 下载和升级

- 安装程序：`NovelStudio-2.24.16-Preview-Setup.exe`。
- 便携包：`NovelStudio-2.24.16-Windows-Preview.zip`；保留独立公开演示模式。
- 个人使用推荐安装程序，备份作品后明确选择原有数据目录；安装和作品目录分开。
- `SHA256SUMS.txt` 提供完整性核对。程序尚未代码签名；PyInstaller 可能触发杀软误报，请核对来源和校验值，不要盲目关闭安全防护。
- 源码在仓库。私人 Developer ZIP、用户作品、凭据、角色资源和审计日志不作为 Release 附件。

### 验证边界和已知问题

19 项真实 headless 浏览器流程、45 项相关后端检查、TypeScript/Vite、源码/封包对齐、实际 EXE worker 和静默隔离安装/卸载已通过。固定本地 JSON 通过真实 TaskManager 的生成检查属于 MOCK；本次没有远端模型调用。当前提交的 hosted Windows CI 结果在发布前另行核对。

**已知边界：** 多窗口发生保存冲突时，“载入已存版本”后保留的未保存本地副本仍只在当前窗口内，关闭保护存在缺口。请在载入前先下载本窗口草稿；若已载入，先“恢复本地输入”并保存或下载，确认保存成功后再关闭。正在处理的修复不混入本版。

继续标记 **Preview / PARTIAL**。原生 GUI、实体中文输入法、系统 DPI、真实语音、新远端 AI 和长期使用未在本轮验收。浏览器、worker 与静默安装不能替代这些验收。

## English

This update improves the existing candidate editor and history without new dependencies, agents, migrations or permissions.

- Reset transient notes/choices for fresh candidates and closed decisions; proposed candidates reopen with their own stored edits.
- Expose per-variant author snapshots separately in handled history. Saved text may include unadopted edits and is not an adoption receipt or manuscript authority.
- Keep the selected original variant in stale read-only history instead of restoring another editable draft.
- Retain valid computed diffs for identical-text variant switches.
- Preserve explicit author adoption, source revisions, raw provenance, pre-adoption snapshots and project/Canon/State/Knowledge protections.

Download the Setup installer or portable ZIP and check SHA256SUMS.txt. Back up first and explicitly select the existing data directory in the installer. Portable builds retain isolated public demo mode. Binaries are unsigned and PyInstaller may cause antivirus false positives; verify origin/checksums rather than blindly disabling protection. Private developer archives, works, credentials, character assets and audit logs are not release attachments.

Nineteen actual headless browser workflows, 45 scoped backend checks, TypeScript/Vite, package/source alignment, a real executable worker and silent isolated installation/uninstallation passed. Fixed local JSON through the actual TaskManager is explicitly MOCK. No remote model was called. Exact-commit hosted Windows CI is verified separately before publication.

**Known limitation:** after a cross-window save conflict, loading the stored version retains the unsaved local backup only in the current view and its close protection has a gap. Download the local draft before loading. If already loaded, recover local input and save or download it before closing. The in-progress fix is outside this release.

**Preview / PARTIAL:** native GUI, physical Chinese IME, system DPI, real speech, new remote AI and long-duration use remain UNVERIFIED; browser/worker/silent-install checks do not establish those gates.
