# Candidate Session Reliability — 2.24.15 Preview

## 简体中文

本版包含 2.24.14 的候选勾选、独立版本、连续输入和自动暂存改进，并修复迟到保存回执的界面归属。

在候选保存仍在等待时，作者可以关闭并重新打开同一个候选。原请求可能已经真正保存，不能把关窗当作服务器撤回。回执仍保留它提交的快照，但只有原编辑会话仍有效时，才能继续原来的切换版本或关闭操作。仅凭相同候选 ID、文本和说明不能认为是同一界面会话。旧失败也不能污染新窗口。

复用现有 CandidateDraft、Monaco、业务保存、版本校验和 Diff 采用通道。没有新增依赖、Agent、数据迁移或权限。没有向远端模型发送作品。正式采用仍由作者明确操作；Canon / State / Knowledge 权限不变。

## English

This Preview includes 2.24.14 candidate-choice, independent-variant, continuous-input and autosave improvements. A late save receipt may acknowledge its submitted snapshot, but may continue a variant switch or close only in the exact editing session that initiated it. Reopening identical IDs/text creates a different view; cancelled intentions cannot replay there. Existing committed drafts remain stored and stale failures cannot contaminate the replacement view.

The existing CandidateDraft, Monaco, save, revision and author-controlled adoption channels are reused. No dependency, agent, migration, permission expansion or remote-model request is added.

## Verification boundaries / 验证边界

Actual headless browser tests use an isolated public fixture and authenticated local application APIs; controlled response delays are transport tests, not model results. A real packaged worker and silent isolated installation do not establish native window interaction. Native WebView2/physical IME, system DPI, voice, new remote AI and long-duration use remain UNVERIFIED. Product status remains Preview / PARTIAL.

Use the Setup installer for personal installation and explicitly select your existing data directory. Portable Preview retains an isolated demonstration mode. Private source snapshots and audit receipts are not automatically public; only reviewed allowlisted files enter the GitHub source tree.
