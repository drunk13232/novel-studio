"""Story clocks only; narrative order and associations are never chronology proof."""
from datetime import datetime
from .expressions import evaluate, Missing, Unsafe

def interval(event):
    if event.get('clock','gregorian')!='gregorian':
        value=event.get('coordinate')
        return None if value is None else (float(value),float(value),event['clock'])
    def instant(text):
        try:
            if not text or 'T' not in text and ' ' not in text:return None
            d=datetime.fromisoformat(text.replace('Z','+00:00'))
            return None if d.tzinfo is None else d.timestamp()
        except (ValueError,OverflowError):return None
    if event.get('time'):
        t=instant(event['time']);return None if t is None else (t,t,'gregorian')
    a,b=instant(event.get('earliest','')),instant(event.get('latest',''))
    return None if a is None or b is None or a>b else (a,b,'gregorian')

def active_edges(definition,env):
    active=[];unknown=[]
    for edge in definition['dependencies']:
        condition=edge.get('condition','')
        if condition:
            try:
                result=evaluate(condition,env)
                if not isinstance(result,bool):raise Unsafe('依赖适用条件必须是布尔关系')
                if not result:continue
            except (Missing,Unsafe) as e:unknown.append({'id':edge['id'],'detail':str(e)});continue
        active.append(edge)
    return active,unknown

def check_times(definition,edges):
    events={v['id']:v for v in definition.get('events',[])};rows=[]
    if not events and not any(e.get('kind')=='availability' for e in edges):return rows
    for edge in edges:
        if edge.get('kind','strict_order') not in {'strict_order','availability'}:continue
        before,after=events.get(edge['before']),events.get(edge['after'])
        a,b=interval(before) if before else None,interval(after) if after else None
        detail='';status='INCONCLUSIVE'
        if not a or not b:detail='缺少可比较故事时刻；日期不完整、时区缺失或架空坐标未知。没有补造精确时刻。'
        elif a[2]!=b[2]:detail='不同纪年坐标没有作者确认的转换规则，无法比较。'
        else:
            equal_allowed=edge.get('kind')=='availability'
            if a[1]<=b[0] if equal_allowed else a[1]<b[0]:status='PASS';detail='声明的时间区间满足先后条件。'
            elif a[0]>b[1] if equal_allowed else a[0]>=b[1]:status='FAIL';detail='声明的故事时刻违反先后或获得后使用的条件。'
            else:detail='时间区间重叠，无法证明严格先后。'
        rows.append({'id':'time_'+edge['id'],'name':edge.get('meaning') or edge['id'],'status':status,'detail':detail,'dependency_id':edge['id'],'source_ids':edge.get('source_ids',[]),'before_event':edge['before'],'after_event':edge['after'],'narrative_order_ignored':True})
    return rows
