"""Bounded request controls over existing AI preferences and source services.

This module selects data, not permissions. Callers must supply only sources
already authorized by their Writer/author service. No files, model calls or DB.
"""
import copy,hashlib,json
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from app.errors import ConsoleError
from app.ai.models import Parameters

VERSION='ai-context-1'
class ContextPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode:Literal['auto','manual','hybrid']='hybrid'
    budget:int=Field(default=32768,ge=1024,le=2000000)
    output_reserve:int=Field(default=4096,ge=0,le=1000000)
    reasoning_reserve:int=Field(default=0,ge=0,le=1000000)
    history:Literal['auto','messages','turns','tokens','all','manual','off']='auto'
    history_limit:int=Field(default=12,ge=1,le=1000)
    history_tokens:int=Field(default=8192,ge=0,le=1000000)
    include:list[str]=Field(default_factory=list,max_length=2000)
    exclude:list[str]=Field(default_factory=list,max_length=2000)
    pins:list[str]=Field(default_factory=list,max_length=2000)
    priorities:dict[str,int]=Field(default_factory=dict,max_length=2000)
    category_budgets:dict[str,int]=Field(default_factory=dict,max_length=20)
    @model_validator(mode='after')
    def valid(self):
        if set(self.pins)&set(self.exclude):raise ValueError('固定内容不能同时排除')
        if any(not 0<=v<=100 for v in self.priorities.values()):raise ValueError('优先级必须在 0～100 之间')
        if any(not 0<=v<=2000000 for v in self.category_budgets.values()):raise ValueError('类别预算超出范围')
        return self

class RequestControls(BaseModel):
    model_config=ConfigDict(extra='forbid')
    model:str|None=Field(default=None,max_length=300)
    parameters:dict[str,Any]=Field(default_factory=dict,max_length=14)
    context:ContextPolicy=Field(default_factory=ContextPolicy)
    max_cost:float|None=Field(default=None,gt=0,le=100000)
    max_turns:int=Field(default=1,ge=1,le=20)
    retries:Literal[0]=0
    @field_validator('parameters')
    @classmethod
    def valid_parameters(cls,value):
        Parameters.model_validate(value)
        return value

class ControlSave(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scope:Literal['global','project','feature','session']='feature'
    project:str=''
    feature:str=Field(default='brainstorm',pattern=r'^[a-z][a-z0-9_-]{0,79}$')
    session:str=Field(default='',max_length=100,pattern=r'^[a-zA-Z0-9_-]*$')
    value:dict=Field(default_factory=dict)
    @field_validator('value')
    @classmethod
    def valid_value(cls,value):
        # Partial overrides retain lower-priority defaults. Unknown keys fail.
        RequestControls.model_validate(value)
        return value

def merge(*layers):
    result={}
    for layer in layers:
        for key,value in (layer or {}).items():
            result[key]=merge(result.get(key,{}),value) if isinstance(value,dict) else copy.deepcopy(value)
    return result

def estimate(text):
    """Conservative UTF-8 byte upper estimate, never claimed as a tokenizer."""
    return len(str(text).encode('utf8'))+8

def item(id,category,title,content,*,required=False,locked=False,source='',revision='',priority=50,**meta):
    return dict(id=id,category=category,title=title,content=content,required=required,
                locked=locked,source=source,revision=str(revision),priority=priority,**meta)

def render(items):
    # Stable serialization is the very payload consumed by the adapter.
    return '\n'.join(json.dumps({'source_id':v['id'],'category':v['category'],'revision':v['revision'],'content':v['content']},ensure_ascii=False,separators=(',',':')) for v in items)

def build(items,policy:ContextPolicy,model_limit=None,output_limit=None,overhead=0):
    if len(items)>3000:raise ConsoleError('上下文来源超过 3000 项，请缩小范围',413)
    ids=[i['id'] for i in items]
    if len(ids)!=len(set(ids)):raise ConsoleError('上下文来源 ID 重复',422)
    # A selected source removed upstream may be stale. Never silently omit pins.
    if set(policy.pins)-set(ids):raise ConsoleError('固定来源已不可用或不在本次授权范围，请重新选择',409)
    budget=min(policy.budget,model_limit) if model_limit else policy.budget
    reserve=max(policy.output_reserve,output_limit or 0)+policy.reasoning_reserve
    available=budget-reserve-overhead
    if available<=0:raise ConsoleError('输出、推理预留与必要指令已占满上下文预算，请调整预算或预留',422)
    rows=copy.deepcopy(items);excluded=[];eligible=[]
    history=[r for r in rows if r['category']=='history']
    limit=policy.history_limit*(2 if policy.history=='turns' else 1)
    recent={r['id'] for r in history[-limit:]} if policy.history in {'auto','messages','turns'} else set(ids)
    for i,r in enumerate(rows):
        r['index']=i;r['pinned']=r.get('locked',False) or r['id'] in policy.pins
        r['estimated_tokens']=estimate(render([r]));reason=None
        if r.get('required') and r['id'] in policy.exclude:raise ConsoleError('本次任务必要内容不能移除',422)
        if not r.get('required') and not r['pinned']:
            if r['id'] in policy.exclude:reason='AUTHOR_EXCLUDED'
            elif policy.mode=='manual' and r['id'] not in policy.include:reason='NOT_SELECTED'
            elif r['category']=='history':
                if policy.history=='off':reason='HISTORY_DISABLED'
                elif policy.history=='manual' and r['id'] not in policy.include:reason='HISTORY_NOT_SELECTED'
                elif r['id'] not in recent and r['id'] not in policy.include:reason='OUTSIDE_HISTORY_RANGE'
        if reason:excluded.append({**r,'reason':reason})
        else:eligible.append(r)
    fixed=[r for r in eligible if r.get('required') or r['pinned']]
    used=estimate(render(sorted(fixed,key=lambda r:r['index'])))
    if used>available:raise ConsoleError('必要内容或固定资料超过预算；未删除固定规则、未扩大预算、未发送请求',422)
    selected=fixed[:];by_category={}
    for r in fixed:by_category[r['category']]=by_category.get(r['category'],0)+r['estimated_tokens']
    rest=sorted([r for r in eligible if r not in fixed],key=lambda r:(-policy.priorities.get(r['id'],r.get('priority',50)),-r['index']))
    for r in rest:
        cap=policy.category_budgets.get(r['category'])
        if r['category']=='history' and policy.history=='tokens':cap=min(cap,policy.history_tokens) if cap is not None else policy.history_tokens
        reason=None
        if cap is not None and by_category.get(r['category'],0)+r['estimated_tokens']>cap:reason='CATEGORY_BUDGET'
        elif estimate(render(sorted([*selected,r],key=lambda v:v['index'])))>available:reason='TOTAL_BUDGET'
        if reason:excluded.append({**r,'reason':reason})
        else:selected.append(r);by_category[r['category']]=by_category.get(r['category'],0)+r['estimated_tokens']
    selected.sort(key=lambda r:r['index']);payload=render(selected)
    return {'version':VERSION,'prompt':payload,'prompt_sha256':hashlib.sha256(payload.encode()).hexdigest(),
            'model_limit':model_limit,'user_budget':policy.budget,'effective_budget':budget,
            'input_estimate':estimate(payload)+overhead,'output_reserve':max(policy.output_reserve,output_limit or 0),
            'reasoning_reserve':policy.reasoning_reserve,'overhead_estimate':overhead,'estimator':'UTF8_BYTE_UPPER_ESTIMATE',
            'items':selected,'excluded':excluded,'category_estimates':by_category,
            'note':'估算不等于服务商计数。预留不保证模型实际输出或思考 Token；Codex 内部工具结果与服务端注入不可见。'}

def receipt(packet):
    """Small, content-free task provenance. User-visible source text stays local."""
    return {k:v for k,v in packet.items() if k not in {'prompt','items','excluded'}}|{
        'sources':[{k:v for k,v in i.items() if k in {'id','category','title','source','revision','pinned','estimated_tokens'}} for i in packet['items']],
        'excluded':[{k:v for k,v in i.items() if k in {'id','category','title','reason','estimated_tokens'}} for i in packet['excluded']]}
