"""Declarative field metadata over Bible.Category; no executable template language."""
import json,math
from jsonschema import Draft202012Validator
from app.errors import ConsoleError

PRESETS=[
 {'id':'modern','name':'现实 / 现代','focus':['制度与日常生活','资源来源','信息传播'],'modules':['society','economy']},
 {'id':'alternate','name':'架空历史','focus':['历史分歧点','制度延续','技术边界'],'modules':['society','history']},
 {'id':'science','name':'科幻','focus':['技术前提','能源与运输','技术使用代价'],'modules':['economy','technology']},
 {'id':'fantasy','name':'奇幻','focus':['自然规则','能力代价','文化与信仰'],'modules':['society','power']},
 {'id':'cultivation','name':'仙侠 / 玄幻','focus':['修炼限制','传承组织','资源竞争'],'modules':['power','economy']},
 {'id':'apocalypse','name':'末日','focus':['库存与消耗','运输中断','组织秩序'],'modules':['economy','logistics']},
 {'id':'mystery','name':'超自然悬疑','focus':['公开规则与例外','角色可见信息','线索来源'],'modules':['power','history']},
]

def f(id,name,type='longtext',group='基本信息',help='',**kw):
    return dict(id=id,name=name,type=type,group=group,help=help,options=[],**kw)

MODULES={
 'society':{'name':'制度与社会', 'fields':[
  f('government_form','治理结构',group='制度与社会',help='权力如何产生、约束与交接？实际运作与名义制度可不同。'),
  f('social_tensions','社会张力',group='制度与社会',help='列出利益差异、日常代价和规则例外，避免用一种立场代替所有居民。'),
  f('everyday_life','日常生活',group='制度与社会',help='普通人的居住、教育、医疗与交流方式。')]},
 'economy':{'name':'经济与财政','fields':[
  f('population_total','人口数量','quantity','经济与财政','未知可留空；数字需要年份、口径与依据。',unit='person',minimum=0),
  f('revenue_sources','财政与收入来源',group='经济与财政',help='税收、贸易、外援等分别说明；没有模型时不编造精确预算。'),
  f('production_limits','产业与生产限制',group='经济与财政',help='设备、原料、劳动、能源和技术能力。'),
  f('external_dependency','对外依赖',group='经济与财政',help='供应中断会影响什么？关联不自动等于确定因果。')]},
 'logistics':{'name':'军事与后勤','fields':[
  f('military_supply','军事装备与补给',group='军事与后勤',help='装备来源、人员来源、维护、补给运输与消耗。'),
  f('stock_and_flow','库存与流量',group='军事与后勤',help='明确时间单位；无法量化的部分标为待定。'),
  f('transport_limits','运输限制',group='军事与后勤',help='距离、路线、运力、旅行时间、季节和特殊能力。')]},
 'history':{'name':'历史与纪年','fields':[
  f('calendar_system','纪年体系','calendar','历史与纪年','可使用自定义纪年；不强制转换为公历。'),
  f('history_causes','历史转折与前提',group='历史与纪年',help='标明已经确认的历史、传闻和未来计划。'),
  f('unresolved_history','未知或争议历史',group='历史与纪年',help='保留不同说法，不将记载自动认定为事实。',author_only=True)]},
 'technology':{'name':'技术与自然规则','fields':[
  f('technical_basis','技术前提',group='技术与自然规则',help='明确允许的自然常数、技术水平与必要资源。'),
  f('energy_cost','能源与代价',group='技术与自然规则'),
  f('technical_exception','例外与失效条件','rule','技术与自然规则','这是作者规则，不会执行任何脚本。')]},
 'power':{'name':'能力与例外','fields':[
  f('power_rule','能力规则','rule','能力与例外','触发条件、效果、代价、上限以及证据。'),
  f('power_exception','例外条件',group='能力与例外',help='超出现实物理的规则可以成立，但需作者明确确认。'),
  f('power_observability','可观察与秘密',group='能力与例外',help='区分作者真相与角色可知信息。',author_only=True)]},
}

def enrich(rows):
    for c in rows:
        modules={'country':['society','economy','logistics','history'],'city':['society','economy','logistics'],'company':['society','economy'],'faction':['society','economy','logistics'],'overview':['history','technology'],'nature':['technology','power'],'history':['history'],'resource':['economy','logistics']}.get(c['id'],[])
        c['modules']=modules
        for module in modules:c['fields'] += json.loads(json.dumps(MODULES[module]['fields']))
        c['description']={'country':'从制度、经济、军事、社会与历史建立可追溯的国家设定。','city':'记录空间、管辖、居民、日常生活、生产和交通。','company':'梳理权力结构、业务、资源、运作和利益冲突。'}.get(c['id'],'')
    return rows

def check_template(c):
    size=0
    def visit(fields,depth=0):
        nonlocal size
        size+=len(fields)
        if depth>3 or size>150:raise ConsoleError('模板最多三级嵌套、150 个字段',422)
        ids={v['id'] for v in fields}
        if len(ids)!=len(fields):raise ConsoleError('同一组内字段 ID 不能重复',422)
        for v in fields:
            if len(json.dumps(v,ensure_ascii=False))>30000:raise ConsoleError('字段定义过大',413)
            if v.get('minimum') is not None and v.get('maximum') is not None and v['minimum']>v['maximum']:raise ConsoleError('字段最小值不能大于最大值',422)
            if set(v.get('visible_when',{}))-ids:raise ConsoleError('显示条件必须引用同组已有字段',422)
            if v['type']!='group' and v.get('children'):raise ConsoleError('只有字段组可以包含子字段',422)
            visit(v.get('children',[]),depth+1)
    visit(c['fields'])
    Draft202012Validator.check_schema(value_schema(c))

def field_schema(f):
    t=f['type'];s={'title':f['name'],'description':f.get('help','')}
    if t=='number':s.update(type='number')
    elif t=='boolean':s.update(type='boolean')
    elif t in {'tags','multiselect','list','entities'}:
        s.update(type='array',maxItems=100,items={'type':'string','maxLength':4000})
        if t=='multiselect':s['items']['enum']=f['options']
    elif t=='quantity':s.update(type='object',properties={'value':{'type':'number'},'unit':{'type':'string','minLength':1,'maxLength':80}},required=['value','unit'],additionalProperties=False)
    elif t=='group':s.update(value_schema({'fields':f.get('children',[])},root=False))
    elif t=='evidence':s.update(type='object',properties={k:{'type':'string','maxLength':4000} for k in ['path','revision','quote']},required=['path','revision','quote'],additionalProperties=False)
    else:
        s.update(type='string',maxLength=20000)
        if t=='select':s['enum']=f['options']
    target=s['properties']['value'] if t=='quantity' else s
    for k in ['minimum','maximum']:
        if f.get(k) is not None:target[k]=f[k]
    return s

def value_schema(c,root=True):
    row={'type':'object','properties':{f['id']:field_schema(f) for f in c['fields']},'additionalProperties':False}
    if root:row['$schema']='https://json-schema.org/draft/2020-12/schema'
    return row

def validate_values(c,values,formal=False):
    try:size=len(json.dumps(values,ensure_ascii=False,allow_nan=False))
    except (ValueError,TypeError):raise ConsoleError('字段包含非有限数值或非法数据',422) from None
    if size>250000:raise ConsoleError('专属字段内容超过上限',413)
    # Empty values explicitly mean unknown, never zero or an invented default.
    clean={k:v for k,v in values.items() if v not in (None,'',[])}
    err=next(Draft202012Validator(value_schema(c)).iter_errors(clean),None)
    if err:raise ConsoleError('模板字段校验失败：'+'.'.join(map(str,err.path))+' · '+err.message[:250],422)
    if formal:
        missing=[f['name'] for f in c['fields'] if f.get('required') and f['id'] not in clean and all(values.get(k)==v for k,v in f.get('visible_when',{}).items())]
        if missing:raise ConsoleError('正式采用前请填写必填字段：'+'、'.join(missing),422)
        for f in c['fields']:
            if f['type']=='group' and values.get(f['id']):validate_values({'fields':f.get('children',[])},values[f['id']],True)

def ai_template(c):
    c=json.loads(json.dumps(c))
    def prune(fields):
        rows=[]
        for f in fields:
            if not f.get('ai_allowed',True) or f.get('locked') or f.get('author_only'):continue
            f['children']=prune(f.get('children',[]));rows.append(f)
        return rows
    c['fields']=prune(c['fields']);return c

def compatible(old,new):
    """Recursive compatibility; no discarded values or narrowed accepted domains."""
    by_id={f['id']:f for f in new['fields']}
    for f in old['fields']:
        n=by_id.get(f['id'])
        if not n or n['type']!=f['type'] or set(f.get('options',[]))-set(n.get('options',[])):return False
        if f['type']=='group' and not compatible({'fields':f.get('children',[])},{'fields':n.get('children',[])}):return False
    return True
