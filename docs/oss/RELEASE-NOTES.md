# Novel Studio 2.24.18 Candidate Open Reliability Preview

## 简体中文

本次公开更新合并 2.24.17–2.24.18 的候选恢复与读取修复，沿用现有 TaskManager、Diff、版本校验和作者确认，没有新增依赖、Agent、迁移或权限。

- 多窗口载入已存候选后，真正未保存的本地副本继续受到关闭和切换保护；可以单独下载、明确恢复或放弃。另一窗口已处理的候选保持只读。
- 候选历史和已有外部候选入口共用带取消与文档作用域的读取路径；迟到的成功或错误不覆盖新的比较。
- 应用候选前重新核对当前未保存输入、暂存状态、任务、作品与章节；读取有真实状态、取消入口和失败后的明确重试。
- 保留原始候选、源版本、接受前快照、作者逐项采用和 Canon / State / Knowledge 隔离。

### 下载与升级

- 安装程序：`NovelStudio-2.24.18-Preview-Setup.exe`。
- 便携包：`NovelStudio-2.24.18-Windows-Preview.zip`，保留独立公开演示模式。
- 个人使用推荐安装程序：备份作品后明确选择原有数据目录，程序与作品目录分开。旧发行版保留。
- 核对 `SHA256SUMS.txt`。程序尚未代码签名，PyInstaller 可能触发杀软误报；请核对来源和校验值，不要盲目关闭防护。
- 源码在仓库；私人 Developer ZIP、作品、凭据、角色资产和本地审计日志不上传。

### 实际验证与已知限制

本地记录包括 7 条新读取场景、7 条恢复回归与 19 项原有浏览器回归；新读取中 6 条为 headless 指针/键盘流程，1 条是明确标注的受控 renderer 后台请求边界。固定本地生成通过真实 TaskManager，属于 MOCK。57 项相关后端测试、TypeScript/Vite、封包对齐、EXE 的实际 WASI worker、静默隔离安装/卸载通过。没有新的真实远端模型调用。当前公开提交的 hosted Windows CI 在发布前单独核对。

**已知输入风险：** 通过软件助手结果“打开文档”时，在读取完成前继续输入，新增的未保存正文可能被较旧磁盘内容替换；已在隔离项目复现。请先保存，再导航，等待加载完成后继续输入。该后续修复尚未完成，不混入本版。

恢复副本仍为窗口内状态，没有跨崩溃的自动导入恢复流程；下载与项目暂存不同。请明确保存或下载后再退出。

继续标记 **Preview / PARTIAL**：原生 Windows GUI、实体中文输入法、系统 DPI、真实语音、新远端 AI 和长期使用未在本次重新验收。headless、MOCK、worker 和静默安装不能替代这些验收。

## English

This release combines the 2.24.17–2.24.18 recovery/read fixes using the existing TaskManager, Diff, revisions and author approvals, without new dependencies, agents, migrations or permissions.

- Keep genuinely unsaved local recovery protected after cross-window reloads. Export, explicitly restore or discard it; externally handled candidates remain read-only.
- Scope history and existing external candidate reads by cancellation and document ownership. Late success/errors cannot overwrite a newer comparison.
- Recheck live unsaved input, draft saves, task and document scope before applying a candidate. Show actual read status, cancel-read and explicit retry.
- Preserve raw provenance, source revisions, pre-adoption snapshots, explicit author adoption and Canon / State / Knowledge isolation.

Download the Setup or portable ZIP and check SHA256SUMS.txt. Back up first and explicitly select the existing data directory in the installer. Portable packages retain isolated public demo mode. Old releases are preserved. Binaries are unsigned; verify origin/checksums rather than blindly disabling antivirus protection. Private developer archives, works, credentials, character assets and local audit logs are not release attachments.

Local evidence covers seven new read scenarios, seven recovery regressions and nineteen existing browser checks. Six new read flows use actual headless pointer/keyboard interaction; one is a declared controlled renderer/background-request boundary. Fixed local generation through the actual TaskManager is MOCK. Fifty-seven scoped backend tests, TypeScript/Vite, source/package alignment, a genuine EXE WASI worker and silent isolated install/uninstall passed. No new cloud model was called. Exact-commit hosted Windows CI is checked separately before publication.

**Known input risk:** opening a document from an assistant result and typing while its lookup remains pending can replace newer unsaved manuscript input with older disk content. This was reproduced in an isolated project. Save first, navigate, then wait for loading to finish before typing. The unfinished follow-up fix is outside this release.

Recovery is still window-local, without automatic crash-persistent JSON re-import. Download is not project persistence: explicitly save or download before exiting.

**Preview / PARTIAL:** native Windows GUI, physical Chinese IME, system DPI, real speech, new remote AI and long-duration use were not reaccepted. Headless, MOCK, workers and silent installation do not establish those gates.
