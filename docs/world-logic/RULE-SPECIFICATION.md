# Rule Specification 1.0

语法是有限数学表达式，不是 Python：数值/布尔常量、声明的英文变量、+ - * / **、比较、and/or/not、abs/sqrt/min/max。没有字符串、对象属性、下标、导入、循环、任意函数调用。AST 只用于读取语法树，既不 compile 也不 eval；SymPy 节点由白名单显式构造，不使用 untrusted parse_expr/sympify。

例：distance / speed；duration <= available；stock + (production - consumption) * days；energy >= cost。输出按声明顺序计算，引用未来输出会保留未知，不能自动倒推。需要未知量可行解时选 Z3。Z3 除法分母暂限非零数字常量，可改写为乘法约束并明确分母的范围；幂指数是有限整数。

依赖图由 dependencies 的 before/after 声明，NetworkX 验证有向环和拓扑顺序，并返回影响链；没有显式边就不推测顺序。before/after 使用英文事件标识，可通过 source_ids 关联原事件。

Pint 对同量纲单位换算。长度和时间相加会失败；作者给出重力或魔法恢复参数时使用本次输入，不偷用地球常量。结果不推导未定义的经济行为。

真实例：examples/physics-units.json 使用重力 3.2 m/s²、质量 10 kg、高度 5 m，输出力 32 N、能量 160 J。该值只是模板的架空设定。

Only strict_order dependencies require DAG. availability checks declared instants; causal permits feedback; association is not causal. Conditions must evaluate to Boolean relations. All expressions remain data-only whitelist AST.
