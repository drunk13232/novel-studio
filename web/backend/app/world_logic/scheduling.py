"""Official CP-SAT intervals/cumulative resources, bounded and data-only."""
from .expressions import evaluate, registry, unit, Missing, Unsafe

def solve(definition,env):
    try:from ortools.sat.python import cp_model
    except ImportError:raise Missing('此实验需要 OR-Tools 排程求解器；手动写作和其他实验仍可使用。')
    import networkx as nx
    config=definition['schedule'];tick=config['tick_unit'];horizon=config['horizon'];model=cp_model.CpModel()
    def integer(expression,time=False):
        quantity=evaluate(expression,env).to(unit(tick if time else 'dimensionless'));value=float(quantity.magnitude)
        if not value.is_integer() or not 1<=value<=1000000:raise Unsafe('排程时间/容量需在所选刻度下为 1 到 1000000 的整数；请显式调整刻度，不自动四舍五入。')
        return int(value)
    capacities={r['id']:integer(r['capacity']) for r in config['resources']};starts={};ends={};intervals={};durations={};demands={}
    graph=nx.DiGraph();graph.add_nodes_from(o['id'] for o in config['operations']);graph.add_edges_from((p,o['id']) for o in config['operations'] for p in o['predecessors'])
    if not nx.is_directed_acyclic_graph(graph):return {'status':'INFEASIBLE','reason':'排程声明的严格前置关系有环','cycle':list(nx.find_cycle(graph))},None
    for op in config['operations']:
        id=op['id'];duration=integer(op['duration'],True);demand=integer(op['demand']);durations[id]=duration;demands[id]=demand
        starts[id]=model.new_int_var(op['release'],horizon,'start_'+id);ends[id]=model.new_int_var(0,horizon,'end_'+id)
        intervals[id]=model.new_interval_var(starts[id],duration,ends[id],id)
        if op['deadline'] is not None:model.add(ends[id]<=op['deadline'])
    for op in config['operations']:
        for p in op['predecessors']:model.add(starts[op['id']]>=ends[p])
    for resource,capacity in capacities.items():
        ops=[o for o in config['operations'] if o['resource']==resource]
        model.add_cumulative([intervals[o['id']] for o in ops],[demands[o['id']] for o in ops],capacity)
    makespan=model.new_int_var(0,horizon,'makespan');model.add_max_equality(makespan,list(ends.values()));model.minimize(makespan)
    seed=definition.get('seed') or 0
    if seed>2**31-1:raise Unsafe('CP-SAT Seed 最大为 2147483647')
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=3;solver.parameters.num_search_workers=1;solver.parameters.random_seed=seed
    answer=solver.solve(model);status=solver.status_name(answer)
    report={'status':status,'tick_unit':tick,'horizon':horizon,'capacities':capacities,'operations':[],'wall_seconds':solver.wall_time,'effective_seed':seed,'workers':1,'acceptance_evaluation':'验收针对本次求得的排程；任意验收表达式未全部编译为排程约束','interpretation':'仅验证声明的整数刻度、工期、资源容量和前置关系。可行排程不证明现实工厂或经济总体可行。'}
    if answer in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        for op in config['operations']:report['operations'].append({'id':op['id'],'name':op['name'],'start':solver.value(starts[op['id']]),'end':solver.value(ends[op['id']]),'duration':durations[op['id']],'resource':op['resource'],'demand':demands[op['id']],'source_ids':op.get('source_ids',[])})
        report['makespan']=solver.value(makespan);return report,registry().Quantity(report['makespan'],unit(tick))
    return report,None
