"""Rule-card views over Bible fields; no independent rule/Canon store."""
import json, math
from datetime import date,datetime,timezone
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from app.errors import ConsoleError

KINDS=['自然规律','物理','地理生态','魔法能力','政治制度','法律','经济制度','社会习俗','组织内部','技术限制','历史条件','文化','人物行动','作者自定义']
RELATIONS={'RULE_REQUIRES':'实际依赖','RULE_ASSOCIATED':'普通关联','RULE_CONDITIONAL':'条件性影响','RULE_AI_POSSIBLE':'AI 推测','RULE_OVERRIDES':'明确优先于'}

def template():
    rows=[('rule_kind','规则分类','select',KINDS),('rule_strength','硬规则 / 软规则','select',['HARD','SOFT']),('rule_scope','适用范围','select',['WORLD','ENTITY','PERIOD','SCENARIO']),('scope_ids','约束对象','entities',[]),('conditions','生效条件','longtext',[]),('exceptions','例外条件','longtext',[]),('confidence','可信状态','select',['AUTHOR_CONFIRMED','CONDITIONAL','UNKNOWN']),('calendar','时间坐标','text',[]),('assumptions','作者假设与尚缺条件','longtext',[]),('formal_model','受限数学映射（JSON）','longtext',[])]
    return {'id':'world_rule','name':'世界规则卡','group':'世界规则','description':'自然语言先行；硬软规则、范围、例外和证据分别记录。数学映射必须由作者确认后才执行。','fields':[{'id':id,'name':name,'type':'text' if id=='rule_kind' else kind,'options':options,'group':'数学验证' if id=='formal_model' else '适用条件','primary':id!='formal_model','help':'iso：公历日期/带时区时间；自定义纪年填写相同坐标名称，时间用有序数值。' if id=='calendar' else '数据定义，不执行 Python、脚本或 SQL。' if id=='formal_model' else ''} for id,name,kind,options in rows]}

def is_rule(entity):
    fields={f['id'] for f in (entity.get('template_snapshot') or {}).get('fields',[])}
    return entity.get('category')=='world_rule' or {'rule_strength','rule_scope'}<=fields

class RuleCard(BaseModel):
    model_config=ConfigDict(extra='forbid')
    rule_kind:str=Field(default='作者自定义',max_length=80)
    rule_strength:Literal['HARD','SOFT']='SOFT'
    rule_scope:Literal['WORLD','ENTITY','PERIOD','SCENARIO']='WORLD'
    scope_ids:list[str]=Field(default_factory=list,max_length=30)
    conditions:str=Field(default='',max_length=20000)
    exceptions:str=Field(default='',max_length=20000)
    confidence:Literal['AUTHOR_CONFIRMED','CONDITIONAL','UNKNOWN']='UNKNOWN'
    calendar:str=Field(default='iso',max_length=80)
    assumptions:str=Field(default='',max_length=20000)
    formal_model:str=Field(default='',max_length=20000)

def card(entity):
    return RuleCard.model_validate({k:v for k,v in entity.get('fields',{}).items() if k in RuleCard.model_fields and v not in (None,'',[])}).model_dump()

def coordinate(value,calendar='iso'):
    if not value:return None
    try:
        if calendar!='iso':
            n=float(value)
            return ('ordinal:'+calendar,n) if math.isfinite(n) else None
        if len(value)==10:return ('iso-date',date.fromisoformat(value).toordinal())
        v=datetime.fromisoformat(value.replace('Z','+00:00'))
        if v.tzinfo is None:return None
        return ('iso-instant',v.astimezone(timezone.utc).timestamp())
    except (ValueError,TypeError,OverflowError):return None

def interval(start,end,at,calendar='iso'):
    point=coordinate(at,calendar);a=coordinate(start,calendar);b=coordinate(end,calendar)
    if not point or start and not a or end and not b:return 'UNKNOWN'
    if any(v and v[0]!=point[0] for v in [a,b]):return 'UNKNOWN'
    if a and b and a[1]>=b[1]:return 'UNKNOWN'
    return 'OUTSIDE' if a and point[1]<a[1] or b and point[1]>=b[1] else 'MATCH'

def historical(entity,at,calendar='iso'):
    """Story-time periods are author records, independent from editing timestamps."""
    periods=entity.get('periods',[])
    def state(p):return interval(p.get('story_start',''),p.get('story_end',''),at,calendar) if p.get('story_start') or p.get('story_end') else 'UNKNOWN'
    matched=[p for p in periods if p.get('confirmed') and p.get('calendar','iso')==calendar and state(p)=='MATCH']
    unknown=[p for p in periods if p.get('confirmed') and p.get('calendar','iso')==calendar and state(p)=='UNKNOWN']
    if len(matched)>1:return {'status':'CONFLICT','periods':matched,'facts':{},'reason':'多个作者确认时期重叠，不以编辑时间决定优先级'}
    if unknown:return {'status':'UNKNOWN','periods':matched,'facts':{},'reason':'相关时期边界无法确定，不能排除冲突'}
    if len(matched)==1:return {'status':'VERIFIED_AUTHOR_PERIOD','period':matched[0],'facts':matched[0].get('facts',{}),'basis':'AUTHOR_CONFIRMED_STORY_PERIOD_NOT_CURRENT_STATE_REPLAY'}
    return {'status':'UNKNOWN','facts':{},'reason':'没有该故事时间的确认记录，不使用当前状态倒推过去'}

def writer_summary(entity,at,selected_ids,pov):
    text=entity.get('writer_view','').strip();basis='AUTHOR_RELEASED_STATIC_WORLD_NOT_RUNTIME_KNOWLEDGE'
    if is_rule(entity):
        r=card(entity)
        if r['rule_scope']=='SCENARIO':raise ConsoleError('实验分支规则不能进入正式 Writer Context',409)
        if r['rule_scope']=='ENTITY' and not set(r['scope_ids'])&{pov,*selected_ids}:raise ConsoleError('规则适用对象未包含在本次写作范围，请先选择相应实体',409)
        if r['rule_scope']=='PERIOD' and not (entity.get('valid_from') or entity.get('valid_to')):raise ConsoleError('历史规则缺少有效时间边界',409)
    if entity.get('periods'):
        projected=historical(entity,at,card(entity)['calendar'] if is_rule(entity) else 'iso')
        if projected['status']!='VERIFIED_AUTHOR_PERIOD':raise ConsoleError('该故事时间的世界资料未知或冲突，不能使用最新设定替代',409)
        text=projected['period'].get('writer_view','').strip();basis=projected['basis']
        if not text:raise ConsoleError('该历史时期尚未发布 Writer 安全摘要',409)
    if entity.get('valid_from') or entity.get('valid_to'):
        calendar=card(entity)['calendar'] if is_rule(entity) else 'iso'
        if interval(entity.get('valid_from',''),entity.get('valid_to',''),at,calendar)!='MATCH':raise ConsoleError('世界设定不适用于当前故事时间，或日期精度/时区不足',409)
    return text,basis

def fragment(text):
    """Validate via the existing experiment schema, including its safe grammar."""
    if not text.strip():return None
    try:
        value=json.loads(text)
        if not isinstance(value,dict) or set(value)-{'solver','inputs','constraints','outputs','acceptance_rules','assumptions','limitations'}:raise ValueError('数学映射字段无效')
        from app.world_logic.models import validate
        base={'schema_version':'1.0','experiment_id':'exp_'+'0'*32,'name':'规则形式化映射','experiment_type':'world_rules',**value}
        return validate(base)
    except Exception as e:raise ConsoleError('规则数学映射无效：'+str(e)[:200],422) from None
