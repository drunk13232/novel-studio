# Review Evidence & Recovery — 2.24.12 Local Preview

## 简体中文

本轮修复已复现的报告有效性与完成回执缺口，不新增 Agent 或另一套评审系统。复用 Director、ReviewCenter、TaskManager、候选 Diff 和原有主题。

- AI 追加、局部重写、取消后保留文字、重启后恢复文字及作者调整创作依据，都会让相同复核记录成为历史。
- 读取时核对既有报告的作品、路径、来源版本和受审文本哈希。旧记录漏标仍可被识别；版本依据不足标为无法核实。派生有效性不写回项目或迁移文件。
- 只展示已核实的原文引用；没有核实引用的发现标为作者待判断意见。点击“定位候选原文”使用实际 UTF-16 范围，不改正文、不自动采用建议；重复引用明确定位第一处。
- 未保存改文、历史/无法核实报告或已变化的来源，不能跳入新候选。重新读取报告时另行核对正文和引用来源；候选指纹一致并不代表来源仍是最新，也不代表正式正文通过。
- 报告损坏/丢失不隐藏已保留草稿。读取失败可用既有 GET-only 重试；再次模型复核仍由作者显式触发。
- 后台先清理执行状态、前端后收到完成回执时，仍处理属于当前记录及任务的真实回执；旧任务不能影响另一条记录或新执行。

安装程序可选择原用户数据目录；便携 Preview 保留公开演示用途。旧发行包、GitHub 发布与快捷方式保持原样。Developer ZIP 是本地开发快照，不是本轮已复扫的公开候选。

## 验证口径

针对性后端与无界面浏览器检查使用隔离项目、实际本地服务及受控模型/报告样本；不代表真实模型文学质量。结果明细见本轮本地交付回执。构建、安装/卸载、受限 EXE worker 与原生窗口是不同验收层次。未声称原生 GUI、实体中文输入法、DPI、真实语音或新远端 AI 已通过。

## English

The existing Director, ReviewCenter, TaskManager and candidate Diff remain authoritative. AI append/rewrite, retained cancellation/restart output and author-basis edits invalidate the same saved review. Existing report hashes and scope/version evidence derive read-only validity without a migration or report rewrite. Missing/corrupt provenance is unverifiable, not current, and cannot hide recoverable drafts.

Only verified source quotations are displayed as evidence. Locating one selects its validated UTF-16 range in the candidate; repeated quotes explicitly select the first verified location. Unsaved changes, historical/unverifiable reports and changed sources disable the jump. Re-reading a report checks source currency separately; a matching candidate fingerprint is not manuscript approval or proof of current sources.

Owned terminal receipts remain accepted after record cleanup; stale events cannot affect a different record/new execution. Local controlled checks, packaged-worker execution and silent install/uninstall are separate from native GUI, physical IME/DPI, voice and new remote-AI acceptance. Existing author confirmation and project isolation are preserved; no dependency, hidden remote call or automatic manuscript adoption was added. Setup can use the existing data directory; portable Preview is for the public demo. Developer ZIP is a local snapshot, not a newly reviewed publication candidate.
