# Candidate Recovery Protection — 2.24.17 Local Preview

## 简体中文

本轮修复选段比较与现有修订台中的多窗口冲突恢复，复用同一候选状态、etag 和作者确认通道。

- 载入另一窗口版本前，先对比；只为当前真正未保存且不同于已存版本的输入保留副本。干净的旧快照不制造额外未保存提示。
- 副本仍在时，退出与切换保持保护，编辑、再次载入、暂存和采用先暂停，避免在作者尚未取舍时覆盖内容。
- “下载保留的本地副本”导出保留的文字、说明和勾选。普通“下载当前草稿”仍导出当前画面中的版本，两者含义分开。
- 下载不等于项目暂存，也不会擅自解除离开保护。需要继续编辑时选择恢复，再明确暂存；希望保留已存版本时明确放弃本地副本。
- 另一窗口已处理的候选保持只读；本地未保存输入可下载，不能再次暂存或采用。关闭或切换仍需明确放弃。
- 保留副本只在当前运行窗口内。请保存或下载需要保留的内容；本版未增加崩溃后的副本持久化，也没有自动导入恢复 JSON 的入口。

正文不因载入、下载、放弃或恢复候选而改变。真正采用继续经过原文版本和作者明确确认。

## English

The existing Selection Diff and Revision Desk reuse the same candidate state, etags and author approvals. Loading another-window receipts retains only genuinely unsaved local input that differs from the stored value. Clean old snapshots create no false recovery warning. Retained input keeps the shared exit/navigation guard active and prevents unresolved overwrites, repeated loads or handoffs.

Download retained local copy exports that original buffer, note and choices; the ordinary draft download exports the currently displayed buffer. Downloading is not project persistence and does not dismiss protection. Restore local input and explicitly save, or explicitly discard it while keeping the stored version. A handled candidate stays read-only and cannot be saved/adopted again; its retained local input can still be downloaded before explicit discard/close.

Recovery remains window-local: save or download important text. Crash-persistent recovery and automatic re-import of recovery JSON are not implemented. No dependency, migration, new AI framework, storage format or permission expansion. Manuscript adoption remains separate and explicit.

## Verification boundary

Before/after reproduction and actual headless browser checks use independent public/synthetic projects and authenticated existing APIs. Controlled save failures and fixed local MOCK generation are not remote-AI evidence. Runtime/source alignment, executable worker and silent installation are separate checks. Native GUI, physical IME, system DPI, real speech, new cloud AI and long-duration use remain UNVERIFIED. This is a local Preview; publication and shortcut changes are separate actions.
