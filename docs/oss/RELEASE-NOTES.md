# Novel Studio 2.24.27 — Recovery Integrity Preview

Preview / PARTIAL. A focused recovery and saving-safety update. Previous releases are retained.

## 中文

- 新版自动清理恢复副本时核对实际存储版本；副本已经变化则返回 412 并保留，损坏副本明确报错，不静默删除。原有四字段格式不变，无需迁移。
- 正文确认落盘与恢复副本维护分别显示。清理最多等待 10 秒，涵盖排队；未确认维护保留缓存与警告，不自动重发正文保存。
- 晚到回执必须符合当前项目、章节、加载代次、文字与本地缓存归属，不能清掉较新的恢复内容或释放其他未完成写入。
- 再次保存被拒绝时保留之前的未确认/冲突状态与离开保护；工作区忙碌不再被新误判为磁盘修订冲突。
- 章节读取中隐藏旧恢复入口，并检查读写归属。放弃副本等待实际删除回执；副本已变化时先保留，再由作者重新读取和明确选择。

## English

- Automatic cleanup compares the actual stored recovery-file version. Changed copies return 412 and stay intact; corrupt copies fail explicitly. Existing four-field storage needs no migration.
- Confirmed manuscript saves and recovery maintenance have separate feedback. Cleanup has a ten-second queue-inclusive deadline; uncertain maintenance retains caches/warnings and never replays manuscript writes.
- Late receipts must still own the current project, chapter, load generation, text and local cache; they cannot clear newer recovery input or release other pending writes.
- Rejected retries preserve prior uncertainty/conflicts and navigation guards. Busy-workspace rejection no longer creates a new disk-revision conflict.
- Recovery controls are hidden during chapter reads and guarded against concurrent reads/saves. Discard waits for a real receipt; changed copies remain pending for explicit reread/review.

## Verification and limits / 验证与限制

Completed local-delivery evidence: 26 isolated headless cases (nine recovery flows plus 17 affected existing regressions), 15 real local API tests, 56 separately labelled local-transport assertions, production frontend build, semantic frozen/source alignment, a real packaged bounded worker and isolated silent install/uninstall. This publication rechecks the immutable artifacts and public source; these local results are reused evidence, not newly repeated native acceptance. No real AI call was made. Exact-commit CI is reported in this Release and Actions.

Native WebView2 interaction, physical Chinese IME, actual system DPI, voice, real cloud AI and prolonged-use acceptance are not newly verified. Existing build chunk warnings remain. An isolated Windows Proactor/service-shutdown issue and older candidate-external Codex config drift remain unresolved; no claim of a shutdown fix. Later shutdown diagnostic changes are excluded. The legacy explicit unconditional-delete API remains compatible; new automatic cleanup is version-bound. Cancelling a browser request does not prove a server write stopped. Recovery copies are not durable backups.

## Installation / 安装

Use **NovelStudio-2.24.27-Preview-Setup.exe** to install, or fully extract **NovelStudio-2.24.27-Windows-Preview.zip** before running NovelStudio.exe. Keep existing writing data separate and select the existing data directory when upgrading. Basic packaged use needs no Python/Node installation. WebView2 and optional external AI/image/voice services retain their documented requirements. An unsigned PyInstaller EXE may trigger security warnings: check SHA-256 and the trusted source; do not disable protection blindly. Private writing, credentials and private character models are excluded. Source is available in this repository; the private Developer ZIP is not a public asset.
