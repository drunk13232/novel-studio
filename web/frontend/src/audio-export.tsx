import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {base,ErrorNote,Empty} from './library-shared';
import {StudioDialog} from './studio-dialog';
import {t,useUiTranslation,formatBytes} from './i18n';
import './creative-tools.css';
type D=Record<string,any>;
const tr=(key:string,values?:Record<string,unknown>)=>t('creativeTools:audio.'+key,values);
const errorMessage=(e:unknown)=>t('creativeTools:errors.'+((e as {code?:string})?.code||'unknown'),{defaultValue:String(e)});
const active=(row:D|null)=>!!row&&['QUEUED','RUNNING','CANCELLING'].includes(row.status);
export function AudioExport({project}:{project:string}){
 useUiTranslation('creativeTools');
 const url=base(project)+'/audio-export';
 const [catalog,setCatalog]=useState<D|null>(null),[info,setInfo]=useState<D|null>(null),[voice,setVoice]=useState(''),[rate,setRate]=useState(0),[directory,setDirectory]=useState(''),[drafts,setDrafts]=useState(false),[selected,setSelected]=useState<string[]>([]),[all,setAll]=useState(true),[preview,setPreview]=useState<D|null>(null),[job,setJob]=useState<D|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[search,setSearch]=useState(''),[pollFailed,setPollFailed]=useState(false),[refreshStamp,setRefreshStamp]=useState(0);
 const generation=useRef(0),pending=useRef(false),currentJob=useRef<D|null>(null);currentJob.current=job;
 async function initialize(current:()=>boolean){
  const [a,b]=await Promise.all([api<D>(url),api<D>(base(project)+'/book')]);
  if(!current())return;
  setInfo(a);setCatalog(b);setVoice(a.capabilities.voices?.[0]?.id||'');setDirectory(b.capabilities.default_directory||'');
  setJob(a.jobs.find((j:D)=>active(j))||null);
 }
 useEffect(()=>{
  const stamp=++generation.current;pending.current=false;setBusy(false);setError('');setCatalog(null);setInfo(null);setJob(null);setPreview(null);setSearch('');setSelected([]);setAll(true);setDrafts(false);setPollFailed(false);
  void initialize(()=>stamp===generation.current).catch(e=>{if(stamp===generation.current)setError(errorMessage(e))});
  return()=>{generation.current++};
 },[url,project]);
 async function load(){const ticket=generation.current;const v=await api<D>(url);if(ticket===generation.current)setInfo(v)}
 useEffect(()=>{
  if(!active(job))return;
  let live=true;const ticket=generation.current;
  const timer=setTimeout(()=>{
   void api<D>(url+'/'+job!.id).then(v=>{
    if(!live||ticket!==generation.current)return;
    setJob(v);setPollFailed(false);
    if(!active(v))void load().catch(e=>{if(live&&ticket===generation.current)setError(errorMessage(e))});
   }).catch(()=>{if(live&&ticket===generation.current)setPollFailed(true)});
  },900);
  return()=>{live=false;clearTimeout(timer)};
 },[job,url,refreshStamp]);
 async function run(fn:(current:()=>boolean)=>Promise<void>){
  if(pending.current)return;pending.current=true;const ticket=generation.current,current=()=>ticket===generation.current;
  setBusy(true);setError('');
  try{await fn(current)}catch(e){if(current())setError(errorMessage(e))}
  finally{if(current()){pending.current=false;setBusy(false)}}
 }
 function change(){setPreview(null)}
 if(!info||!catalog)return <div className="creative-tool-page"><p role="status">{error||tr('loading')}</p>{error&&<button disabled={busy} onClick={()=>void run(initialize)}>{tr('refresh')}</button>}</div>;
 const running=active(job),otherRunning=info.jobs.find((row:D)=>row.id!==job?.id&&active(row)),locked=running||!!otherRunning;
 const visible=catalog.chapters.filter((c:D)=>(c.title+' '+(c.volume_title||'')).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
 const mutateJob=(suffix:string)=>run(async current=>{
  const identifier=job!.id;const v=await api<D>(url+'/'+identifier+'/'+suffix,{},'POST');
  if(!current())return;
  if(currentJob.current?.id===identifier){setJob(v);setPollFailed(false)}
  await load();
 });
 return <div className="creative-tool-page">
  <h1>{tr('title')}</h1><p>{tr('local')}</p><ErrorNote text={error}/>
  {(info.warnings?.length>0||info.history_limited)&&<p role="status" className="studio-notice">{tr('historyWarning',{count:info.warnings?.length||0})}</p>}
  <button disabled={busy} onClick={()=>void run(async()=>{await load()})}>{tr('refreshHistory')}</button>
  {otherRunning&&<button onClick={()=>{setJob(otherRunning);setPollFailed(false)}}>{tr('returnRunning')}</button>}
  {!info.capabilities.available&&<div className="studio-notice"><h2>{tr('unavailable')}</h2><p>{tr('installVoice')}</p><button disabled={busy} onClick={()=>void run(async()=>{await load()})}>{tr('refresh')}</button></div>}
  <section className="night-panel">
   <div className="creative-tool-actions">
    <label>{tr('voice')}<select value={voice} disabled={locked||busy} onChange={e=>{setVoice(e.target.value);change()}}><option value="">{tr('chooseVoice')}</option>{info.capabilities.voices.map((v:D)=><option key={v.id} value={v.id}>{v.name||v.description||v.id}</option>)}</select></label>
    <label>{tr('rate')}<input type="range" min={-10} max={10} value={rate} disabled={locked||busy} onChange={e=>{setRate(+e.target.value);change()}}/><span>{rate}</span></label>
    <label>{tr('folder')}<input value={directory} disabled={locked||busy} onChange={e=>{setDirectory(e.target.value);change()}}/></label>
    {window.pywebview&&<button disabled={locked||busy} onClick={()=>void run(async current=>{const v=await window.pywebview?.api.choose_export_directory();if(current()&&v?.path){setDirectory(v.path);change()}})}>{tr('chooseFolder')}</button>}
   </div>
   <label className="check"><input type="checkbox" checked={all} disabled={locked||busy} onChange={e=>{setAll(e.target.checked);change()}}/>{tr('all')}</label>
   <label className="check"><input type="checkbox" checked={drafts} disabled={locked||busy} onChange={e=>{setDrafts(e.target.checked);change()}}/>{tr('drafts')}</label>
   {!all&&<><div className="creative-tool-actions"><input aria-label={tr('search')} placeholder={tr('search')} value={search} onChange={e=>setSearch(e.target.value)}/><button disabled={locked||busy} onClick={()=>{setSelected(s=>Array.from(new Set([...s,...visible.map((c:D)=>c.id)])));change()}}>{tr('selectVisible')}</button><button disabled={locked||busy} onClick={()=>{setSelected([]);change()}}>{tr('clearSelection')}</button><span>{tr('selected',{count:selected.length})}</span></div><div className="audio-chapter-list">{visible.map((c:D)=><label className="check" key={c.id}><input type="checkbox" disabled={locked||busy} checked={selected.includes(c.id)} onChange={e=>{setSelected(s=>e.target.checked?[...s,c.id]:s.filter(id=>id!==c.id));change()}}/>{c.title} · {c.status}</label>)}</div></>}
   {!catalog.chapters.length&&<Empty text={tr('emptyScope')}/>}
   <button disabled={busy||locked||!voice||!directory||!info.capabilities.available||!catalog.chapters.length||!all&&!selected.length} onClick={()=>void run(async current=>{
    const submitted={chapters:all?[]:selected,drafts,voice,rate,directory,confirm:false};const value=await api<D>(url+'/preview',submitted,'POST');
    if(current())setPreview({...value,request:submitted});
   })}>{tr('preview')}</button>
  </section>
  {preview&&<StudioDialog title={tr('confirmTitle')} onClose={()=>setPreview(null)}>
   <p>{tr('confirmRange',{count:preview.chapters.length})}</p>
   {preview.estimate_basis==='PRIOR_LOCAL_AUDIO_SAME_VOICE_RATE'?<p>{tr('sampleEstimate',{minutes:Math.ceil(preview.estimated_seconds/60),size:formatBytes(preview.estimated_bytes),count:preview.estimate_sample_characters})}</p>:<p>{tr('estimates')}</p>}
   <p>{tr('format')} · {preview.directory}</p><p>{info.capabilities.voices.find((v:D)=>v.id===preview.request.voice)?.name} · {tr('rate')}: {preview.request.rate}</p>
   <ul className="audio-chapter-list">{preview.chapters.map((c:D)=><li key={c.id}>{c.title} · {c.characters.toLocaleString()} {tr('characters')}</li>)}</ul>
   {preview.warnings.map((w:string)=><p key={w} className="studio-notice">{w}</p>)}
   <button disabled={busy} onClick={()=>void run(async current=>{const v=await api<D>(url,{...preview.request,preview_id:preview.preview_id,confirm:true},'POST');if(!current())return;setJob(v);setPreview(null);setPollFailed(false);await load()})}>{tr('start')}</button>
  </StudioDialog>}
  {job&&<section className="night-panel" aria-live="polite">
   <h2>{tr('progress')}</h2><p>{tr('status.'+job.status)} · {Object.keys(job.completed).length} / {job.chapters.length}</p><progress value={Object.keys(job.completed).length} max={Math.max(1,job.chapters.length)}/>
   {job.error&&<ErrorNote text={job.error_code?t('creativeTools:errors.'+job.error_code,{defaultValue:job.error}):job.error}/>}
   {pollFailed&&<p role="status" className="studio-notice">{tr('pollFailed')} <button onClick={()=>{setPollFailed(false);setRefreshStamp(n=>n+1)}}>{tr('retryProgress')}</button></p>}
   <p>{job.request.directory} · {tr('rate')}: {job.request.rate}</p><p>{job.chapters.find((c:D)=>c.id===job.current)?.title}</p>
   {running&&<button disabled={busy||job.status==='CANCELLING'} onClick={()=>void mutateJob('cancel')}>{tr('cancel')}</button>}
   {['FAILED','CANCELLED','INTERRUPTED'].includes(job.status)&&<button disabled={busy||!!otherRunning} onClick={()=>void mutateJob('resume')}>{tr('resume')}</button>}
   {job.output_directory&&<p>{job.output_directory}</p>}
   {Object.entries(job.completed).map(([identifier,value])=>{const v=value as D;return <p key={identifier}>{job.chapters.find((c:D)=>c.id===identifier)?.title} · {(v.duration_seconds/60).toFixed(1)} {tr('minutes')} · {formatBytes(v.bytes)}{v.filename&&<small> · {v.filename}</small>}</p>})}
  </section>}
  <section className="night-panel"><h2>{tr('history')}</h2>{!info.jobs.length&&<Empty text={tr('empty')}/>}<div className="audio-history">{info.jobs.map((j:D)=><button key={j.id} onClick={()=>{setJob(j);setPollFailed(false)}}>{j.title} · {tr('status.'+j.status)} · {Object.keys(j.completed).length}/{j.chapters.length}</button>)}</div></section>
 </div>;
}
