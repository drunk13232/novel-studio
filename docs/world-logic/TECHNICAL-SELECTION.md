# 技术选型 — 2026-10-12

| 库 | 实际版本 | Python/Windows | 许可证 | 用途 |
|---|---|---|---|---|
| z3-solver | 5.1.0.0 | 官方 PyPI win_amd64 wheel，当前 Python 3.12 | MIT | SAT、UNSAT、冲突集合、反例 |
| NetworkX | 3.7 | Python >=3.12，纯 Python | BSD-3-Clause | DAG、环、拓扑、后代影响链 |
| SymPy | 1.14.0 | Python >=3.9，纯 Python | BSD-3-Clause | 白名单符号公式 |
| Pint | 0.26.1 | Python >=3.12，纯 Python | BSD-3-Clause | 单位/量纲 |
| jsonschema | 4.26.0 | Python >=3.10，纯 Python | MIT | Draft 2020-12 |

依赖通过官方 https://pypi.org/simple 安装，未关闭 TLS，未修改全局 Python。SymPy 带 mpmath 1.3.0；Pint 带 flexcache 0.3、flexparser 0.4、platformdirs 4.13.0。许可全文由现有 desktop/collect_licenses.py 收集。

官方来源：[Z3](https://github.com/Z3Prover/z3)、[NetworkX DAG](https://networkx.org/documentation/stable/reference/algorithms/dag.html)、[SymPy parsing warning](https://docs.sympy.org/latest/modules/parsing.html)、[Pint](https://pint.readthedocs.io/en/stable/getting/tutorial.html)、[JSON Schema](https://json-schema.org/draft/2020-12)。通用 SymPy 字符串解析有执行风险，本模块没有采用。

PyInstaller 沿用原方案，收集 z3/libz3.dll、Pint definitions、分发元数据、实验 Schema/模板及许可；实际冻结运行结果见本轮报告。不是仅根据文档认定兼容。

未安装 Pymunk、Mesa 或 3D 引擎；没有可靠社会模型时只输出设计 Proposal 和局限。前端复用现有 React Flow/Dagre/Recharts，未增加可视化引擎或 AI 框架。

## V2.9.2 selection

Official OR-Tools 9.15.6755 is added specifically for finite-resource scheduling (Apache-2.0, official CPython 3.12 win_amd64 wheel). Z3 5.1.0.0, NetworkX 3.7, SymPy 1.14.0, Pint 0.26.1 and jsonschema 4.26.0 remain pinned. The original worker budget and filesystem restrictions remain; numerical threads are bounded to one. Windows source and frozen validation are recorded separately.

[Official wheel and license](https://pypi.org/project/ortools/9.15.6755/), [CP-SAT integer constraints and statuses](https://developers.google.com/optimization/cp/cp_solver), [interval/resource scheduling](https://developers.google.com/optimization/scheduling/job_shop), [NetworkX DAG](https://networkx.org/documentation/stable/reference/algorithms/dag.html), [SymPy parse_expr warning](https://docs.sympy.org/latest/modules/parsing.html). The application continues constructing symbolic expressions from a bounded AST whitelist, without parse_expr/eval/exec for imported formulas.

SimPy is appropriate for future explicitly modeled queues and event processes; SALib is appropriate for defined global sensitivity problems. Neither is required for the current static schedule and deterministic one-factor scan, so neither is installed. No simulator service or plugin market is introduced.
