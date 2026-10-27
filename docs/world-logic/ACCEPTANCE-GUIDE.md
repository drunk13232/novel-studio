# Acceptance Rule Guide 1.0

每项验收包含 id/name/type/target/expression/minimum/maximum/unit/condition/basis/applicability/severity/automatic/source_ids。

- HARD：明确布尔关系，例如 duration <= available。
- RANGE：选择数值目标、单位和上下限，例如 balance 至少为 0 tonne。
- RELATIONAL：明确顺序关系；target=dependencies 检查显式依赖有向环。
- DIMENSIONAL：检查公式单位能否转换到指定单位，不能替代数值有效性判断。
- CONDITIONAL：condition 控制适用，例如 not teleport 时才检查旅行时间。
- QUALITATIVE 或 automatic=false：NOT RUN，作者审核。AI 可以给意见，不能假装数学证明。

PASS：只表示当前实际执行的条件通过。FAIL：违反明确规则，或 Z3 返回可违反验收的反例。INCONCLUSIVE：输入不足、不适用或 Z3 UNKNOWN。ERROR：执行出错。NOT RUN：未执行/需人工判断。信息不足优先保留，不自动补值。未接受假设使实验认证为 INCONCLUSIVE。

Z3 SAT 提供可行解；验收通过要求在当前约束下其否定不可满足。发现可违反的可行模型时显示反例，明确不代表所有情景必然失败。UNSAT core 是可定位冲突集合，不保证最小集合。不能将 SAT 宣传为完整世界合理。

确认时冻结定义及 acceptance_fingerprint；失败后 AI 只能建议新草稿，任何阈值修改都需作者重新确认并说明原因。示例：examples/travel.json 的 arrival / units 两条验收。

Challenge intensity cannot replace baseline criteria. Same-model roles are opinions. CP-SAT FEASIBLE is not OPTIMAL, and a failing incomplete witness yields INCONCLUSIVE. Unsat Core is not guaranteed minimum.
