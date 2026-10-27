"""Bounded mature solver adapters. Runs only in a disposable child process."""
import copy, json, math, platform, time
from datetime import datetime, timezone
from importlib.metadata import version
from .models import validate
from .expressions import evaluate, registry, unit, Missing, Unsafe, condition
ADAPTER_VERSION='1.1'
ADAPTERS=[{'extension_id':'builtin.'+id,'name':name,'version':ADAPTER_VERSION,'experiment_types':types,'input_schema':'world-experiment-1.0.json','output_schema':'world-report-1.0.json','engine_type':id,'requirements':[dep],'license':license,'enabled':True} for id,name,types,dep,license in [
 ('z3','Z3 约束验证',['logic','time_space','world_rules','custom'],'z3-solver','MIT'),
 ('graph','NetworkX 事件依赖',['time_space','logic','custom'],'networkx','BSD-3-Clause'),
 ('schedule','OR-Tools 有限资源排程',['resources','time_space','custom'],'ortools','Apache-2.0'),
 ('formula','SymPy + Pint 公式与量纲',['physics','resources','time_space','world_rules','counterfactual','custom'],'sympy + pint','BSD-3-Clause')]]

def outcome(id,name,status,detail='',**extra):return {'id':id,'name':name,'status':status,'detail':detail,**extra}
def status_of(rows):
    states=[r['status'] for r in rows]
    if 'ERROR' in states:return 'ERROR'
    if 'FAIL' in states:return 'FAIL'
    if not states or any(s in ['INCONCLUSIVE','NOT RUN'] for s in states):return 'INCONCLUSIVE'
    return 'PASS'
def scalar(v):
    x=float(v)
    if not math.isfinite(x) or abs(x)>1e30:raise Unsafe('结果超出有限数值范围')
    return x

def formula(d,env,dimensions):
    import sympy as sp
    names={id:sp.Symbol(id,real=True) for id in env};rows=[];values=[]
    for v in d['outputs']:
        try:
            symbolic=evaluate(v['expression'],names,'symbolic');names[v['id']]=symbolic
            dim=evaluate(v['expression'],dimensions).to(unit(v['unit']));dimensions[v['id']]=dim
            result=evaluate(v['expression'],env).to(unit(v['unit']));env[v['id']]=result
            values.append({'id':v['id'],'name':v['name'],'value':scalar(result.magnitude),'unit':v['unit'],'expression':v['expression'],'symbolic':str(symbolic),'latex':sp.latex(symbolic),'status':'PASS'})
        except Missing as e:
            env[v['id']]=None;values.append({'id':v['id'],'name':v['name'],'value':None,'unit':v['unit'],'expression':v['expression'],'status':'INCONCLUSIVE','detail':str(e)})
        except Exception as e:
            env[v['id']]=None;rows.append(outcome('formula_'+v['id'],v['name'],'FAIL' if 'Dimensionality' in type(e).__name__ or isinstance(e,Unsafe) else 'ERROR',str(e)[:400],expression=v['expression']))
    return rows,values

def graph(d,env):
    import networkx as nx
    from .temporal import active_edges, check_times
    edges,unknown=active_edges(d,env);strict=[e for e in edges if e.get('kind','strict_order')=='strict_order']
    g=nx.DiGraph();g.add_edges_from((e['before'],e['after']) for e in strict)
    acyclic=nx.is_directed_acyclic_graph(g);cycle=list(nx.find_cycle(g)) if not acyclic else []
    ids=[e['id'] for e in strict if (e['before'],e['after']) in cycle]
    influence=nx.DiGraph();influence.add_edges_from((e['before'],e['after']) for e in edges if e.get('kind')=='causal')
    nodes=sorted({n for e in edges for n in [e['before'],e['after']]})
    return {'acyclic':acyclic,'order':list(nx.topological_sort(g)) if acyclic else [],'cycle':cycle,'conflicting_dependencies':ids,
        'nodes':[{'id':n,'affected':sorted(nx.descendants(influence,n)) if n in influence else []} for n in nodes], 'edges':edges,'uncertain_conditions':unknown,
        'time_results':check_times(d,edges),
        'causal_feedback_present':not nx.is_directed_acyclic_graph(influence),'interpretation':'仅 strict_order 的显式严格先后关系要求 DAG；普通关联不是因果。causal 路径只表示作者声明的依赖，不能自动推导未给公式的数量后果。'}

def range_expr(rule,env,engine):
    name=rule['target']
    if name not in env or env[name] is None:raise Missing('缺少验收目标：'+name)
    value=env[name];r=registry();parts=[]
    for k,op in [('minimum','>='),('maximum','<=')]:
        threshold=rule[k]
        if threshold is None:continue
        q=r.Quantity(threshold,unit(rule['unit']))
        b=q.to_base_units().magnitude if engine=='z3' else q.to(value.units).magnitude
        if engine=='quantity':a=scalar(value.magnitude)
        else:a=value
        parts.append(a>=b if op=='>=' else a<=b)
    if engine=='z3':
        import z3
        return z3.And(*parts)
    return all(parts)

def z3_run(d,env,dimensions):
    import z3
    s=z3.Solver();s.set(timeout=3000);s.set(max_memory=256)
    values={};raws={};units={};rows=[];tracked={}
    def add(id,name,expr,**meta):
        if not z3.is_bool(expr):raise Unsafe('逻辑约束必须返回布尔值')
        tag=z3.Bool('track_'+id);s.assert_and_track(expr,tag);tracked[str(tag)]={'id':id,'name':name,**meta}
    for v in d['inputs']:
        id=v['id'];raw=z3.Bool(id) if v['kind']=='boolean' else z3.Int(id) if v['kind']=='integer' else z3.Real(id);raws[id]=raw
        q=registry().Quantity(1,unit(v['unit']));scale=q.to_base_units().magnitude
        if registry().Quantity(0,unit(v['unit'])).to_base_units().magnitude!=0:raise Unsafe('约束求解不支持偏移单位，请使用绝对温标或线性单位')
        values[id]=raw if v['kind']=='boolean' else raw*z3.RealVal(str(scale));units[id]=scale
        if v['value'] is not None:add('value_'+id,v['name']+'固定输入',raw==v['value'],source_ids=v['source_ids'],expression=id+' == '+str(v['value']))
        elif v['role']=='input':raise Missing('缺少固定输入：'+id+'；仅作者明确标记的待求解变量可以未知')
        if v['minimum'] is not None:add('min_'+id,v['name']+'下限',raw>=v['minimum'])
        if v['maximum'] is not None:add('max_'+id,v['name']+'上限',raw<=v['maximum'])
    for v in d['outputs']:
        evaluate(v['expression'],dimensions).to(unit(v['unit']))
        values[v['id']]=evaluate(v['expression'],values,'z3')
    for c in d['constraints']:
        evaluate(c['expression'],dimensions)
        test=evaluate(c['expression'],values,'z3')
        if c.get('condition'):evaluate(c['condition'],dimensions);test=z3.Implies(evaluate(c['condition'],values,'z3'),test)
        add(c['id'],c['name'],test,expression=c['expression'],meaning=c['meaning'],source_ids=c['source_ids'])
    answer=s.check();proof={'status':str(answer).upper(),'model':{},'unsat_core':[],'unsat_core_is_minimal':False}
    if answer==z3.unsat:
        proof['unsat_core']=[tracked[str(t)] for t in s.unsat_core()]
        rows.append(outcome('constraints','输入与约束能否同时成立','FAIL','Z3 UNSAT：仅指这些形式化约束冲突，请复核自然语言映射。',conflicts=proof['unsat_core']))
        return rows,proof,[]
    if answer==z3.unknown:
        rows.append(outcome('constraints','约束求解','INCONCLUSIVE',s.reason_unknown()));return rows,proof,[]
    m=s.model();proof['model']={v['id']:{'value':str(m.eval(raws[v['id']],model_completion=True)),'unit':v['unit'],'role':v['role']} for v in d['inputs']}
    proof['interpretation']='SAT 是一组可行解，不是对世界观整体合理性的证明。模型中的待求解值不是角色知识或已发生事实。'
    for r in d['acceptance_rules']:
        if r['target']=='dependencies':continue
        if not r['automatic'] or r['type']=='QUALITATIVE':rows.append(outcome(r['id'],r['name'],'NOT RUN','定性意见需作者审阅，求解器不做文学证明。'));continue
        try:
            if r['target']=='dependencies':continue
            if r['type']=='DIMENSIONAL':evaluate(r['expression'],dimensions).to(unit(r['unit']));rows.append(outcome(r['id'],r['name'],'PASS','Pint 量纲一致'));continue
            if r['type']=='RANGE':
                dimensions[r['target']].to(unit(r['unit']));test=range_expr(r,values,'z3')
            else:
                evaluate(r['expression'],dimensions);test=evaluate(r['expression'],values,'z3')
            if r['condition']:
                evaluate(r['condition'],dimensions);test=z3.Implies(evaluate(r['condition'],values,'z3'),test)
            if not z3.is_bool(test):raise Unsafe('验收需要布尔关系')
            s.push();s.add(z3.Not(test));a=s.check()
            if a==z3.unsat:rows.append(outcome(r['id'],r['name'],'PASS','在当前已锁定输入和约束下成立。',basis=r['basis']))
            elif a==z3.sat:rows.append(outcome(r['id'],r['name'],'FAIL','存在违反验收的可行反例；这不等于所有情景都必然失败。',counterexample={v['id']:{'value':str(s.model().eval(raws[v['id']],model_completion=True)),'unit':v['unit']} for v in d['inputs']},basis=r['basis']))
            else:rows.append(outcome(r['id'],r['name'],'INCONCLUSIVE',s.reason_unknown()))
            s.pop()
        except Exception as e:rows.append(outcome(r['id'],r['name'],'INCONCLUSIVE' if isinstance(e,Missing) else 'FAIL' if 'Dimensionality' in type(e).__name__ or isinstance(e,Unsafe) else 'ERROR',str(e)[:400]))
    return rows,proof,[{'id':v['id'],'name':v['name'],'value':str(m.eval(values[v['id']],model_completion=True)),'unit':'SI base units','status':'PASS'} for v in d['outputs']]

def single(d):
    env={};dims={};rows=[];values=[];proof={}
    for v in d['inputs']:
        dims[v['id']]=True if v['kind']=='boolean' else registry().Quantity(2,unit(v['unit']))
        env[v['id']]=v['value'] if v['kind']=='boolean' else registry().Quantity(v['value'],unit(v['unit'])) if v['value'] is not None else None
    g=graph(d,env)
    rows.extend(g['time_results'])
    rows.extend(outcome('condition_'+e['id'],'依赖适用条件','INCONCLUSIVE',e['detail']) for e in g['uncertain_conditions'])
    unaccepted=[a['id'] for a in d['assumptions'] if not a['accepted']]
    if unaccepted:rows.append(outcome('assumptions','实验假设','INCONCLUSIVE','未接受的假设：'+', '.join(unaccepted)))
    try:
        if d['solver']=='z3':
            rows2,proof,values=z3_run(d,env,dims);rows.extend(rows2)
        else:
            if d['solver']=='schedule':
                from .scheduling import solve
                proof,finish=solve(d,env);env['schedule_makespan']=finish;dims['schedule_makespan']=registry().Quantity(2,unit(d['schedule']['tick_unit']))
                rows.append(outcome('schedule','有限资源排程','PASS' if proof['status'] in ['OPTIMAL','FEASIBLE'] else 'FAIL' if proof['status']=='INFEASIBLE' else 'INCONCLUSIVE',proof.get('reason') or proof['interpretation']))
            if d['solver'] in ['formula','schedule']:
                rows2,values=formula(d,env,dims);rows.extend(rows2)
                rows.extend(outcome(v['id'],v['name'],'INCONCLUSIVE',v.get('detail','')) for v in values if v['status']=='INCONCLUSIVE')
            for c in d['constraints']:
                try:
                    if c.get('condition') and not condition(c['condition'],env):rows.append(outcome(c['id'],c['name'],'PASS','适用条件未启用；未验证无条件命题。',applicable=False));continue
                    result=evaluate(c['expression'],env)
                    if not isinstance(result,bool):raise Unsafe('约束需要布尔关系')
                    rows.append(outcome(c['id'],c['name'],'PASS' if result else 'FAIL',c['meaning'],expression=c['expression'],source_ids=c['source_ids']))
                except Missing as e:rows.append(outcome(c['id'],c['name'],'INCONCLUSIVE',str(e)))
                except Exception as e:rows.append(outcome(c['id'],c['name'],'FAIL' if 'Dimensionality' in type(e).__name__ or isinstance(e,Unsafe) else 'ERROR',str(e)[:400]))
            for r in d['acceptance_rules']:
                if r['target']=='dependencies':continue
                try:
                    if not r['automatic'] or r['type']=='QUALITATIVE':rows.append(outcome(r['id'],r['name'],'NOT RUN','定性验收需作者审核。'));continue
                    if r['condition'] and not condition(r['condition'],env):rows.append(outcome(r['id'],r['name'],'PASS','适用条件未启用；条件式验收未触发，不证明原命题。',applicable=False));continue
                    if r['type']=='DIMENSIONAL':evaluate(r['expression'],dims).to(unit(r['unit']));result=True
                    else:result=range_expr(r,env,'quantity') if r['type']=='RANGE' else evaluate(r['expression'],env)
                    if not isinstance(result,bool):raise Unsafe('验收需要布尔关系')
                    rows.append(outcome(r['id'],r['name'],'PASS' if result else 'FAIL',r['basis'],expression=r['expression'],source_ids=r['source_ids']))
                except Missing as e:rows.append(outcome(r['id'],r['name'],'INCONCLUSIVE',str(e)))
                except Exception as e:rows.append(outcome(r['id'],r['name'],'FAIL' if 'Dimensionality' in type(e).__name__ or isinstance(e,Unsafe) else 'ERROR',str(e)[:400]))
    except Missing as e:rows.append(outcome('parameters','参数不完整','INCONCLUSIVE',str(e)))
    except Exception as e:rows.append(outcome('solver','求解错误','ERROR',str(e)[:400]))
    graph_rules=[r for r in d['acceptance_rules'] if r['target']=='dependencies']
    if d['solver']=='graph' and not any(r['automatic'] and r['type']!='QUALITATIVE' for r in graph_rules):rows.append(outcome('dependency','事件依赖','PASS' if g['acyclic'] else 'FAIL','NetworkX 拓扑顺序 / 有向环检查',conflicting_dependencies=g['conflicting_dependencies']))
    for r in graph_rules:
        if not r['automatic'] or r['type']=='QUALITATIVE':
            rows.append(outcome(r['id'],r['name'],'NOT RUN','等待作者人工验收；拓扑计算不能代替人工判断。',manual=True,basis=r['basis'],source_ids=r['source_ids']));continue
        try:
            if r['condition'] and not condition(r['condition'],env):
                rows.append(outcome(r['id'],r['name'],'PASS','适用条件未启用；没有验证无条件命题。',applicable=False));continue
            rows.append(outcome(r['id'],r['name'],'PASS' if g['acyclic'] else 'FAIL','仅检查显式依赖，未提供的时间与路程仍未知。',basis=r['basis'],source_ids=r['source_ids'],conflicting_dependencies=g['conflicting_dependencies']))
        except Missing as e:rows.append(outcome(r['id'],r['name'],'INCONCLUSIVE',str(e)))
        except Exception as e:rows.append(outcome(r['id'],r['name'],'ERROR',str(e)[:400]))
    # Missing parameters or UNSAT may short-circuit a solver; manual rules still remain pending.
    present={r['id'] for r in rows}
    for r in d['acceptance_rules']:
        if (not r['automatic'] or r['type']=='QUALITATIVE') and r['id'] not in present:
            rows.append(outcome(r['id'],r['name'],'NOT RUN','等待作者人工验收。',manual=True,basis=r['basis'],source_ids=r['source_ids']))
    if g['cycle'] and not graph_rules:rows.append(outcome('dependency','事件有向环','FAIL','存在不允许的依赖环',conflicting_dependencies=g['conflicting_dependencies']))
    if d['solver']=='schedule' and proof.get('status')=='FEASIBLE':
        for row in rows:
            if row['status']=='FAIL':row.update(status='INCONCLUSIVE',detail='当前找到的排程未通过；优化尚未证明最优，不能声称目标不可达。'+row.get('detail',''))
    if unaccepted:
        # Conditional calculations can be inspected but cannot be certified as author-approved.
        result='INCONCLUSIVE'
    else:result=status_of(rows)
    import ast, networkx as nx
    math_graph=nx.DiGraph();math_edges=[]
    for output in d['outputs']:
        refs=sorted({n.id for n in ast.walk(ast.parse(output['expression'],mode='eval')) if isinstance(n,ast.Name) and n.id in env})
        math_graph.add_edges_from((n,output['id']) for n in refs);math_edges.extend({'before':n,'after':output['id'],'basis':'DECLARED_FORMULA'} for n in refs)
    trace=[{'id':o['id'],'expression':o['expression'],'unit':o['unit'],'input_ids':sorted({n.id for n in ast.walk(ast.parse(o['expression'],mode='eval')) if isinstance(n,ast.Name) and n.id in env}),'result':next((v for v in values if v['id']==o['id']),None)} for o in d['outputs']]
    return {'status':result,'calculation_trace':trace,'model_influence':{'edges':math_edges,'affected_outputs':{v['id']:sorted(nx.descendants(math_graph,v['id'])) if v['id'] in math_graph else [] for v in d['inputs']},'basis':'Only explicit formula dependencies; associations excluded'},'acceptance_results':rows,'outputs':values,'solver_result':proof,'dependency_graph':g,'limitations':d['limitations']+['结果仅覆盖已执行的输入、公式和规则；不构成真实社会预测，也不自动成为 Canon。'],'unverified':[r['name'] for r in rows if r['status'] in ['NOT RUN','INCONCLUSIVE']]}

def run(definition):
    started=time.monotonic();d=validate(definition);report=single(d);scan=[]
    if d['sensitivity']:
        sweep=d['sensitivity'];v=next(v for v in d['inputs'] if v['id']==sweep['variable'])
        if d['solver']!='formula' or v['role']!='input' or v['kind']=='boolean':report['unverified'].append('敏感性扫描当前只支持明确公式及数值输入')
        else:
            for i in range(sweep['samples']):
                value=sweep['minimum']+(sweep['maximum']-sweep['minimum'])*i/(sweep['samples']-1)
                variant=copy.deepcopy(d);variant['sensitivity']=None;next(x for x in variant['inputs'] if x['id']==v['id'])['value']=value
                try:
                    result=single(validate(variant));scan.append({'parameter':value,'status':result['status'],'outputs':result['outputs']})
                except Exception as e:scan.append({'parameter':value,'status':'ERROR','detail':str(e)[:200],'outputs':[]})
            report['sensitivity']={'variable':v['id'],'unit':v['unit'],'samples':scan,'transitions':[{'from':a['parameter'],'to':b['parameter'],'status':b['status']} for a,b in zip(scan,scan[1:]) if a['status']!=b['status']],'interpretation':'离散采样，只覆盖已给公式；过渡区间不是精确临界点。'}
    report.update(schema_version='1.0',adapter_version=ADAPTER_VERSION,executed_at=datetime.now(timezone.utc).isoformat(),duration_seconds=round(time.monotonic()-started,4),solver_versions={dep:version(dep) for dep in ['z3-solver','networkx','sympy','pint','jsonschema']+(['ortools'] if d['solver']=='schedule' else [])},environment={'python':platform.python_version(),'platform':platform.system(),'machine':platform.machine()},seed=d['seed'],random_simulation=False)
    return report
