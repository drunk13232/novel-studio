"""Portable data contract. A frozen experiment is not a Canon assertion."""
import json, math, re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from jsonschema import Draft202012Validator
from app.errors import ConsoleError

IDENT = r'^[A-Za-z][A-Za-z0-9_]{0,47}$'
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
class SourceFact(Strict):
    id: str = Field(max_length=80)
    name: str = Field(max_length=100)
    value: float | bool | str | None = None
    unit: str = Field(default='',max_length=80)
class Source(Strict):
    id: str = Field(pattern=IDENT)
    type: Literal['entity','character','event','chapter','clue','reference','manual'] = 'manual'
    target_id: str = Field(default='', max_length=100)
    name: str = Field(default='', max_length=200)
    basis: Literal['AUTHOR_CONFIRMED','COMMITTED','REFERENCE','ASSUMPTION','UNKNOWN'] = 'UNKNOWN'
    sha256: str = Field(default='', pattern=r'^(?:[a-f0-9]{64})?$')
    excerpt: str = Field(default='', max_length=2000)
    facts: list[SourceFact] = Field(default_factory=list,max_length=32)
class Input(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1, max_length=100)
    kind: Literal['real','integer','boolean'] = 'real'
    role: Literal['input','decision'] = 'input'
    value: float | bool | None = None
    unit: str = Field(default='dimensionless', max_length=80)
    minimum: float | None = None
    maximum: float | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=8)
    note: str = Field(default='', max_length=400)
    basis: Literal['AUTHOR','CANON','REFERENCE','DEMO','AI_PROPOSED','SCENARIO','UNKNOWN'] = 'UNKNOWN'
    @model_validator(mode='after')
    def bounds(self):
        if self.kind=='boolean' and (self.minimum is not None or self.maximum is not None):raise ValueError('布尔值不使用数值范围')
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum: raise ValueError('变量范围倒置')
        if self.value is not None:
            if self.kind=='boolean' and not isinstance(self.value,bool):raise ValueError('布尔变量需 true / false')
            if self.kind!='boolean' and isinstance(self.value,bool):raise ValueError('数值变量不能使用布尔值')
            if self.kind=='integer' and self.value!=int(self.value):raise ValueError('整数变量不能含小数')
            if not isinstance(self.value,bool) and abs(self.value)>1e15:raise ValueError('数值过大')
            if self.minimum is not None and self.value<self.minimum or self.maximum is not None and self.value>self.maximum:raise ValueError('数值不在作者范围内')
        if self.role=='decision' and self.value is not None:raise ValueError('待求解变量不设置固定值')
        return self
class Assumption(Strict):
    id: str = Field(pattern=IDENT)
    text: str = Field(min_length=1,max_length=1200)
    origin: Literal['AUTHOR','DEMO','AI_PROPOSED','UNKNOWN'] = 'UNKNOWN'
    accepted: bool = False
class Constraint(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1,max_length=100)
    expression: str = Field(min_length=1,max_length=800)
    meaning: str = Field(default='',max_length=1200)
    condition: str = Field(default='',max_length=800)
    source_ids: list[str] = Field(default_factory=list,max_length=8)
class Output(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1,max_length=100)
    expression: str = Field(min_length=1,max_length=800)
    unit: str = Field(default='dimensionless',max_length=80)
class Acceptance(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1,max_length=100)
    type: Literal['HARD','RANGE','RELATIONAL','DIMENSIONAL','CONDITIONAL','QUALITATIVE'] = 'HARD'
    expression: str = Field(default='',max_length=800)
    target: str = Field(default='',max_length=48)
    minimum: float | None = None
    maximum: float | None = None
    unit: str = Field(default='dimensionless',max_length=80)
    condition: str = Field(default='',max_length=800)
    basis: str = Field(default='',max_length=1200)
    applicability: str = Field(default='',max_length=500)
    origin: Literal['AUTHOR','CANON','REFERENCE','AI_PROPOSED','UNKNOWN'] = 'UNKNOWN'
    severity: Literal['HARD','WARNING','INFO'] = 'HARD'
    automatic: bool = True
    source_ids: list[str] = Field(default_factory=list,max_length=8)
    @model_validator(mode='after')
    def complete(self):
        if self.type=='RANGE' and (not self.target or self.minimum is None and self.maximum is None):raise ValueError('区间验收需要目标与阈值')
        if self.minimum is not None and self.maximum is not None and self.minimum>self.maximum:raise ValueError('验收区间倒置')
        if self.type=='CONDITIONAL' and not self.condition:raise ValueError('条件验收需要适用条件')
        if self.automatic and self.type not in ['RANGE','DIMENSIONAL','QUALITATIVE'] and self.target!='dependencies' and not self.expression:raise ValueError('验收需要声明式表达式')
        return self
class EventTime(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1,max_length=100)
    clock: str = Field(default='gregorian',min_length=1,max_length=80)
    time: str = Field(default='',max_length=80)
    earliest: str = Field(default='',max_length=80)
    latest: str = Field(default='',max_length=80)
    coordinate: float | None = Field(default=None,ge=-1e15,le=1e15)
    narrative_order: int | None = None
    basis: Literal['AUTHOR_CONFIRMED','COMMITTED','REFERENCE','ASSUMPTION','UNKNOWN'] = 'UNKNOWN'
    source_ids: list[str] = Field(default_factory=list,max_length=8)
class ResourceCapacity(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1,max_length=100)
    capacity: str = Field(min_length=1,max_length=800)
    source_ids: list[str] = Field(default_factory=list,max_length=8)
class ScheduledOperation(Strict):
    id: str = Field(pattern=IDENT)
    name: str = Field(min_length=1,max_length=100)
    duration: str = Field(min_length=1,max_length=800)
    resource: str = Field(pattern=IDENT)
    demand: str = Field(default='1',max_length=800)
    predecessors: list[str] = Field(default_factory=list,max_length=16)
    release: int = Field(default=0,ge=0,le=1000000)
    deadline: int | None = Field(default=None,ge=1,le=1000000)
    source_ids: list[str] = Field(default_factory=list,max_length=8)
class Schedule(Strict):
    tick_unit: str = Field(default='hour',max_length=80)
    horizon: int = Field(default=48,ge=1,le=1000000)
    resources: list[ResourceCapacity] = Field(min_length=1,max_length=16)
    operations: list[ScheduledOperation] = Field(min_length=1,max_length=48)
    @model_validator(mode='after')
    def references(self):
        resources={r.id for r in self.resources};ops={o.id for o in self.operations}
        if len(resources)!=len(self.resources) or len(ops)!=len(self.operations):raise ValueError('排程标识重复')
        for o in self.operations:
            if o.resource not in resources or any(p not in ops for p in o.predecessors):raise ValueError('排程资源或前置作业无法解析')
        return self
class Dependency(Strict):
    id: str = Field(pattern=IDENT)
    before: str = Field(pattern=IDENT)
    after: str = Field(pattern=IDENT)
    meaning: str = Field(default='',max_length=300)
    kind: Literal['strict_order','availability','causal','association'] = 'strict_order'
    condition: str = Field(default='',max_length=800)
    source_ids: list[str] = Field(default_factory=list,max_length=8)
class Sweep(Strict):
    variable: str = Field(pattern=IDENT)
    minimum: float
    maximum: float
    samples: int = Field(default=8,ge=2,le=32)
class Experiment(Strict):
    schema_version: Literal['1.0'] = '1.0'
    experiment_id: str = Field(pattern=r'^exp_[0-9a-f]{32}$')
    name: str = Field(min_length=1,max_length=200)
    description: str = Field(default='',max_length=4000)
    experiment_type: Literal['logic','time_space','physics','resources','world_rules','counterfactual','custom'] = 'custom'
    solver: Literal['z3','graph','formula','schedule'] = 'formula'
    inputs: list[Input] = Field(default_factory=list,max_length=48)
    assumptions: list[Assumption] = Field(default_factory=list,max_length=32)
    constraints: list[Constraint] = Field(default_factory=list,max_length=64)
    acceptance_rules: list[Acceptance] = Field(default_factory=list,max_length=48)
    outputs: list[Output] = Field(default_factory=list,max_length=32)
    source_references: list[Source] = Field(default_factory=list,max_length=24)
    dependencies: list[Dependency] = Field(default_factory=list,max_length=100)
    events: list[EventTime] = Field(default_factory=list,max_length=64)
    schedule: Schedule | None = None
    sensitivity: Sweep | None = None
    baseline_id: str = Field(default='',pattern=r'^(?:exp_[0-9a-f]{32})?$')
    baseline_version: int | None = Field(default=None,ge=1)
    baseline_fingerprint: str = Field(default='',pattern=r'^(?:[a-f0-9]{64})?$')
    baseline_acceptance_fingerprint: str = Field(default='',pattern=r'^(?:[a-f0-9]{64})?$')
    scenario_note: str = Field(default='',max_length=1200)
    seed: int | None = Field(default=None,ge=0,le=2**32-1)
    limitations: list[str] = Field(default_factory=list,max_length=24)
    steps: list[str] = Field(default_factory=list,max_length=16)
    @model_validator(mode='after')
    def references(self):
        for group in [self.inputs,self.constraints,self.acceptance_rules,self.outputs,self.assumptions,self.dependencies,self.events,self.source_references]:
            ids=[v.id for v in group]
            if len(ids)!=len(set(ids)):raise ValueError('同一类别存在重复 ID')
        ids={v.id for v in self.inputs}
        if ids & {v.id for v in self.outputs}:raise ValueError('输入与输出 ID 冲突')
        source_ids={v.id for v in self.source_references}
        if any(s not in source_ids for group in [self.inputs,self.constraints,self.acceptance_rules,self.dependencies,self.events] for v in group for s in v.source_ids):raise ValueError('来源 ID 无法解析')
        if self.sensitivity and self.sensitivity.minimum>self.sensitivity.maximum:raise ValueError('扫描范围倒置')
        if self.sensitivity and self.sensitivity.variable not in ids:raise ValueError('参数扫描变量不存在')
        if self.solver=='schedule' and self.schedule is None:raise ValueError('排程求解器需要声明资源与作业')
        if self.schedule and any(s not in source_ids for v in [*self.schedule.resources,*self.schedule.operations] for s in v.source_ids):raise ValueError('排程来源无法解析')
        if self.baseline_id==self.experiment_id:raise ValueError('反事实不能覆盖 Baseline')
        return self

def schema():
    value=Experiment.model_json_schema();value['$schema']='https://json-schema.org/draft/2020-12/schema'
    value['$id']='https://novel-studio.example/schemas/world-experiment-1.0.json'
    return value
VALIDATOR=Draft202012Validator(schema())
def validate(value):
    try:
        data=json.loads(json.dumps(value,allow_nan=False))
        if len(json.dumps(data,ensure_ascii=False).encode())>160000:raise ValueError('实验定义超过 160 KB')
        VALIDATOR.validate(data)
        model=Experiment.model_validate(data)
        from .expressions import check, unit
        names={v.id for v in model.inputs}|{v.id for v in model.outputs}
        if model.schedule:
            if 'schedule_makespan' in names:raise ValueError('schedule_makespan 是排程保留结果')
            names.add('schedule_makespan')
            if unit(model.schedule.tick_unit).dimensionality != unit('second').dimensionality:raise ValueError('排程刻度必须是时间单位')
            for v in model.schedule.resources:check(v.capacity,names)
            for v in model.schedule.operations:
                check(v.duration,names);check(v.demand,names)
        for v in model.inputs:
            unit(v.unit)
            if v.kind=='boolean' and v.unit not in ['','dimensionless']:raise ValueError('布尔变量没有物理单位')
        for v in [*model.constraints,*model.outputs,*model.acceptance_rules,*model.dependencies]:
            try:
                if getattr(v,'expression',''):check(v.expression,names)
                if getattr(v,'condition',''):check(v.condition,names)
            except Exception as error:raise ValueError('规则 '+v.id+' 的表达式无效：'+str(error).splitlines()[0]) from error
            if hasattr(v,'unit'):unit(v.unit)
        return model.model_dump()
    except ConsoleError:raise
    except Exception as e:
        raise ConsoleError('实验格式或规则无效：'+(str(e).splitlines() or [type(e).__name__])[0][:350],422) from e

class Save(Strict):
    definition: Experiment
    etag: str = Field(default='',max_length=64)
class Freeze(Strict):
    etag: str = Field(min_length=64,max_length=64)
    reason: str = Field(min_length=1,max_length=500)
    confirm: Literal[True]
class Run(Strict):
    version: int = Field(ge=1)
    fingerprint: str = Field(min_length=64,max_length=64)
    timeout_seconds: int = Field(default=20,ge=3,le=60)
class Design(Strict):
    instruction: str = Field(min_length=1,max_length=6000)
    mode: Literal['design','acceptance','adversarial','explain','rebuild','rebuttal'] = 'design'
    strength: Literal['explore','strict','extreme'] = 'explore'
    experiment_id: str | None = Field(default=None,pattern=r'^exp_[0-9a-f]{32}$')
    report_id: str | None = Field(default=None,pattern=r'^run_[0-9a-f]{32}$')
    source_ids: list[str] = Field(default_factory=list,max_length=8)
    selected_text: str = Field(default='',max_length=6000)
    model: str | None = Field(default=None,max_length=250)
class CounterexampleValue(Strict):
    variable: str = Field(pattern=IDENT)
    value: float | bool | None = None
class Finding(Strict):
    title: str
    evidence_source_ids: list[str]
    condition: str
    gap: str
    suggestion: str
    classification: Literal['POSSIBLE','FORMALIZABLE','QUALITATIVE','CONDITIONAL_RISK','MISSING_INFORMATION']
    severity: Literal['HIGH','MEDIUM','INFO'] = 'INFO'
    counterexample_inputs: list[CounterexampleValue] = Field(default_factory=list,max_length=16)
    rule_ids: list[str] = Field(default_factory=list,max_length=16)
    tradeoffs: str = Field(default='',max_length=1200)
class Proposal(Strict):
    experiment: Experiment | None = None
    questions: list[str] = Field(default_factory=list,max_length=3)
    missing_parameters: list[str]
    findings: list[Finding]
    explanation: str
    limitations: list[str]
    extra_materials: list[str]

# Compact inference contract; application expands it into the portable format.
# No model-generated path, credential, project ID or executable adapter name.
class AIInput(Strict):
    id:str=Field(pattern=IDENT)
    name:str
    kind:Literal['real','integer','boolean']='real'
    role:Literal['input','decision']='input'
    value:float|bool|None=None
    unit:str='dimensionless'
class AIRule(Strict):
    id:str=Field(pattern=IDENT)
    name:str
    type:Literal['HARD','RANGE','RELATIONAL','DIMENSIONAL','CONDITIONAL','QUALITATIVE']='HARD'
    expression:str=''
    target:str=''
    minimum:float|None=None
    maximum:float|None=None
    unit:str='dimensionless'
    condition:str=''
    basis:str=''
class AIExperiment(Strict):
    name:str
    description:str
    experiment_type:Literal['logic','time_space','physics','resources','world_rules','counterfactual','custom']
    solver:Literal['z3','graph','formula','schedule']
    inputs:list[AIInput]=Field(max_length=16)
    assumptions:list[str]=Field(max_length=8)
    constraints:list[Constraint]=Field(max_length=12)
    outputs:list[Output]=Field(max_length=8)
    acceptance_rules:list[AIRule]=Field(max_length=8)
    dependencies:list[Dependency]=Field(max_length=12)
    events:list[EventTime]=Field(default_factory=list,max_length=12)
    schedule:Schedule|None=None
    limitations:list[str]
    steps:list[str]
class AIProposal(Strict):
    experiment:AIExperiment|None
    questions:list[str]=Field(max_length=3)
    missing_parameters:list[str]
    findings:list[Finding]=Field(max_length=8)
    explanation:str
    limitations:list[str]
    extra_materials:list[str]
