# Novel Studio 2.24.23 — Verified Save Feedback Preview

## Updates / 更新

- 2.24.20: revalidate selection and scope immediately before task creation; reject cancelled/expired assistant and Python ownership. Never automatically replay ambiguous task dispatches.
- 2.24.21: late save/recovery receipts cannot navigate after cancellation or newer input; actual errors and explicit retry.
- 2.24.22: owned nonblocking desktop-exit guard, duplicate protection and active-task recheck after backups. Real save/recovery/preferences outcomes.
- 2.24.23: distinguish confirmed manuscript saves from recovery-maintenance failures. Check ambiguous receipts once through the existing read-only file API, without replaying writes. Preserve newer input and unknown/conflicting state through undo; explicit manual recovery does not enable automatic recovery.

本次汇总选区任务取消、离开/退出与保存反馈修复。正文保存和恢复副本维护分别显示真实结果，不明回执不自动重发写入；未知或不同磁盘版本保持编辑保护。无新增依赖、Agent、数据库迁移或权限。统计只刷新既有视图，不制造字数、计时或用量。

## Verification and limitations / 验证与限制

47 isolated headless-browser scenarios passed for 2.24.23: 18 receipt/format/safety flows, 12 leave-dialog regressions, 15 exit regressions and 2 confirmed-save/recovery-failure combinations. Actual local file APIs and disk-byte checks, controlled response faults and a labelled desktop-boundary double. No model calls. Earlier-version evidence remains separate.

Preview / PARTIAL: native GUI, physical Chinese IME, system DPI, voices, real Codex/MCP/cloud AI and prolonged use are not newly validated. The packaged worker is a process check, not GUI acceptance. One earlier isolated-service shutdown cause and pre-existing outside-candidate global configuration drift remain unattributed; global configuration was not modified or reverted. Recovery snapshots do not replace persistent backups.

源码与发行候选排除私人作品、文献、凭据、用户配置、私有角色资源及父仓库 Git 历史。旧版保留。原生桌面、实体输入法、DPI、真实语音与新云端 AI 验收未完成，继续标为 Preview。

## Installation / 安装

Use Setup EXE or extract the portable ZIP to a new directory. Keep user data separate. Verify SHA256SUMS.txt before installing. AI, external Skills and ComfyUI require their own configuration; manual writing does not require an API key. PyInstaller EXEs may trigger antivirus heuristics; do not disable security protections to bypass warnings. Unsigned Preview; no signing guarantee.
