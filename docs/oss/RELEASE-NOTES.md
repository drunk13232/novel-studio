# Novel Studio 2.24.28 — Shutdown Admission Preview

Preview / PARTIAL。关闭服务前停止主、项目、草稿与已有文献任务入口；排队任务不会在关闭后启动。单个中断或关闭失败不再跳过其他任务/服务，等待真实 runner 并保留错误。64 项不同的相关本地检查、两项真实回环保存/关闭场景及五项最终 headless 恢复场景通过。最后隔离服务退出仍出现 WinError 10054 和 30 秒 graceful-shutdown 超时，根因未确认；另一次浏览器首轮非成功响应未记录状态码，后续未重现。未宣称这些问题已修复。

Preview / PARTIAL. Stop admission for main/project/draft/known-reference managers before service waits, prevent queued work from starting after closure, continue other owners after stop/close errors, drain real runners and preserve failures. 64 unique targeted local checks, two real loopback save/shutdown cases and five final headless recovery cases passed. Final isolated service exit still logged WinError 10054 and the existing 30-second graceful-shutdown timeout; root cause remains unresolved. One initial browser non-success response was not status-recorded and did not recur on follow-up. Neither issue is claimed fixed.

## Downloads / 下载

- `NovelStudio-2.24.28-Preview-Setup.exe`: recommended Windows installer; existing data stays independent.
- `NovelStudio-2.24.28-Windows-Preview.zip`: portable Preview (existing demo marker retained; use an explicit workspace for real projects).
- `SHA256SUMS.txt`: SHA-256 download checksums.
- Source: repository / GitHub-generated source archives. No private Developer ZIP is uploaded.

## Verification and limits / 验证与限制

64 unique targeted local checks; two actual loopback save/recovery/shutdown cases; five final headless recovery cases; real packaged bounded worker; isolated silent install/uninstall; frontend production build. These do not represent native GUI/IME/DPI/voice/cloud-AI acceptance.

Known: final isolated Windows exit reproduced connection reset plus the existing 30-second graceful-shutdown timeout. One earlier unclassified non-success browser cleanup response did not reproduce later. Preview remains PARTIAL. Details: [publication verification](https://github.com/drunk13232/novel-studio/blob/main/docs/workbench-experience/DELIVERY-2.24.28-PUBLICATION.md).

No new dependencies, schema migration, broader permissions, real-work edits or shortcut changes. Prior releases retained. Private manuscripts, credentials and character assets excluded; no parent private Git history introduced. Apache-2.0 / drunk13232. Unsigned PyInstaller builds can trigger antivirus false positives; download only from the project Release and verify hashes.
