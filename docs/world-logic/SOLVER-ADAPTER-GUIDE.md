# Solver Adapter Guide 1.0

接口声明：app/world_logic/adapters.py 的 SolverAdapter Protocol。实现提供 extension_id、version 和 run(definition, timeout_seconds, cancelled) -> report。元数据示例见 examples/adapter.json，包含名称、实验类型、输入/输出 Schema、引擎类型、运行要求和许可证。报告 Schema 位于 resources/world-report-1.0.json。

内置静态白名单：z3、graph、formula。实现位于 engine.py，使用 Z3 Solver、NetworkX DAG 算法、SymPy 符号表达式和 Pint 量纲。适配器没有 Canon、数据库或任意文件写入对象。

第三方 Python 代码必须作为开发者扩展单独安装、审核、授权，并接入受限子进程；导入实验不能自动安装包或加载任意模块。本版不提供热加载或插件市场。请求未启用的 Pymunk/Mesa 类型会被 Schema 拒绝，不会伪造模拟结果。

worker 仅 JSON stdin/stdout。运行通过现有 TaskManager，超时/取消只关闭本应用持有的进程。Windows Job Object 限制 512 MiB 与两个进程（兼容 venv 启动器）；Unix 设置内存/CPU 上限。Z3 自身另限 3 秒与 256 MiB。开发者需重新做冻结 EXE 检查，不能仅凭 import 宣称可打包。

Builtin adapter version 1.1 includes schedule via official OR-Tools. Inputs/outputs remain the existing schemas. Code-based extensions still require separately audited installation; imported JSON cannot register executable adapters.
