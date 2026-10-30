# Candidate History Reliability — 2.24.16 Local Preview

## 简体中文

本轮修复现有选段候选的临时状态与历史展示，没有新增 Agent、依赖或存储格式。

- 开始新候选或关闭已决策比较时，说明与临时勾选不跨候选遗留。重新打开仍在处理的候选时，按原有接口恢复它自己的已保存状态。
- 历史中的“作者暂存的文字与说明（只读）”保存每个版本原有的记录。这些文字可能包含未采用修改，不能当作实际正文或完整采用凭证。
- 原文变化后的历史保持所选原始候选版本，不再被可编辑暂存恢复覆盖。查看不会写入；采用仍受原版本与作者确认保护。
- 同样文字的版本切换继续使用有效的已计算差异，避免无内容变化时等待不会发生的计算事件。

操作：候选记录 → 查看历史 → 展开作者暂存记录 → 查看说明或当时文字。要采用建议，仍需当前原文有效且经过现有 Diff 明确确认。

## English

Fresh candidate generations and closed decisions reset transient notes/choices; reopening a proposed candidate restores its own saved state. Handled history exposes per-variant author snapshots read-only. Saved edits may include changes that were never adopted; they are not a manuscript authority or an adoption receipt. Stale read-only history retains the selected original variant rather than applying editable-draft restoration. Identical-text switches retain their valid computed diff. Existing TaskManager, storage, revisions and explicit adoption remain the only authorities.

## Verification boundary

Isolated public/synthetic projects and actual headless browser interactions validate local behavior. Fixed local JSON generation through the real TaskManager is explicitly MOCK, not a real-AI result. Packaged worker and silent installation checks do not establish native GUI, physical IME, system DPI, real speech or new remote-AI acceptance. Product status remains Preview / PARTIAL. The public 2.24.15 release and its Allowlist remain unchanged; this iteration is local only.
