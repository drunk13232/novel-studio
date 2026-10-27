# Experiment Format Specification 1.0

规范 Schema：`web/backend/app/world_logic/resources/world-experiment-1.0.json`，JSON Schema Draft 2020-12；这是应用自带 Schema，导入不能指定远端 Schema URL。

核心字段：schema_version、experiment_id、name、description、experiment_type、inputs、assumptions、constraints、acceptance_rules、solver、outputs、source_references。扩展字段：dependencies、sensitivity、baseline_id、baseline_version、scenario_note、seed、limitations、steps。未知字段拒绝；稳定 experiment_id 格式为 exp_ 加 32 位十六进制。

输入变量：id/name/kind(real/integer/boolean)/role(input/decision)/value/unit/minimum/maximum/source_ids/note。未知固定输入使用 null；只有作者明确将 role 设为 decision 时才允许 Z3 求可行值。可行解中的数值不是已经发生的事实。单位使用 Pint 英文单位，例如 km/hour、kg、joule；credit 是示例货币单位，不预设购买力。

来源区分 AUTHOR_CONFIRMED、COMMITTED、REFERENCE、ASSUMPTION、UNKNOWN。冻结时应用按当前项目重新校验目标并记录来源文件哈希。时间线计划或章节计划不会变为 COMMITTED。原始自然语言及数学约束 meaning 同时保留。

真实可解析示例见本目录 examples/travel.json 与 examples/event-order.yaml，均使用虚构参数。单位和表达式还需通过应用白名单检查，不能只依赖 Schema。

V2.9.2 optional fields: dependency kind/condition, events with explicit clocks or coordinates, schedule with bounded resources/operations, input basis and baseline fingerprints. Old 1.0 definitions remain readable. See the regenerated schema and finite-schedule/magic-consumption examples.
