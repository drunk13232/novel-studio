# Candidate Editing Reliability — 2.24.14 Local Preview

## 简体中文

本轮完善现有选段候选 Diff，不新增 Agent、工作台、依赖或项目格式。

- 每个候选版本的勾选与说明分别保存。换行表现变化不会清空勾选；点击“暂存候选”也会记住所选版本，单纯查看不会写入。
- 编辑候选时按原文覆盖范围保留已作出的选择。先前跳过的部分不会因别处编辑而重新勾选。新增、扩大、无法可靠对应或混入未选范围的修改保持未勾选，并给出核对提示。
- 自动暂存等待回执时仍能编辑候选和说明；回执仅确认本次提交，后续输入继续保持待保存。首次读取、冲突待处理和实际采用/拒绝期间仍受既有锁定保护。
- 编辑器的即时输入与主动加载/重置/切换候选分开，避免逐字输入经父组件回写造成回退或光标跳动。
- 采用只通过现有作者确认与版本校验通道。未勾选内容不采用；Source、Final、Canon、State、Knowledge 权限不变。原有换行、BOM 和接受前快照继续保留。

建议操作：打开候选 → 勾选修改 → 编辑文字/说明 → 暂存 → 必要时切换版本 → 核对最终勾选 → 明确采用。遇到新增或合并变化时先检查，不以“差异已计算”代替作者决定。

## 验证边界

隔离公开演示项目、实际 headless 浏览器和本地业务 API 用于检查；没有调用远端模型。键盘与候选保存检查不等于实体中文输入法或原生 WebView2 验收。精确通过项目见本地 LOCAL-DELIVERY.json。原生 GUI、实体 IME、系统 DPI、真实语音、新远端 AI 和长期使用未验收，保持 Preview / PARTIAL。

旧 2.24.13 公开发行与 Allowlist 保留。本轮 Developer ZIP 是本地开发快照，不是重新审核的公开候选。个人安装推荐 Setup 并选择原数据目录；便携 Preview 保留独立演示模式。

## English

This local Preview refines the existing candidate Diff without agents, dependencies, workbenches or data migrations.

- Store each variant's choices and note independently. Logical newline equivalence preserves indexes; explicit Save also records the selected variant. Merely viewing does not write.
- Carry explicit choices by immutable original-source coverage. Skipped text stays skipped after unrelated edits. New, expanded or ambiguous/merged changes remain unchecked for author review.
- Keep candidate and note input writable during autosave. Receipts acknowledge their submitted snapshot; later input stays pending. Initial reads, incoming conflicts and actual decisions retain their locks.
- Keep live model edits distinct from deliberate load/reset/switch replacement props to avoid rapid-input echo and caret regressions.
- Adoption still uses the existing author confirmation, candidate/source revision checks, EOL/BOM preservation and original byte snapshot. Formal content and Canon/State/Knowledge authority remain unchanged.

Validation uses isolated public fixtures, actual headless browser and local APIs, with no remote-model call. It does not establish native WebView2, physical IME/DPI, speech or long-duration acceptance. See LOCAL-DELIVERY.json for exact results. The public 2.24.13 artifacts and reviewed Allowlist remain; this private Developer ZIP is not a newly cleared public source release.

## Implementation reference

The installed Monaco 0.57.0 API supplies computed original/modified line ranges and actual model change events; no new diff engine is implemented. Coverage mapping only retains or reduces prior consent, never silently grants skipped/new ranges. It is scoped to the same original text and existing candidate session. The existing backend author_draft / active_variant schema remains unchanged.
