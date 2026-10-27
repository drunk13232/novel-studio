import {useEffect,useSyncExternalStore} from 'react';
import {api} from './api';
import {WRITING_METRICS_CHANGED,WRITING_PROGRESS_LOADED,goalCrossedToday,goalNoticeKey,type WritingProgress,type WritingMetricsChange} from './writing-metrics-events';
export {invalidateWritingMetrics} from './writing-metrics-events';
export type {WritingProgress} from './writing-metrics-events';
type Snapshot={data:WritingProgress|null;error:string;loading:boolean};
type Entry={snapshot:Snapshot;listeners:Set<()=>void>;pending:Promise<void>|null;again:boolean;kind:WritingMetricsChange['kind']|null};
const entries=new Map<string,Entry>(),noticed=new Set<string>();
function entry(project:string):Entry {
 let value=entries.get(project);
 if(!value){value={snapshot:{data:null,error:'',loading:false},listeners:new Set(),pending:null,again:false,kind:null};entries.set(project,value);}
 return value;
}
function publish(e:Entry,snapshot:Snapshot){e.snapshot=snapshot;for(const listener of e.listeners)listener();}
function announceGoal(before:WritingProgress|null,after:WritingProgress,kind:WritingMetricsChange['kind']|null){
 if(!kind||!goalCrossedToday(before,after,kind))return;
 const key=goalNoticeKey(after);
 if(noticed.has(key))return;
 try{if(localStorage.getItem(key))return;localStorage.setItem(key,'1');}catch{}
 noticed.add(key);
 window.dispatchEvent(new CustomEvent('novel-writing-goal-reached',{detail:{project:after.project_id,date:after.date,goal:after.daily_goal}}));
}
/** One in-flight local read per project; save notifications arriving during it request one trailing read. */
export function refreshWritingProgress(project:string,kind:WritingMetricsChange['kind']|null=null):Promise<void>{
 const e=entry(project);
 if(e.pending){e.again=true;if(kind&&(e.kind!=='save'&&e.kind!=='restore'))e.kind=kind;return e.pending;}
 e.kind=kind;
 const baseline=e.snapshot.data;
 e.pending=(async()=>{
  do{
   e.again=false;
   publish(e,{...e.snapshot,loading:true,error:''});
   try{
    const data=await api<WritingProgress>('/api/projects/'+project+'/experience/writing-progress');
    publish(e,{data,error:'',loading:false});
    window.dispatchEvent(new CustomEvent(WRITING_PROGRESS_LOADED,{detail:{project,data}}));
   }catch(error){publish(e,{...e.snapshot,error:String(error),loading:false});}
  }while(e.again);
  // Compare with the baseline from BEFORE the coalesced reads. The first
  // response may already include a save that arrived while it was in flight.
  if(!e.snapshot.error&&e.snapshot.data)announceGoal(baseline,e.snapshot.data,e.kind);
 })().finally(()=>{e.pending=null;e.kind=null;});
 return e.pending;
}

let users=0;
function invalidate(event:Event){const change=(event as CustomEvent<WritingMetricsChange>).detail;if(!change?.project)return;const e=entries.get(change.project);if(e&&(e.listeners.size||e.pending))void refreshWritingProgress(change.project,change.kind);else if(e)e.snapshot={data:null,error:'',loading:false};}
function dayAtZone(){return new Date(Date.now()+8*3600000).toISOString().slice(0,10);}
function refreshDate(){if(document.visibilityState==='hidden')return;for(const [project,e] of entries)if(e.listeners.size&&e.snapshot.data?.date!==dayAtZone())void refreshWritingProgress(project);}
function bind(){if(++users!==1)return;window.addEventListener(WRITING_METRICS_CHANGED,invalidate);window.addEventListener('focus',refreshDate);document.addEventListener('visibilitychange',refreshDate);}
function unbind(){if(--users!==0)return;window.removeEventListener(WRITING_METRICS_CHANGED,invalidate);window.removeEventListener('focus',refreshDate);document.removeEventListener('visibilitychange',refreshDate);}
export function useWritingProgress(project:string){
 const e=entry(project);
 const snapshot=useSyncExternalStore(listener=>{e.listeners.add(listener);return()=>{e.listeners.delete(listener);};},()=>e.snapshot);
 useEffect(()=>{bind();void refreshWritingProgress(project);return unbind;},[project,e]);
 return {...snapshot,retry:()=>refreshWritingProgress(project)};
}
