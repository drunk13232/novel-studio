"""AST is syntax only: never compile/eval, attributes, strings or arbitrary calls."""
import ast, math, re
from functools import lru_cache
from app.errors import ConsoleError
class Missing(ValueError):pass
class Unsafe(ValueError):pass
@lru_cache(maxsize=1)
def registry():
    import pint
    r=pint.UnitRegistry();r.define('credit = [currency]')
    return r
@lru_cache(maxsize=256)
def unit(text):
    text=text or 'dimensionless'
    if len(text)>80 or '__' in text or not re.fullmatch(r'[A-Za-z0-9_ */^().-]+',text):raise Unsafe('单位仅允许标准英文单位名和乘除幂')
    return registry().Unit(text)

def exponent(node):
    # A signed literal only; AST precedence stays Python's mathematical precedence.
    sign=1
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
        sign=-1 if isinstance(node.op,ast.USub) else 1;node=node.operand
    if not isinstance(node,ast.Constant) or type(node.value) is not int or abs(node.value)>8:raise Unsafe('幂指数必须是 -8 到 8 的有符号整数字面量')
    return sign*node.value

def check(text,names):
    if len(text)>800:raise Unsafe('表达式过长')
    tree=ast.parse(text,mode='eval')
    nodes=list(ast.walk(tree))
    if len(nodes)>120:raise Unsafe('表达式过于复杂')
    if sum(isinstance(n,ast.Pow) for n in nodes)>3:raise Unsafe('单个表达式最多允许三个幂运算')
    allowed=(ast.Expression,ast.Constant,ast.Name,ast.Load,ast.BinOp,ast.UnaryOp,ast.BoolOp,ast.Compare,ast.Call,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.USub,ast.UAdd,ast.Not,ast.And,ast.Or,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    for n in nodes:
        if not isinstance(n,allowed):raise Unsafe('不支持的表达式语法：'+type(n).__name__)
        if isinstance(n,ast.Constant) and (not isinstance(n.value,(int,float,bool)) or not math.isfinite(n.value) or abs(n.value)>1e15):raise Unsafe('常量必须为有限数值或布尔值')
        if isinstance(n,ast.Name) and (n.id.startswith('_') or n.id not in names|{'abs','sqrt','min','max'}):raise Unsafe('未声明的变量：'+n.id)
        if isinstance(n,ast.Call) and (not isinstance(n.func,ast.Name) or n.func.id not in {'abs','sqrt','min','max'} or n.keywords or not 1<=len(n.args)<=4):raise Unsafe('仅支持 abs / sqrt / min / max')
        if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Pow):exponent(n.right)
    return tree.body

def interpret(node,env,engine='quantity'):
    import sympy as sp
    if engine=='z3':import z3
    if isinstance(node,ast.Constant):
        if isinstance(node.value,bool):return z3.BoolVal(node.value) if engine=='z3' else node.value
        return z3.RealVal(str(node.value)) if engine=='z3' else sp.Rational(str(node.value)) if engine=='symbolic' else registry().Quantity(node.value)
    if isinstance(node,ast.Name):
        if node.id not in env or env[node.id] is None:raise Missing('缺少参数：'+node.id)
        return env[node.id]
    if isinstance(node,ast.BinOp):
        a=interpret(node.left,env,engine)
        if isinstance(node.op,ast.Pow):
            power=exponent(node.right)
            if engine=='z3' and power<0 and not isinstance(node.left,ast.Constant):raise Unsafe('Z3 负幂暂限非零常量底数；变量请改为乘法约束并声明非零范围')
            if power<0 and isinstance(node.left,ast.Constant) and node.left.value==0:raise Unsafe('零不能取负整数幂')
            return a**power
        b=interpret(node.right,env,engine)
        if isinstance(node.op,ast.Add):return a+b
        if isinstance(node.op,ast.Sub):return a-b
        if isinstance(node.op,ast.Mult):return a*b
        if isinstance(node.op,ast.Div):
            if engine=='z3' and not isinstance(node.right,ast.Constant):raise Unsafe('Z3 除法暂限非零数值常量；请改为乘法约束并明确分母范围')
            if isinstance(node.right,ast.Constant) and node.right.value==0:raise Unsafe('分母不能为零')
            return a/b
    if isinstance(node,ast.UnaryOp):
        a=interpret(node.operand,env,engine)
        if isinstance(node.op,ast.Not):
            if engine=='quantity' and not isinstance(a,bool):raise Unsafe('not 只能用于布尔变量或关系')
            return z3.Not(a) if engine=='z3' else sp.Not(a) if engine=='symbolic' else not a
        return -a if isinstance(node.op,ast.USub) else a
    if isinstance(node,ast.Compare):
        values=[interpret(node.left,env,engine)]+[interpret(n,env,engine) for n in node.comparators];results=[]
        for a,b,op in zip(values,values[1:],node.ops):
            if engine=='quantity':
                # Literal zero is a unit-polymorphic boundary, not an invented parameter.
                if getattr(a,'dimensionless',False) and a.magnitude==0:a=registry().Quantity(0,getattr(b,'units',''))
                if getattr(b,'dimensionless',False) and b.magnitude==0:b=registry().Quantity(0,getattr(a,'units',''))
                if hasattr(a,'dimensionality') and hasattr(b,'dimensionality') and a.dimensionality!=b.dimensionality:raise Unsafe('单位不兼容，不能比较不同物理量')
            if engine=='symbolic':
                f={ast.Eq:sp.Eq,ast.NotEq:sp.Ne,ast.Lt:sp.Lt,ast.LtE:sp.Le,ast.Gt:sp.Gt,ast.GtE:sp.Ge}[type(op)];r=f(a,b)
            else:r={ast.Eq:lambda:a==b,ast.NotEq:lambda:a!=b,ast.Lt:lambda:a<b,ast.LtE:lambda:a<=b,ast.Gt:lambda:a>b,ast.GtE:lambda:a>=b}[type(op)]()
            results.append(r)
        return z3.And(*results) if engine=='z3' else sp.And(*results) if engine=='symbolic' else all(results)
    if isinstance(node,ast.BoolOp):
        values=[interpret(n,env,engine) for n in node.values]
        if engine=='quantity' and any(not isinstance(v,bool) for v in values):raise Unsafe('and / or 需要布尔关系')
        if engine=='z3':return z3.And(*values) if isinstance(node.op,ast.And) else z3.Or(*values)
        if engine=='symbolic':return sp.And(*values) if isinstance(node.op,ast.And) else sp.Or(*values)
        return all(values) if isinstance(node.op,ast.And) else any(values)
    if isinstance(node,ast.Call):
        values=[interpret(n,env,engine) for n in node.args];f=node.func.id
        if f=='sqrt':
            if len(values)!=1 or engine=='z3':raise Unsafe('sqrt 只用于公式计算且需要一个参数')
            return sp.sqrt(values[0]) if engine=='symbolic' else values[0]**.5
        if f=='abs':
            if len(values)!=1:raise Unsafe('abs 需要一个参数')
            return z3.If(values[0]>=0,values[0],-values[0]) if engine=='z3' else sp.Abs(values[0]) if engine=='symbolic' else abs(values[0])
        if engine=='symbolic':return (sp.Min if f=='min' else sp.Max)(*values)
        if engine=='z3':
            a=values[0]
            for b in values[1:]:a=z3.If(a<b if f=='min' else a>b,a,b)
            return a
        return (min if f=='min' else max)(values)
    raise Unsafe('不支持的表达式')

def evaluate(text,env,engine='quantity'):return interpret(check(text,set(env)),env,engine)


def condition(text,env):
    value=evaluate(text,env)
    if not isinstance(value,bool):raise Unsafe("适用条件必须是布尔变量或比较关系")
    return value
