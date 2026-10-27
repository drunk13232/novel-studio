import i18n, {t, useUiTranslation} from './i18n';
import {lazy, Suspense, useEffect, useRef, useState} from 'react';
import type {CSSProperties,KeyboardEvent} from 'react';
import {api} from './api';
import {useUnsavedChanges} from './library-shared';
import {invalidateWritingMetrics} from './writing-metrics-client';
import {useReducedMotion} from 'motion/react';
import './writing-statistics.css';

const WritingChart = lazy(() => import('./writing-chart'));
type Row = Record<string, any>;
type Goals = {daily:string;weekly:string;volume:string;book:string;volume_id:string};
const emptyGoals:Goals = {daily:'',weekly:'',volume:'',book:'',volume_id:''};
const readGoals=(row:Row):Goals=>({daily:String(row.goals?.daily||''),weekly:String(row.goals?.weekly||''),volume:String(row.goals?.volume||''),book:String(row.goals?.book||''),volume_id:row.goals?.volume_id||''});
const sameGoals=(a:Goals,b:Goals)=>a.volume_id===b.volume_id&&(['daily','weekly','volume','book'] as const).every(key=>Number(a[key]||0)===Number(b[key]||0));
const readNotes=(row:Row):Record<string,string>=>{const result:Record<string,string>={};for(const item of [...(row.trend||[]),...(row.calendar?.days||[])])if(item.date)result[item.date]=String(item.note||'');for(const [date,value] of Object.entries(row.notes||{}))result[date]=String(value||'');return result;};
const text = (key:string, values?:Record<string,unknown>) => t('dashboard:writingDashboard.' + key, values);
const number = (value:unknown) => Number(value || 0).toLocaleString(i18n.language);
const signed = (value:unknown) => Number(value || 0) > 0 ? '+' + number(value) : number(value);
const dayDate = (value:string) => new Date(value + 'T00:00:00Z');
const dateLabel = (value:string) => new Intl.DateTimeFormat(i18n.language,{dateStyle:'medium',timeZone:'UTC'}).format(dayDate(value));

function GoalProgress({label,current,target}:{label:string;current:number;target:number}) {
 const percent = target > 0 ? Math.max(0,Math.min(100,current / target * 100)) : 0;
 return <div className="wd-goal"><div><b>{label}</b><span>{target > 0 ? text('goalValue',{current:number(current),target:number(target)}) : text('goalUnset')}</span></div><progress aria-label={label} max={100} value={percent}/><small>{target > 0 ? text('goalPercent',{percent:Math.round(percent)}) : text('goalOptional')}</small></div>;
}

function AnnualHeatmap({calendar,selected,onSelect}:{calendar:Row;selected:string;onSelect:(date:string)=>void}) {
 const rows:Row[] = calendar.days || [];
 const buttons = useRef<(HTMLButtonElement|null)[]>([]);
 const activeIndex = Math.max(0,rows.findIndex(row => row.date === selected));
 const [focusIndex,setFocusIndex] = useState(activeIndex);
 useEffect(() => setFocusIndex(activeIndex),[activeIndex]);
 if (!rows.length) return null;
 const first = (dayDate(rows[0].date).getUTCDay() + 6) % 7;
 const columns = Math.ceil((first + rows.length) / 7);
 const navigate = (event:KeyboardEvent<HTMLButtonElement>,index:number) => {
  const offset:Record<string,number> = {ArrowRight:7,ArrowLeft:-7,ArrowDown:1,ArrowUp:-1};
  let next:number;
  if (event.key === 'Home') next = 0;
  else if (event.key === 'End') next = rows.length - 1;
  else if (event.key in offset) next = Math.max(0,Math.min(rows.length - 1,index + offset[event.key]));
  else return;
  event.preventDefault();setFocusIndex(next);buttons.current[next]?.focus();
 };
 const weekday = (index:number) => new Intl.DateTimeFormat(i18n.language,{weekday:'short',timeZone:'UTC'}).format(new Date(Date.UTC(2026,0,5 + index)));
 return <><div className="wd-calendar-scroll"><div className="wd-calendar" dir="ltr" style={{'--calendar-columns':columns} as CSSProperties}><div className="wd-months" aria-hidden="true">{rows.map((row,index) => {
  if (index && dayDate(row.date).getUTCDate() !== 1) return null;
  return <span key={row.date} style={{gridColumn:Math.floor((first + index) / 7) + 1}}>{new Intl.DateTimeFormat(i18n.language,{month:'short',timeZone:'UTC'}).format(dayDate(row.date))}</span>;
 })}</div><div className="wd-weekdays" aria-hidden="true">{[0,1,2,3,4,5,6].map(index => <span key={index}>{index % 2 === 0 ? weekday(index) : ''}</span>)}</div><div className="wd-cells" role="group" aria-label={text('heatmapKeyboard')}>{rows.map((row,index) => {
  const hint = text('dayTooltip',{date:dateLabel(row.date),net:signed(row.han),note:row.note || text('noDailyNote')});
  const position = first + index;
  return <button type="button" key={row.date} ref={element => {buttons.current[index] = element;}} className={'wd-day wd-level-' + row.level + (row.date === selected ? ' is-selected' : '')} style={{gridColumn:Math.floor(position / 7) + 1,gridRow:position % 7 + 1}} title={hint} aria-label={hint} aria-pressed={row.date === selected} tabIndex={index === focusIndex ? 0 : -1} onFocus={() => setFocusIndex(index)} onKeyDown={event => navigate(event,index)} onClick={() => onSelect(row.date)}>{row.han < 0 ? '−' : ''}</button>;
 })}</div></div></div><div className="wd-heatmap-legend"><span>{text('heatmapLess')}</span>{[0,1,2,3,4].map(level => <i key={level} className={'wd-level-' + level} aria-hidden="true"/>)}<span>{text('heatmapMore')}</span><i className="wd-level--1" aria-hidden="true">−</i><span>{text('negativeDay')}</span></div></>;
}

export function WritingStatistics({project,animate=true,onNavigate}:{project:string;animate?:boolean;onNavigate?:(page:string)=>void}) {
 useUiTranslation(['common','dashboard','navigation']);
 const reduced = useReducedMotion();
 const chartAnimation = animate && !reduced;
 const url = '/api/projects/' + encodeURIComponent(project) + '/experience';
 const [data,setData] = useState<Row|null>(null);
 const [goals,setGoals] = useState<Goals>(emptyGoals);
 const noteEditor=useRef<HTMLTextAreaElement|null>(null),goalSettings=useRef<HTMLDetailsElement|null>(null);
 const [savedGoals,setSavedGoals]=useState<Goals>(emptyGoals);
 const [savedNotes,setSavedNotes]=useState<Record<string,string>>({});
 const goalBaseline=useRef<Goals>(emptyGoals);
 const noteBaseline=useRef<Record<string,string>>({});
 const [days,setDays] = useState(7);
 const [error,setError] = useState('');
 const [day,setDay] = useState('');
 const [note,setNote] = useState('');
 const [noteDrafts,setNoteDrafts] = useState<Record<string,string>>({});
 const [notice,setNotice] = useState('');
 const [savingGoals,setSavingGoals] = useState(false);
 const [savingNote,setSavingNote] = useState(false);
 const generation = useRef(0);
 const requestVersion = useRef(0);
 const activeProject = useRef(project);activeProject.current = project;
 const inputs=useRef({goals,day,note,noteDrafts});inputs.current={goals,day,note,noteDrafts};
 const goalsDirty=!sameGoals(goals,savedGoals);
 const pendingNoteDays=Object.keys(noteDrafts).filter(date=>noteDrafts[date] !== (savedNotes[date]||'')).sort();
 const noteDirty=!!day&&pendingNoteDays.includes(day);
 useUnsavedChanges(goalsDirty||savingGoals,text('unsavedGoalsLabel'));
 useUnsavedChanges(pendingNoteDays.length>0||savingNote,text('unsavedNotesLabel'));

 useEffect(() => {
  const ticket = ++generation.current;
  let disposed = false;
  let hydrated = false;
  setData(null);setGoals(emptyGoals);setSavedGoals(emptyGoals);setSavedNotes({});goalBaseline.current=emptyGoals;noteBaseline.current={};setError('');setNotice('');setDay('');setNote('');setNoteDrafts({});setSavingGoals(false);setSavingNote(false);
  const load = async () => {
   const request = ++requestVersion.current;
   try {
    const result = await api<Row>(url + '/statistics');
    if (disposed || ticket !== generation.current || request !== requestVersion.current) return;
    setData(result);setError('');
    const incomingGoals=readGoals(result),previousGoals=goalBaseline.current,incomingNotes=readNotes(result);
    goalBaseline.current=incomingGoals;noteBaseline.current=incomingNotes;
    setSavedGoals(incomingGoals);setSavedNotes(incomingNotes);
    setGoals(current=>sameGoals(current,previousGoals)?incomingGoals:current);
    setNoteDrafts(current=>Object.fromEntries(Object.entries(current).filter(([date,value])=>value!==(incomingNotes[date]||''))));
    if(hydrated&&!Object.hasOwn(inputs.current.noteDrafts,inputs.current.day))setNote(incomingNotes[inputs.current.day]||'');
    if (!hydrated) {
     hydrated = true;
     setGoals(incomingGoals);
     const today = result.calendar?.end || result.trend?.at(-1)?.date || '';
     setDay(today);setNote(incomingNotes[today]||'');
    }
   } catch (reason) {if (!disposed && ticket === generation.current && request === requestVersion.current) setError(String(reason));}
  };
  void load();
  const refresh = (event:Event) => {
   if ((event as CustomEvent).detail?.project === project) void load();
  };
  window.addEventListener('novel-writing-metrics-changed',refresh);
  return () => {disposed = true;window.removeEventListener('novel-writing-metrics-changed',refresh);};
 },[project,url]);

 if (!data) return <div className="writing-statistics"><p role={error ? 'alert' : 'status'}>{error || text('loading')}</p>{error && <button onClick={() => invalidateWritingMetrics(project)}>{text('retry')}</button>}</div>;
 const light = ['short','undecided'].includes(data.form);
 const novella = data.form === 'novella';
 const recorded = Number(data.quality?.recorded_saves || 0);
 const selectedDay = data.calendar?.days?.find((row:Row) => row.date === day) || data.trend?.find((row:Row) => row.date === day);
 const graph = (rows:Row[],type:'line'|'bar',label:string) => rows.length ? <Suspense fallback={<p role="status" className="chart-loading">{t('dashboard:loadingChart')}</p>}><WritingChart rows={rows} type={type} animate={chartAnimation} valueName={label}/></Suspense> : <p className="chart-loading muted">{t('dashboard:writingProgressEmptyHelp')}</p>;
 const selectDay = (value:string) => {if(!value)return;setDay(value);setNote(Object.hasOwn(noteDrafts,value)?noteDrafts[value]:savedNotes[value]||'');};
 const editNote=(value:string)=>{const drafts={...inputs.current.noteDrafts};if(value===(noteBaseline.current[day]||''))delete drafts[day];else drafts[day]=value;inputs.current={...inputs.current,note:value,noteDrafts:drafts};setNote(value);setNoteDrafts(drafts);};
 const openJournal=(value?:string)=>{if(value)selectDay(value);requestAnimationFrame(()=>{const node=noteEditor.current;if(!node)return;node.scrollIntoView?.({block:'center',behavior:chartAnimation?'smooth':'auto'});node.focus({preventScroll:true});});};
 const openBookGoal=()=>{if(!goalSettings.current)return;goalSettings.current.open=true;requestAnimationFrame(()=>{const node=goalSettings.current?.querySelector<HTMLInputElement>('[data-goal=book]');node?.scrollIntoView?.({block:'center',behavior:chartAnimation?'smooth':'auto'});node?.focus({preventScroll:true});});};
 const saveShortcut=(event:KeyboardEvent<HTMLFormElement>)=>{if(event.defaultPrevented||event.nativeEvent.isComposing||event.nativeEvent.keyCode===229||event.altKey||event.shiftKey||!(event.ctrlKey||event.metaKey)||!['s','enter'].includes(event.key.toLowerCase()))return;event.preventDefault();event.stopPropagation();event.currentTarget.requestSubmit();};
 const resetGoals=()=>{setGoals({...savedGoals});setNotice('');};
 const resetNote=()=>{const value=savedNotes[day]||'';setNote(value);setNoteDrafts(current=>{const next={...current};delete next[day];return next;});setNotice('');};
 const bestDay = (row:Row|null|undefined) => row ? text('bestDayValue',{date:dateLabel(row.date),count:number(row.han)}) : text('noPositiveDay');
 const goalItems = [
  {key:'daily',label:text('dailyGoal'),current:data.today},
  {key:'weekly',label:text('weeklyGoal'),current:data.week},
  ...(data.form === 'novel' ? [{key:'volume',label:text('volumeGoal'),current:data.volumes.find((volume:Row) => volume.id === data.goals?.volume_id)?.han || 0}] : []),
  {key:'book',label:light ? text('storyGoal') : text('bookGoal'),current:data.total_han},
 ];
 const sources = data.sources || {};
 const sourceKeys = ['manual','ai','restore','unknown'];
 const manualShare = sources.manual_share;
 const aiShare = sources.ai_share;
 const pace = data.pace || {};
 const lastWeek = data.last_week;
 const saveGoals = async () => {
  if(savingGoals||!goalsDirty)return;
  const submitted={...goals};++requestVersion.current;setSavingGoals(true);setError('');setNotice('');
  try {
   const body = {...submitted,daily:Number(goals.daily || 0),weekly:Number(goals.weekly || 0),volume:Number(goals.volume || 0),book:Number(goals.book || 0)};
   await api(url + '/goals',body,'PUT');
   if (activeProject.current !== project) return;
   goalBaseline.current=submitted;setSavedGoals(submitted);setData(current=>current?{...current,goals:body}:current);
   setNotice(sameGoals(inputs.current.goals,submitted)?t('dashboard:writingGoalsSaved'):text('earlierSubmissionSaved'));
  } catch (reason) {if (activeProject.current === project) setError(String(reason));}
  finally {if (activeProject.current === project) setSavingGoals(false);}
 };
 const saveNote = async () => {
  if(savingNote||!day||!noteDirty)return;
  const submittedDay=day,submittedNote=note;++requestVersion.current;setSavingNote(true);setError('');setNotice('');
  try {
   await api(url + '/daily-note',{day:submittedDay,text:submittedNote},'PUT');
   if (activeProject.current !== project) return;
   noteBaseline.current={...noteBaseline.current,[submittedDay]:submittedNote};setSavedNotes(current=>({...current,[submittedDay]:submittedNote}));
   setData(current=>current?{...current,notes:{...(current.notes||{}),[submittedDay]:submittedNote},calendar:current.calendar?{...current.calendar,days:current.calendar.days?.map((row:Row)=>row.date===submittedDay?{...row,note:submittedNote}:row)}:current.calendar,trend:current.trend?.map((row:Row)=>row.date===submittedDay?{...row,note:submittedNote}:row)}:current);
   setNotice(text('noteSavedForDate',{date:dateLabel(submittedDay)})+(inputs.current.noteDrafts[submittedDay]!==undefined&&inputs.current.noteDrafts[submittedDay]!==submittedNote?' '+text('earlierSubmissionSaved'):''));
   setNoteDrafts(current => {if(current[submittedDay]!==submittedNote)return current;const next={...current};delete next[submittedDay];return next;});
  } catch (reason) {if (activeProject.current === project) setError(String(reason));}
  finally {if (activeProject.current === project) setSavingNote(false);}
 };

 return <div className="writing-statistics wd-dashboard"><header className="page-title"><p className="overline">{text('eyebrow')}</p><h1>{text('title')}</h1><p>{text('intro')}</p><small className="muted">{text('privacy')}</small>{onNavigate&&<nav className="creative-tool-actions"><button onClick={()=>onNavigate('annual')}>{t('navigation:annualReport')}</button><button onClick={()=>onNavigate('ritual')}>{t('navigation:writingRitual')}</button></nav>}</header>
  {error && <p role="alert" className="wd-alert">{error}</p>}{notice && <p role="status" className="wd-notice">{notice}</p>}
  {lastWeek && <section className="night-panel wd-week-summary" aria-labelledby="wd-week-title"><div><h2 id="wd-week-title">{text('lastWeekTitle')}</h2><small>{dateLabel(lastWeek.start)} — {dateLabel(lastWeek.end)}</small></div><p><strong>{signed(lastWeek.han)}</strong><span>{text('netCharacters')}</span></p><p><strong>{number(lastWeek.writing_days)}</strong><span>{text('writingDays')}</span></p><p className="wd-week-best"><b>{text('bestSingleDay')}</b><span>{bestDay(lastWeek.best_day)}</span></p></section>}
  {!recorded && <section className="night-panel wd-empty"><h2>{text('emptyTitle')}</h2><p>{text('emptyHelp')}</p><small>{text('baselineHelp')}</small></section>}
  <div className="metric-grid wd-metrics">{[['today',data.today],['week',data.week],['month',data.month],['bodyTotal',data.total_han]].map(([key,value]) => <div className="night-panel" key={String(key)}><small>{text(String(key))}</small><strong>{number(value)}</strong><span>{t('dashboard:chineseCharactersOnly')}</span></div>)}</div>
  <section className="night-panel" aria-labelledby="wd-heatmap-title"><div className="section-heading"><div><h2 id="wd-heatmap-title">{text('heatmapTitle')}</h2><p className="muted">{text('heatmapHelp')}</p></div><small>{data.calendar?.start} — {data.calendar?.end}</small></div><div className="wd-calendar-tools"><label>{text('jumpToDate')}<input type="date" min={data.calendar?.start} max={data.calendar?.end} value={day} onChange={event=>selectDay(event.target.value)}/></label><button type="button" onClick={()=>selectDay(data.calendar?.end||data.trend?.at(-1)?.date||'')}>{text('backToToday')}</button></div><AnnualHeatmap calendar={data.calendar || {}} selected={day} onSelect={selectDay}/><div className="wd-day-detail" aria-live="polite"><b>{day ? dateLabel(day) : text('selectDay')}</b><span>{selectedDay ? text('dayNet',{count:signed(selectedDay.han)}) : text('noDayMetrics')}</span><p>{noteDirty?note:data.notes?.[day]||selectedDay?.note||text('noDailyNote')}</p>{noteDirty&&<small className="wd-preview-unsaved">{text('notePreviewUnsaved')}</small>}<button type="button" className="wd-edit-selected-note" disabled={!day} onClick={()=>openJournal()}>{text('editSelectedNote')}</button>{selectedDay && <small>{text('logBreakdown',{net:signed(selectedDay.han),manual:signed(selectedDay.manual),ai:signed(selectedDay.ai),restore:signed(selectedDay.restore),unknown:signed(selectedDay.unknown)})}</small>}<small>{selectedDay ? text('daySaves',{count:selectedDay.save_count || selectedDay.events?.length || 0}) : ''}</small></div></section>
  <div className="metric-grid wd-streaks">{[['currentStreak',data.streaks?.current],['longestStreak',data.streaks?.longest],['totalWritingDays',data.streaks?.writing_days]].map(([key,value]) => <div className="night-panel" key={String(key)}><small>{text(String(key))}</small><strong>{text('daysValue',{count:Number(value || 0)})}</strong></div>)}<div className="night-panel"><small>{text('bestSingleDay')}</small><strong>{data.streaks?.best_day ? '+' + number(data.streaks.best_day.han) : '—'}</strong><span>{data.streaks?.best_day ? dateLabel(data.streaks.best_day.date) : text('noPositiveDay')}</span></div></div><p className="muted wd-streak-help">{text('streakHelp')}</p>
  <div className="chart-grid"><section className="night-panel"><div className="section-heading"><h2>{t('dashboard:writingTrends')}</h2><div className="wd-period-buttons">{[7,30].map(period => <button type="button" key={period} aria-pressed={days === period} className={days === period ? 'selected' : ''} onClick={() => setDays(period)}>{text('recentDays',{count:period})}</button>)}</div></div>{recorded ? graph((data.trend || []).slice(-days),'line',text('netCharacters')) : <p className="wd-chart-empty">{text('noRecordedSaves')}</p>}</section>
   <section className="night-panel"><h2>{text('hourlyTitle')}</h2><p className="muted">{text('hourlyHelp')}</p>{recorded ? graph((data.hourly || []).map((row:Row) => ({...row,label:String(row.hour).padStart(2,'0') + ':00'})),'bar',text('netCharacters')) : <p className="wd-chart-empty">{text('noRecordedSaves')}</p>}</section>
   <section className="night-panel wd-source-panel"><h2>{text('sourceTitle')}</h2><p className="muted">{text('sourceHelp')}</p>{manualShare != null && aiShare != null ? <><div className="wd-source-bar" role="img" aria-label={text('sourceShareLabel',{manual:Math.round(manualShare * 100),ai:Math.round(aiShare * 100)})}>{manualShare > 0 && <span className="wd-source-manual" style={{width:manualShare * 100 + '%'}}/>}{aiShare > 0 && <span className="wd-source-ai" style={{width:aiShare * 100 + '%'}}/>}</div><div className="wd-source-legend"><span><i className="wd-source-manual"/>{text('manual')} {Math.round(manualShare * 100)}%</span><span><i className="wd-source-ai"/>{text('ai')} {Math.round(aiShare * 100)}%</span></div></> : <p>{text('noAttributableAdditions')}</p>}<div className="wd-source-table-wrap"><table className="wd-source-table"><thead><tr><th>{text('source')}</th><th>{text('positiveAdditions')}</th><th>{text('deletions')}</th><th>{text('net')}</th></tr></thead><tbody>{sourceKeys.map(key => <tr key={key}><th scope="row">{text(key)}</th><td>{number(sources[key]?.added_han)}</td><td>{sources[key]?.deleted_han ? '−' + number(Math.abs(sources[key].deleted_han)) : '0'}</td><td>{signed(sources[key]?.net_han)}</td></tr>)}</tbody></table></div><small className="muted">{text('sourceRatioHelp')}</small></section>
   <section className="night-panel wd-pace"><h2>{text('paceTitle')}</h2>{pace.status === 'FORECAST' && pace.estimated_date ? <><strong>{dateLabel(pace.estimated_date)}</strong><p>{text('paceForecastHelp',{average:number(Number(pace.daily_average).toFixed(1)),remaining:number(pace.remaining),days:number(pace.days_remaining)})}</p></> : pace.status === 'COMPLETE' ? <><strong>{text('targetComplete')}</strong><p>{text('targetCompleteHelp')}</p></> : <><strong>{pace.status === 'NO_TARGET' ? text('noBookTarget') : text('noPace')}</strong><p>{pace.status === 'NO_TARGET' ? text('setBookTargetHelp') : pace.status === 'OUT_OF_RANGE' ? text('paceOutOfRange') : text('noPaceHelp')}</p></>}{pace.status==='NO_TARGET'&&<button type="button" className="wd-edit-book-goal" onClick={openBookGoal}>{text('setBookGoalNow')}</button>}<small className="muted">{text('paceMethod')}{pace.window_start && <><br/>{pace.window_start} — {pace.window_end} · {text('windowNet',{count:signed(pace.net_han)})}</>}</small></section>
  </div>
  <section className="night-panel" aria-labelledby="wd-goals-title"><div className="section-heading"><div><h2 id="wd-goals-title">{text('goalsTitle')}</h2><p className="muted">{text('goalsHelp')}</p></div></div><div className="wd-goal-grid">{goalItems.map(item => <GoalProgress key={item.key} label={item.label} current={item.current} target={Number(data.goals?.[item.key] || (item.key === 'book' ? data.writing?.target_characters : 0) || 0)}/>)}</div><details ref={goalSettings} className="wd-goal-settings"><summary>{text('editGoals')}</summary><form aria-keyshortcuts="Control+s Control+Enter Meta+s Meta+Enter" onKeyDown={saveShortcut} onSubmit={event => {event.preventDefault();void saveGoals();}}><div className="night-fields">{goalItems.map(item => <label key={item.key}>{item.label}<input type="number" min={0} max={item.key === 'daily' ? 1000000 : item.key === 'weekly' ? 10000000 : 100000000} step={1} data-goal={item.key} value={goals[item.key as keyof Goals]} placeholder={t('dashboard:leaveGoalUnset')} onChange={event => setGoals(current => ({...current,[item.key]:event.target.value}))}/></label>)}</div>{data.form === 'novel' && <label>{t('dashboard:targetVolume')}<select value={goals.volume_id} onChange={event => setGoals(current => ({...current,volume_id:event.target.value}))}><option value="">{t('dashboard:selectVolume')}</option>{(data.volumes || []).map((volume:Row) => <option key={volume.id} value={volume.id}>{volume.title}</option>)}</select></label>}<button className="primary" type="submit" disabled={savingGoals||!goalsDirty}>{savingGoals ? text('saving') : t('dashboard:saveGoals')}</button><button type="button" disabled={savingGoals||!goalsDirty} onClick={resetGoals}>{text('resetGoals')}</button><p className="wd-form-status" role="status">{text(savingGoals?'saving':goalsDirty?'goalsUnsaved':'goalsUpToDate')}</p><small className="muted">{text('formSaveShortcut')}</small></form></details></section>
  <details className="night-panel wd-manuscript-detail"><summary>{text('manuscriptOverview')}</summary><p>{text('chapterSummary',{completed:number(data.completed),unfinished:number(data.unfinished),characters:number(data.total_characters)})}</p><p>{text('latestSave',{date:data.last_written ? new Date(data.last_written).toLocaleString(i18n.language) : t('dashboard:noNewRecords')})}</p>{!light && <div className="chart-grid"><section><h3>{t('dashboard:chapterCharacterCounts')}</h3>{graph((data.chapters || []).filter((chapter:Row) => chapter.han).map((chapter:Row) => ({...chapter,label:String(chapter.number)})),'bar',text('currentCharacters'))}</section>{!novella && <section><h3>{t('dashboard:progressByVolume')}</h3>{graph((data.volumes || []).map((volume:Row) => ({...volume,label:volume.title})),'bar',text('currentCharacters'))}{(data.volumes || []).map((volume:Row) => <p key={volume.id}>{volume.title} · {text('volumeChapterProgress',{completed:volume.completed,total:volume.planned})}</p>)}</section>}</div>}<progress aria-label={t('dashboard:bookChapterCompletion')} max={(data.completed || 0) + (data.unfinished || 0) || 1} value={data.completed || 0}/></details>
  <section className="night-panel"><h2>{t('dashboard:dailyWritingLog')}</h2><p className="muted">{text('dailyNoteHelp')}</p>{pendingNoteDays.length>0&&<div className="wd-pending-notes"><p role="status">{text('pendingNoteCount',{count:pendingNoteDays.length})}</p><div>{pendingNoteDays.map(date=><button type="button" key={date} aria-pressed={date===day} onClick={()=>selectDay(date)}>{date}</button>)}</div></div>}<form aria-keyshortcuts="Control+s Control+Enter Meta+s Meta+Enter" onKeyDown={saveShortcut} onSubmit={event => {event.preventDefault();void saveNote();}}><div className="night-fields"><label>{t('common:date')}<input type="date" value={day} onChange={event => selectDay(event.target.value)} required/></label><label>{t('dashboard:briefNote')}<textarea ref={noteEditor} maxLength={1000} rows={3} value={note} onChange={event => editNote(event.target.value)} placeholder={t('dashboard:noteTodaysProgress')}/></label></div><button type="submit" disabled={savingNote||!day||!noteDirty}>{savingNote ? text('saving') : t('dashboard:saveNote')}</button><button type="button" disabled={savingNote||!noteDirty} onClick={resetNote}>{text('resetNote')}</button><p className="wd-form-status" role="status">{text(savingNote?'saving':noteDirty?'noteUnsaved':'noteUpToDate')}</p><small className="muted">{text('formSaveShortcut')}</small></form>{(data.trend || []).filter((row:Row) => row.save_count || row.events?.length || row.note).slice().reverse().map((row:Row) => <article className="daily-record" key={row.date}><b>{dateLabel(row.date)}</b><button type="button" className="wd-record-edit" onClick={()=>openJournal(row.date)}>{text('editRecord')}</button><span>{text('logBreakdown',{net:signed(row.han),manual:signed(row.manual),ai:signed(row.ai),restore:signed(row.restore),unknown:signed(row.unknown)})}</span>{row.note && <p>{row.note}</p>}<small>{text('daySaves',{count:row.save_count || row.events?.length || 0})}</small></article>)}</section>
  <footer className="wd-method"><p>{text('method')}</p><p>{text('timezone')}</p>{Number(data.quality?.excluded_estimates || 0) > 0 && <p>{text('excludedEstimates',{count:data.quality.excluded_estimates})}</p>}{Number(data.quality?.excluded_invalid_events || 0) > 0 && <p>{text('excludedInvalid',{count:data.quality.excluded_invalid_events})}</p>}</footer>
 </div>;
}
