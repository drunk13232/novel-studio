"""Observed net manuscript growth. No invented historical sessions or duration."""
import contextlib,contextvars,json,math,re,threading,uuid
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Query
from pydantic import BaseModel,Field,ConfigDict,model_validator
from typing import Literal
from app.library.storage import safe,read,write,digest,now
from app.studio import body_counts
from app.errors import ConsoleError

WRITING_ZONE=timezone(timedelta(hours=8))
SOURCE_KEYS={'MANUAL':'manual','AI_ACCEPT':'ai','AI_ACCEPTED':'ai','RESTORE':'restore'}

def _today():
    # Keep the existing statistics timezone explicit, independent of OS locale.
    return datetime.now(WRITING_ZONE).date()

def _day_row(day,notes):
    return {'date':day,'han':0,'characters':0,'manual':0,'ai':0,'restore':0,'unknown':0,
            'events':[],'save_count':0,'note':str(notes.get(day,'') or '')[:1000]}

def _event_stamp(event):
    stamp=datetime.fromisoformat(str(event['at']).replace('Z','+00:00'))
    # The original writer stored UTC. Handle old naive UTC timestamps consistently.
    if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(WRITING_ZONE)

def _event_summary(state,today):
    """Aggregate saved deltas only. Opening statistics never manufactures events."""
    notes=state.get('notes',{}) if isinstance(state.get('notes'),dict) else {}
    daily={};hourly=[{'hour':h,'han':0,'manual':0,'ai':0,'restore':0,'unknown':0,'save_count':0} for h in range(24)]
    sources={key:{'net_han':0,'added_han':0,'deleted_han':0,'save_count':0} for key in ['manual','ai','restore','unknown']}
    quality={'recorded_saves':0,'excluded_estimates':0,'excluded_invalid_events':0,'excluded_future_events':0,'legacy_methodless_saves':0,'timezone':'UTC+08:00'}
    raw_events=state.get('events',[]) if isinstance(state.get('events'),list) else []
    for event in raw_events:
        if not isinstance(event,dict):quality['excluded_invalid_events']+=1;continue
        method=event.get('method')
        if method=='OBSERVED_EXTERNAL_ESTIMATE':quality['excluded_estimates']+=1;continue
        if method is not None and method!='NET_SAVE_DIFF':quality['excluded_invalid_events']+=1;continue
        try:
            stamp=_event_stamp(event)
            han=event['han'];characters=event.get('characters',0)
            if not isinstance(han,int) or isinstance(han,bool) or not isinstance(characters,int) or isinstance(characters,bool):raise ValueError('Invalid delta')
        except (KeyError,TypeError,ValueError,OverflowError):quality['excluded_invalid_events']+=1;continue
        if stamp.date()>today:quality['excluded_future_events']+=1;continue
        day=stamp.date().isoformat();row=daily.setdefault(day,_day_row(day,notes));source_name=event.get('source');key=SOURCE_KEYS.get(source_name,'unknown') if isinstance(source_name,str) else 'unknown'
        row['han']+=han;row['characters']+=characters;row[key]+=han;row['save_count']+=1;row['events'].append(event)
        hour=hourly[stamp.hour];hour['han']+=han;hour[key]+=han;hour['save_count']+=1
        source=sources[key];source['net_han']+=han;source['added_han']+=max(han,0);source['deleted_han']+=max(-han,0);source['save_count']+=1
        quality['recorded_saves']+=1
        if method is None:quality['legacy_methodless_saves']+=1
    positive=sorted(day for day,row in daily.items() if row['han']>0)
    longest=run=0;previous=None
    for day in positive:
        date=datetime.strptime(day,'%Y-%m-%d').date()
        run=run+1 if previous and (date-previous).days==1 else 1
        longest=max(longest,run);previous=date
    # Today's zero has not yet broken yesterday's run; a negative day does break it.
    day=today
    if daily.get(day.isoformat(),{}).get('han',0)==0:day-=timedelta(days=1)
    current=0;as_of=None
    while daily.get(day.isoformat(),{}).get('han',0)>0:
        if as_of is None:as_of=day.isoformat()
        current+=1;day-=timedelta(days=1)
    best=max((daily[d] for d in positive),key=lambda d:d['han'],default=None)
    streaks={'current':current,'longest':longest,'best_day':{'date':best['date'],'han':best['han']} if best else None,'writing_days':len(positive),'as_of':as_of}
    added=sources['manual']['added_han']+sources['ai']['added_han']
    sources.update({'share_basis':'POSITIVE_MANUAL_AI_NET_SAVE_DIFF','scope':'ALL_RECORDED_SAVE_EVENTS',
                    'manual_share':sources['manual']['added_han']/added if added else None,'ai_share':sources['ai']['added_han']/added if added else None})
    return daily,hourly,sources,streaks,quality

def compact_progress(state,project_id='',today=None):
    """Metadata-only view for the editor and bookshelf, with no manuscript scan."""
    today=today or _today();daily,_,_,streaks,quality=_event_summary(state,today);row=daily.get(today.isoformat(),{})
    goals=state.get('goals',{}) if isinstance(state.get('goals'),dict) else {}
    return {'project_id':project_id,'date':today.isoformat(),'timezone':'UTC+08:00','today':row.get('han',0),
            'daily_goal':goals.get('daily',0),'current_streak':streaks['current'],'manual_today':row.get('manual',0),
            'ai_today':row.get('ai',0),'restore_today':row.get('restore',0),'unknown_today':row.get('unknown',0),
            'has_saved_events':quality['recorded_saves']>0}

def _goal_progress(current,target):
    target=target if isinstance(target,int) and target>0 else 0
    return {'current':current,'target':target,'ratio':min(1,max(0,current/target)) if target else 0,'exceeded':bool(target and current>=target)}

origin=contextvars.ContextVar('writing_origin',default='MANUAL')
observer=None
@contextlib.contextmanager
def writing_origin(source):
    token=origin.set(source)
    try:yield
    finally:origin.reset(token)
def notify_saved(root,path,before,after,source=None):
    if observer:
        try:observer(root,path,before,after,source or origin.get())
        except Exception:
            import logging
            logging.getLogger(__name__).exception('写作统计失败；正文保存已成功，不撤销保存')
class Goals(BaseModel):
    model_config=ConfigDict(extra='forbid')
    daily:int=Field(default=0,ge=0,le=1000000)
    weekly:int=Field(default=0,ge=0,le=10000000)
    volume:int=Field(default=0,ge=0,le=100000000)
    book:int=Field(default=0,ge=0,le=100000000)
    volume_id:str=''
def default_ritual_steps():
    return [{'id':'daily-goal','kind':'goal','phase':'start','title':'','enabled':True},
            {'id':'focus-clock','kind':'focus','phase':'start','title':'','enabled':True},
            {'id':'reflection','kind':'reflection','phase':'end','title':'','enabled':True}]

class RitualStep(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    kind:Literal['goal','focus','checklist','reflection']='checklist'
    phase:Literal['start','end']='start'
    title:str=Field(default='',max_length=120)
    enabled:bool=True
class RitualPreferences(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled:bool=False
    skip_remembered:bool=False
    steps:list[RitualStep]=Field(default_factory=lambda:[RitualStep(**step) for step in default_ritual_steps()],max_length=12)
    @model_validator(mode='after')
    def unique_steps(self):
        if len({step.id if isinstance(step,RitualStep) else step['id'] for step in self.steps})!=len(self.steps):
            raise ValueError('仪式步骤 ID 不能重复')
        return self
class RitualUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    etag:str=Field(pattern=r'^[a-f0-9]{64}$')
    settings:RitualPreferences
class RitualDailyGoal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    daily:int=Field(ge=0,le=1000000)
    expected_daily:int=Field(ge=0,le=1000000)
class RitualReflection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    day:str=Field(pattern=r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
    text:str=Field(min_length=1,max_length=500)
    expected_note:str=Field(default='',max_length=1000)

class FocusCursor(BaseModel):
    model_config=ConfigDict(extra='forbid')
    event_count:int=Field(ge=0)
    fingerprint:str=Field(pattern=r'^[a-f0-9]{64}$')
class FocusSummaryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    cursor:FocusCursor
    end_cursor:FocusCursor|None=None

def _focus_fingerprint(project,events):
    # Project-bound prefix digest detects truncation or historical edits without
    # storing another history, clock or manuscript snapshot.
    return digest((project+':'+json.dumps(events,sort_keys=True,separators=(',',':'),ensure_ascii=False)).encode('utf-8'))

class Metrics:
    def __init__(self,books):self.books=books;self.registry=books.registry;self.lock=threading.RLock()
    def path(self,p):return safe(self.registry.workspace(p).root,'metadata/studio/writing.json')
    def state(self,p):return read(self.path(p),{'started_at':now(),'snapshots':{},'events':[],'goals':{},'notes':{}})
    def ritual_path(self,p):return safe(self.registry.workspace(p).root,'metadata/studio/writing-ritual.json')
    def ritual(self,p):
        # Separate project metadata is covered by existing backups; opening is read-only.
        with self.lock:
            path=self.ritual_path(p);raw=read(path,None)
            try:settings=RitualPreferences.model_validate(raw or {}).model_dump()
            except Exception:raise ConsoleError('写作仪式设置损坏，请检查项目备份；作品正文不受影响',422) from None
            state=self.state(p);day=_today().isoformat()
            return {'project_id':p,'etag':digest(path.read_bytes()) if path.exists() else digest(b''),
                    'settings':settings,'date':day,'timezone':'UTC+08:00',
                    'goals':state.get('goals',{}),'note':str(state.get('notes',{}).get(day,'') or '')[:1000]}
    def save_ritual(self,p,b):
        with self.lock:
            current=self.ritual(p)
            if b.etag!=current['etag']:raise ConsoleError('写作仪式设置已在其他窗口变化，请刷新后再保存',409)
            write(self.ritual_path(p),b.settings.model_dump());return self.ritual(p)
    def ritual_daily_goal(self,p,b):
        with self.lock:
            state=self.state(p);goals=state.get('goals',{})
            if not isinstance(goals,dict):raise ConsoleError('目标设置损坏，请先检查项目备份',422)
            current=goals.get('daily',0)
            if type(current)!=int or current!=b.expected_daily:raise ConsoleError('日目标已在其他页面变化，请读取最新值后再保存',409,code='RITUAL_GOAL_CHANGED')
            updated={**goals,'daily':b.daily};self._save_goals(p,state,updated)
            return {'saved':True,'goals':updated}
    def ritual_reflection(self,p,b):
        # The same existing journal store, guarded against overwriting newer notes.
        try:datetime.strptime(b.day,'%Y-%m-%d')
        except ValueError:raise ConsoleError('请选择有效的日记日期（YYYY-MM-DD）',422) from None
        with self.lock:
            state=self.state(p);notes=state.get('notes',{})
            if not isinstance(notes,dict):raise ConsoleError('日记记录损坏，请先检查备份',422)
            previous=str(notes.get(b.day,'') or '')[:1000]
            if previous!=b.expected_note:raise ConsoleError('这一天的日记已变化，请刷新后重新确认追加内容',409)
            line=b.text.strip()
            if not line:raise ConsoleError('请先写一句本次记录，或直接跳过',422)
            combined=(previous+'\n'+line) if previous else line
            if len(combined)>1000:raise ConsoleError('追加后日记将超过 1000 字，请到码字看板整理原日记后再保存',422)
            self.note(p,b.day,combined)
            return {'saved':True,'day':b.day,'note':combined}
    def annual(self,p,year):
        today=_today()
        if year<1900 or year>today.year:raise ConsoleError('请选择 1900 年至今年之间的年份',422)
        with self.lock:state=self.state(p)
        all_daily,_,_,_,all_quality=_event_summary(state,today)
        available=sorted({int(day[:4]) for day in all_daily if 1900<=int(day[:4])<=today.year}|{today.year},reverse=True)
        start=datetime(year,1,1).date();end=min(today,datetime(year,12,31).date())
        selected={day:row for day,row in all_daily.items() if day[:4]==str(year)}
        filtered={'events':[event for row in selected.values() for event in row['events']]}
        daily,hourly,sources,streaks,quality=_event_summary(filtered,end)
        sources['scope']='SELECTED_CALENDAR_YEAR'
        def totals(rows):
            return {'net_han':sum(row['han'] for row in rows),'manual_han':sum(row['manual'] for row in rows),
                    'ai_han':sum(row['ai'] for row in rows),'restore_han':sum(row['restore'] for row in rows),
                    'unknown_han':sum(row['unknown'] for row in rows),'save_count':sum(row['save_count'] for row in rows)}
        calendar=[];day=start
        while day<=end:
            row=daily.get(day.isoformat(),_day_row(day.isoformat(),{}))
            calendar.append({key:value for key,value in row.items() if key not in {'events','note'}});day+=timedelta(days=1)
        months=[{'month':month,**totals([row for day,row in daily.items() if int(day[5:7])==month])} for month in range(1,13)]
        # Only this project's current catalog metadata. Never recursively scan anthology members.
        manifest=self.registry.get(p);cfg=manifest.get('writing') or {};form=cfg.get('form','novel')
        catalog={'chapters':[],'volumes':[]}
        if form!='anthology':catalog=self.books.catalog(p,include_auxiliary=False,include_text_counts=False)
        chapter_map={}
        for chapter in catalog.get('chapters',[]):
            if chapter.get('source_project'):continue
            if chapter.get('kind')=='story' or chapter.get('id')=='story':prefix='chapters/story/'
            elif isinstance(chapter.get('number'),int):prefix='chapters/chapter-'+str(chapter['number'])+'/'
            else:continue
            chapter_map[prefix]=chapter
        chapters={};unassigned={'save_count':0,'net_han':0}
        for row in daily.values():
            for event in row['events']:
                raw=event.get('path');parts=raw.split('/') if isinstance(raw,str) else []
                prefix='/'.join(parts[:2])+'/' if len(parts)>=3 else ''
                chapter=chapter_map.get(prefix)
                if not chapter:unassigned['save_count']+=1;unassigned['net_han']+=event['han'];continue
                key=chapter['id'];item=chapters.setdefault(key,{'id':key,'title':str(chapter.get('title','')),'number':chapter.get('number'),
                    'volume_id':chapter.get('volume',''),'save_count':0,'net_han':0,'manual_han':0,'ai_han':0,'restore_han':0,'unknown_han':0})
                source=event.get('source');bucket=SOURCE_KEYS.get(source,'unknown') if isinstance(source,str) else 'unknown'
                item['save_count']+=1;item['net_han']+=event['han'];item[bucket+'_han']+=event['han']
        ranked=sorted(chapters.values(),key=lambda item:(-item['save_count'],-item['net_han'],str(item['id'])))
        volumes=[]
        for volume in catalog.get('volumes',[]):
            rows=[item for item in ranked if item['volume_id']==volume['id']]
            if rows:volumes.append({'id':volume['id'],'title':str(volume.get('title','')),'edited_chapters':len(rows),
                **{key:sum(row[key] for row in rows) for key in ['save_count','net_han','manual_han','ai_han','restore_han','unknown_han']}})
        stamps=sorted(_event_stamp(event) for row in daily.values() for event in row['events'])
        peak=max(hourly,key=lambda row:row['han']) if any(row['han']>0 for row in hourly) else None
        return {'project_id':p,'year':year,'available_years':available,'scope':'CURRENT_PROJECT_ONLY','basis':'NET_SAVE_DIFF',
                'timezone':'UTC+08:00','start':start.isoformat(),'end':end.isoformat(),'is_partial_year':year==today.year,
                'totals':totals(list(daily.values())),'sources':sources,'streaks':streaks,'streak_scope':'WITHIN_SELECTED_YEAR',
                'calendar':calendar,'months':months,'hourly':hourly,'peak_hour':peak['hour'] if peak else None,
                'first_saved_at':stamps[0].isoformat() if stamps else None,'last_saved_at':stamps[-1].isoformat() if stamps else None,
                'edited_chapters':len(ranked),'most_edited':ranked[:5],'volumes':volumes,'unassigned':unassigned,
                'catalog_basis':'CURRENT_CATALOG_NOT_HISTORICAL_COMPLETION','quality':{**quality,'historical_exclusions':all_quality},
                'has_saved_events':bool(quality['recorded_saves'])}
    def progress(self,p):
        with self.lock:return compact_progress(self.state(p),p)
    def focus_boundary(self,p):
        with self.lock:
            state=self.state(p);events=state.get('events',[])
            if not isinstance(events,list):events=[]
            return {'project_id':p,'cursor':{'event_count':len(events),'fingerprint':_focus_fingerprint(p,events)},'started_at':now(),'timezone':'UTC+08:00'}
    def focus_summary(self,p,b):
        with self.lock:
            state=self.state(p);events=state.get('events',[])
            if not isinstance(events,list):events=[]
            count=b.cursor.event_count
            if count>len(events) or _focus_fingerprint(p,events[:count])!=b.cursor.fingerprint:
                raise ConsoleError('保存记录在专注开始后已恢复或变化，本次字数无法可靠计算；正文不受影响',409)
            end=len(events)
            if b.end_cursor:
                end=b.end_cursor.event_count
                if end<count or end>len(events) or _focus_fingerprint(p,events[:end])!=b.end_cursor.fingerprint:
                    raise ConsoleError('专注结束时的保存记录已变化，本次字数无法可靠计算；正文不受影响',409)
            _,_,sources,_,quality=_event_summary({'events':events[count:end]},_today())
            return {'project_id':p,'net_han':sum(sources[key]['net_han'] for key in ('manual','ai','restore','unknown')),
                    **{key+'_han':sources[key]['net_han'] for key in ('manual','ai','restore','unknown')},
                    'save_count':quality['recorded_saves'],'started_event_count':count,'end_event_count':end,'recorded_until':now(),
                    'excluded_estimates':quality['excluded_estimates'],'excluded_invalid_events':quality['excluded_invalid_events']}
    def saved(self,root,path,before,after,source):
        if root.parent.resolve()!=self.registry.root.resolve() or not re.fullmatch(r'chapters/(chapter-\d+|story)/(draft|final|manual-[a-z0-9-]+)\.(txt|md)',path) or before==after:return
        p=root.name;self.registry.get(p)
        with self.lock:
            state=self.state(p);a=body_counts(before,strip_header=not path.startswith('chapters/story/'));b=body_counts(after,strip_header=not path.startswith('chapters/story/'));hash=digest(after.replace('\r\n','\n').encode())
            if source!='VERSION_SWITCH':state['events'].append({'id':uuid.uuid4().hex,'at':now(),'path':path,'han':b['han']-a['han'],'characters':b['characters']-a['characters'],'source':source,'method':'NET_SAVE_DIFF'})
            state['snapshots'][path]={**b,'hash':hash};write(self.path(p),state)
    def summary(self,p):
        catalog=self.books.catalog(p,include_auxiliary=False);ws=self.registry.workspace(p)
        with self.lock:state=self.state(p)
        today=_today();daily,hourly,sources,streaks,quality=_event_summary(state,today)
        notes=state.get('notes',{}) if isinstance(state.get('notes'),dict) else {}
        def range_rows(days):
            return [daily.get((today-timedelta(days=i)).isoformat(),_day_row((today-timedelta(days=i)).isoformat(),notes)) for i in range(days-1,-1,-1)]
        trend=range_rows(30);calendar=[]
        for row in range_rows(365):
            # Keep heatmap responses small; raw events remain in the legacy 30-day trend only.
            item={k:v for k,v in row.items() if k!='events'};han=row['han']
            item['level']=-1 if han<0 else 0 if han==0 else 1 if han<500 else 2 if han<1500 else 3 if han<3000 else 4
            calendar.append(item)
        chapters=catalog['chapters'];week=today-timedelta(days=today.weekday());month=today.replace(day=1)
        weekly=sum(d['han'] for day,d in daily.items() if week.isoformat()<=day<=today.isoformat())
        monthly=sum(d['han'] for day,d in daily.items() if month.isoformat()<=day<=today.isoformat())
        today_han=daily.get(today.isoformat(),{}).get('han',0);total=sum(c['han'] for c in chapters)
        goals=state.get('goals',{}) if isinstance(state.get('goals'),dict) else {}
        writing=catalog.get('writing',{});target=goals.get('book') or writing.get('target_characters') or 0
        pace_start=today-timedelta(days=6);pace_net=sum(d['han'] for day,d in daily.items() if pace_start.isoformat()<=day<=today.isoformat());average=pace_net/7
        remaining=max(0,target-total);pace={'window_days':7,'window_start':pace_start.isoformat(),'window_end':today.isoformat(),
            'net_han':pace_net,'daily_average':average,'target':target,'remaining':remaining,'estimated_date':None,'days_remaining':None,
            'status':'NO_TARGET' if target<=0 else 'NO_PACE' if average<=0 else 'COMPLETE' if remaining==0 else 'FORECAST'}
        if pace['status']=='FORECAST':
            days=math.ceil(remaining/average)
            try:pace.update(estimated_date=(today+timedelta(days=days)).isoformat(),days_remaining=days)
            except OverflowError:pace['status']='OUT_OF_RANGE'
        last_start=week-timedelta(days=7);last_end=week-timedelta(days=1)
        last_rows=[d for day,d in daily.items() if last_start.isoformat()<=day<=last_end.isoformat()]
        last_best=max((d for d in last_rows if d['han']>0),key=lambda d:d['han'],default=None)
        last_week={'start':last_start.isoformat(),'end':last_end.isoformat(),'han':sum(d['han'] for d in last_rows),
            'writing_days':sum(d['han']>0 for d in last_rows),'best_day':{'date':last_best['date'],'han':last_best['han']} if last_best else None,
            'save_count':sum(d['save_count'] for d in last_rows)}
        volume_han=sum(c['han'] for c in chapters if c.get('volume')==goals.get('volume_id')) if goals.get('volume_id') else 0
        modified=[]
        for chapter in chapters:
            path=chapter.get('final') or chapter.get('draft')
            if path:
                file=safe(ws.root,path)
                if file.is_file():modified.append(datetime.fromtimestamp(file.stat().st_mtime,timezone.utc).isoformat())
        valid_events=[e for row in daily.values() for e in row['events']]
        last_written=max((_event_stamp(e) for e in valid_events),default=None)
        return {'writing':writing,'form':writing.get('form','novel'),'total_han':total,'total_characters':sum(c['characters'] for c in chapters),
            'today':today_han,'week':weekly,'month':monthly,'completed':sum(c['status']=='FINAL' for c in chapters),'unfinished':sum(c['status']!='FINAL' for c in chapters),
            'last_written':last_written.isoformat() if last_written else None,'last_modified':max(modified,default=None),'chapters':chapters,
            'volumes':[{'id':v['id'],'title':v['title'],'han':sum(c['han'] for c in chapters if c['volume']==v['id']),
                        'completed':sum(c['status']=='FINAL' for c in chapters if c['volume']==v['id']),'planned':sum(c['volume']==v['id'] for c in chapters)} for v in catalog['volumes']],
            'trend':trend,'goals':goals,'notes':notes,'started_at':state.get('started_at'),'hourly':hourly,'sources':sources,'streaks':streaks,'pace':pace,'last_week':last_week,'quality':quality,
            'calendar':{'start':calendar[0]['date'],'end':today.isoformat(),'timezone':'UTC+08:00','positive_thresholds':[1,500,1500,3000],'days':calendar},
            'goal_progress':{'daily':_goal_progress(today_han,goals.get('daily',0)),'weekly':_goal_progress(weekly,goals.get('weekly',0)),
                             'volume':_goal_progress(volume_han,goals.get('volume',0)),'book':_goal_progress(total,target)},
            'explanation':'码字数据仅统计正文保存前后的净字数差；删文为负，重复保存为零。手动、AI 接受、恢复和未知来源分别展示，不能由复制行为判断原创性。旧版外部观察估算不计入码字数据；启用前历史不补造。时段按保存事件时间及 UTC+08:00 分组，不表示写作时长。复制原文或生成修订候选不计入码字，作者之后保存独立修订稿的实际净差计入；全书当前字数只读现有正文，独立修订稿不重复计入库存。'}
    def _save_goals(self,p,state,values):
        state['goals']=values;write(self.path(p),state);return {'saved':True}
    def goals(self,p,b):
        with self.lock:return self._save_goals(p,self.state(p),b.model_dump())
    def note(self,p,day,text):
        try:
            if not isinstance(day,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',day):raise ValueError('Invalid date')
            datetime.strptime(day,'%Y-%m-%d')
        except (TypeError,ValueError):raise ConsoleError('请选择有效的日记日期（YYYY-MM-DD）',422) from None
        with self.lock:
            state=self.state(p);state['notes'][day]=str(text)[:1000];write(self.path(p),state);return {'saved':True}

class ShelfRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:str=Field(pattern='^(note|bookmark|progress)$')
    path:str=''
    character:str=''
    text:str=Field(default='',max_length=4000)
    revision:str=''
    exact:str=Field(default='',max_length=200)
    start:int=Field(default=0,ge=0)
    ratio:float=Field(default=0,ge=0,le=1)
    etag:str=''
class ReadingShelf:
    def __init__(self,tools):self.tools=tools;self.lock=threading.RLock()
    def path(self,p):return self.tools.local(p,'reading.json')
    def get(self,p):
        self.tools.registry.get(p);path=self.path(p);row=read(path,{'notes':[],'bookmarks':[],'progress':{}});return {**row,'etag':digest(path.read_bytes()) if path.exists() else digest(b'')}
    def save(self,p,b):
        self.tools.writable(p)
        with self.lock:
            row=self.get(p)
            if b.etag!=row['etag']:raise ConsoleError('便笺或阅读记录已变化，请刷新',409)
            if b.path:doc=self.tools.doc(p,b.path)
            if b.kind in {'bookmark','progress'}:
                if not b.path or doc['etag']!=b.revision:raise ConsoleError('正文版本已变化，请重新确认位置',409)
                text=doc['content'].replace('\r\n','\n');from app.studio_tools import utf16_slice
                quote=b.exact
                if quote and utf16_slice(text,b.start,b.start+len(quote.encode('utf-16-le'))//2)!=quote:raise ConsoleError('书签选区已变化',409)
                prefix=utf16_slice(text,0,b.start)[-32:];suffix=utf16_slice(text,b.start+len(quote.encode('utf-16-le'))//2,len(text.encode('utf-16-le'))//2)[:32]
                entry={'id':uuid.uuid4().hex,'path':b.path,'revision':b.revision,'exact':quote,'start':b.start,'end':b.start+len(quote.encode('utf-16-le'))//2,'prefix':prefix,'suffix':suffix,'ratio':b.ratio,'text':b.text,'at':now()}
                if b.kind=='progress':row['progress'][b.path]=entry;row['last_read']=entry
                else:row['bookmarks'].append(entry)
            else:
                if not b.text.strip():raise ConsoleError('请输入便笺',422)
                if b.character and b.character not in {c['canonical']['id'] for c in self.tools.characters.list(p)}:raise ConsoleError('人物关联无法解析',422)
                row['notes'].append({'id':uuid.uuid4().hex,'text':b.text,'path':b.path,'character':b.character,'at':now()})
            row.pop('etag',None);write(self.path(p),row);return self.get(p)
    def remove(self,p,id,etag):
        self.tools.writable(p)
        with self.lock:
            row=self.get(p)
            if row['etag']!=etag:raise ConsoleError('记录已变化，请刷新',409)
            for kind in ['notes','bookmarks']:
                for item in row[kind]:
                    if item['id']==id:item['trashed']=True
            row.pop('etag',None);write(self.path(p),row);return self.get(p)

def experience_routes(metrics,shelf):
    router=APIRouter(prefix='/api/projects/{p}/experience')
    @router.get('/statistics')
    def statistics(p:str):return metrics.summary(p)
    @router.get('/annual')
    def annual(p:str,year:int=Query(ge=1900,le=9998)):return metrics.annual(p,year)
    @router.get('/ritual')
    def ritual(p:str):return metrics.ritual(p)
    @router.put('/ritual')
    def ritual_settings(p:str,b:RitualUpdate):return metrics.save_ritual(p,b)
    @router.put('/ritual/daily-goal')
    def ritual_daily_goal(p:str,b:RitualDailyGoal):return metrics.ritual_daily_goal(p,b)
    @router.put('/ritual/reflection')
    def ritual_reflection(p:str,b:RitualReflection):return metrics.ritual_reflection(p,b)
    @router.get('/writing-progress')
    def writing_progress(p:str):return metrics.progress(p)
    @router.get('/focus-boundary')
    def focus_boundary(p:str):return metrics.focus_boundary(p)
    @router.post('/focus-summary')
    def focus_summary(p:str,b:FocusSummaryRequest):return metrics.focus_summary(p,b)
    @router.put('/goals')
    def goals(p:str,b:Goals):return metrics.goals(p,b)
    @router.put('/daily-note')
    def note(p:str,b:dict):return metrics.note(p,b.get('day',''),b.get('text',''))
    @router.get('/reading')
    def reading(p:str):return shelf.get(p)
    @router.post('/reading')
    def save(p:str,b:ShelfRequest):return shelf.save(p,b)
    @router.post('/reading/{id}/trash')
    def trash(p:str,id:str,b:dict):return shelf.remove(p,id,b.get('etag',''))
    return router
