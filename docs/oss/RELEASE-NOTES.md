# Novel Studio 2.24.26 — Bounded Chapter Opening Preview

Preview / PARTIAL. This update includes the completed 2.24.24–2.24.26 local improvements. Previous releases remain available.

## 中文

- 保存成功后按实际正文保存事件刷新码字统计；不靠持续轮询，不将恢复副本计为正文增字。
- 只读磁盘快照具有取消和明确的失败状态，仍走原有作者选择与修订保护流程。
- 保存回执核对和章节读取具有明确等待边界。章节正文/恢复副本读取共用 10 秒时限，作者可以取消；取消或失败保留原有缓冲区与撤销/重做。
- 工作区恢复先选最终目标。保留版 2.24.25 与新版本的两个实际对照场景中，正文/恢复 GET 从四次减少为两次；不据此宣称启动时间或内存改善比例。
- 不自动重发正文保存，不跳过未完成的恢复检查，不扩大 Codex、文件或模型权限。

## English

- Refresh writing statistics from actual successful manuscript-save events, without continuous polling or treating recovery snapshots as manuscript growth.
- Cancellable read-only disk previews preserve the existing author-choice/revision flow.
- Bounded save-receipt verification and cancellable chapter opening; paired chapter/recovery reads share a 10-second deadline. Failed/cancelled loads preserve existing text and undo/redo.
- Workspace restoration resolves the final target first. Both measured same/alternate-target comparisons reduced content/recovery GETs from four to two; no startup-time or memory percentage is inferred.
- No automatic manuscript-save replay, silent recovery bypass or wider Codex/file/model permissions.

## Verification boundaries / 验证边界

The completed local 2.24.26 delivery records 39 isolated headless cases, a production frontend build, source/frozen-code alignment, a real packaged bounded worker and isolated silent install/uninstall. They are separate gates, not native desktop acceptance. Native WebView2 clicks, physical Chinese IME, actual system DPI, voice, real cloud AI and prolonged-use acceptance were not newly performed. Existing build chunk warnings remain. Older isolated shutdown problems and pre-existing, candidate-external Codex config drift have not been attributed or claimed fixed. Recovery copies are not durable backups. In-progress recovery-integrity changes are intentionally outside this immutable release.

## Install / 安装

Download the **Preview Setup.exe** for installation, or extract the **Windows Preview.zip** fully before running NovelStudio.exe. Keep existing writing data separate from the installation; select your existing data directory when upgrading. No Python/Node installation is required for packaged basic use. WebView2 and optional external AI/image/voice services keep their documented requirements. Windows may warn about the unsigned PyInstaller application; verify SHA-256 and its GitHub source, and do not disable security protection blindly. Both packages contain no personal writing, login credentials or private character models.
