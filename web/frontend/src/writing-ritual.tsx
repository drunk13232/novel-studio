import {useEffect,useId,useRef,useState} from 'react';
import {api} from './api';
import {t,useUiTranslation} from './i18n';
import {useUnsavedChanges} from './library-shared';
import {OPEN_FOCUS_TOOLS_EVENT} from './focus-runtime';
import {invalidateWritingMetrics} from './writing-metrics-events';
import './writing-ritual.css';

export type RitualStep={id:string;kind:'goal'|'focus'|'checklist'|'reflection';phase:'start'|'end';title:string;enabled:boolean};
export type RitualSettings={enabled:boolean;skip_remembered:boolean;steps:RitualStep[]};
export type WritingRitualData={project_id:string;etag:string;settings:RitualSettings;date:string;timezone:string;goals:Record<string,unknown>;note:string};
const tr=(key:string,values?:Record<string,unknown>)=>t('ritual:'+key,values);
const base=(project:string)=>'/api/projects/'+encodeURIComponent(project)+'/experience';
const equal=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
export const defaultRitualSettings=():RitualSettings=>({enabled:false,skip_remembered:false,steps:[{id:'daily-goal',kind:'goal',phase:'start',title:'',enabled:true},{id:'focus-clock',kind:'focus',phase:'start',title:'',enabled:true},{id:'reflection',kind:'reflection',phase:'end',title:'',enabled:true}]});
export function loadWritingRitual(project:string,signal?:AbortSignal){return api<WritingRitualData>(base(project)+'/ritual',undefined,'GET',{signal});}
export function shouldOfferWritingRitual(data:WritingRitualData,phase:'start'|'end'){return data.settings.enabled&&!data.settings.skip_remembered&&data.settings.steps.some(step=>step.enabled&&step.phase===phase);}
const stepLabel=(step:RitualStep)=>step.title.trim()||tr('kind_'+step.kind);

/** Optional project-local checklist preferences, stored outside the saved-event log. */
export function WritingRitualSettings({project}:{project:string}){
 useUiTranslation('ritual');const titleId=useId();
 const [data,setData]=useState<WritingRitualData|null>(null),[draft,setDraft]=useState<RitualSettings>(defaultRitualSettings),[error,setError]=useState(''),[loading,setLoading]=useState(true),[saving,setSaving]=useState(false),[message,setMessage]=useState('');
 const [newTitle,setNewTitle]=useState(''),[newPhase,setNewPhase]=useState<'start'|'end'>('start');
 const live=useRef({project,draft});live.current={project,draft};const generation=useRef(0),busy=useRef(false);
 const dirty=!!data&&!equal(draft,data.settings);useUnsavedChanges(dirty||saving||!!newTitle.trim(),tr('unsavedSettings'));
 useEffect(()=>{const serial=++generation.current,controller=new AbortController();busy.current=false;setSaving(false);setLoading(true);setData(null);setDraft(defaultRitualSettings());setNewTitle('');setError('');setMessage('');
  void loadWritingRitual(project,controller.signal).then(value=>{if(serial===generation.current&&!controller.signal.aborted){setData(value);setDraft(value.settings);}}).catch(reason=>{if(serial===generation.current&&!controller.signal.aborted)setError(String(reason).replace(/^Error: /,''));}).finally(()=>{if(serial===generation.current&&!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[project]);
 const patch=(values:Partial<RitualSettings>)=>{setMessage('');setDraft(current=>({...current,...values}));};
 function updateStep(id:string,values:Partial<RitualStep>){setMessage('');setDraft(current=>({...current,steps:current.steps.map(step=>step.id===id?{...step,...values}:step)}));}
 function move(index:number,delta:number){setMessage('');setDraft(current=>{const steps=[...current.steps],next=index+delta;if(next<0||next>=steps.length)return current;[steps[index],steps[next]]=[steps[next],steps[index]];return {...current,steps};});}
 async function save(){if(!data||busy.current||!dirty)return;busy.current=true;setSaving(true);setMessage('');setError('');const serial=generation.current,submitted=structuredClone(draft);
  try{const value=await api<WritingRitualData>(base(project)+'/ritual',{etag:data.etag,settings:submitted},'PUT');if(serial!==generation.current||live.current.project!==project)return;setData(value);setDraft(current=>equal(current,submitted)?value.settings:current);setMessage(equal(live.current.draft,submitted)?tr('saved'):tr('earlierSaved'));}
  catch(reason){if(serial===generation.current)setError(String(reason).replace(/^Error: /,''));}finally{if(serial===generation.current){busy.current=false;setSaving(false);}}
 }
 return <section className="writing-ritual-settings" aria-labelledby={titleId}><header><h3 id={titleId}>{tr('settingsTitle')}</h3><p>{tr('settingsHelp')}</p></header>{loading&&<p role="status">{tr('loading')}</p>}{error&&<p role="alert">{error}</p>}
  {data&&<><label className="ritual-toggle"><input type="checkbox" checked={draft.enabled} onChange={event=>patch({enabled:event.target.checked,skip_remembered:event.target.checked?false:draft.skip_remembered})}/>{tr('enabled')}</label><label className="ritual-toggle"><input type="checkbox" checked={draft.skip_remembered} onChange={event=>patch({skip_remembered:event.target.checked})}/>{tr('rememberedSkip')}</label><p className="ritual-muted">{tr('alwaysOptional')}</p>
   <ol className="ritual-step-list">{draft.steps.map((step,index)=><li key={step.id}><div className="ritual-step-fields"><label className="ritual-toggle"><input type="checkbox" checked={step.enabled} onChange={event=>updateStep(step.id,{enabled:event.target.checked})}/>{tr('stepEnabled')}</label><label>{tr('stepTitle')}<input aria-label={tr('stepTitle')+' '+(index+1)} maxLength={120} placeholder={tr('kind_'+step.kind)} value={step.title} onChange={event=>updateStep(step.id,{title:event.target.value})}/></label><label>{tr('phase')}<select value={step.phase} onChange={event=>updateStep(step.id,{phase:event.target.value as 'start'|'end'})}><option value="start">{tr('before')}</option><option value="end">{tr('after')}</option></select></label><small>{tr('kind_'+step.kind)}</small></div><div className="ritual-step-actions"><button type="button" aria-label={tr('moveUp')+' '+stepLabel(step)} disabled={!index} onClick={()=>move(index,-1)}>↑</button><button type="button" aria-label={tr('moveDown')+' '+stepLabel(step)} disabled={index===draft.steps.length-1} onClick={()=>move(index,1)}>↓</button><button type="button" onClick={()=>patch({steps:draft.steps.filter(item=>item.id!==step.id)})}>{tr('remove')}</button></div></li>)}</ol>
   <form className="ritual-add-step" onSubmit={event=>{event.preventDefault();if(!newTitle.trim()||draft.steps.length>=12)return;patch({steps:[...draft.steps,{id:'step-'+crypto.randomUUID().replaceAll('-',''),kind:'checklist',phase:newPhase,title:newTitle.trim(),enabled:true}]});setNewTitle('');}}><label>{tr('newStep')}<input maxLength={120} value={newTitle} onChange={event=>setNewTitle(event.target.value)}/></label><label>{tr('phase')}<select value={newPhase} onChange={event=>setNewPhase(event.target.value as 'start'|'end')}><option value="start">{tr('before')}</option><option value="end">{tr('after')}</option></select></label><button disabled={!newTitle.trim()||draft.steps.length>=12}>{tr('addStep')}</button></form><small className="ritual-muted">{tr('limit')}</small>
   <div className="ritual-actions"><button disabled={saving||!dirty} onClick={()=>void save()}>{saving?tr('saving'):tr('saveSettings')}</button><button disabled={saving||!dirty} onClick={()=>{setDraft(data.settings);setMessage('');}}>{tr('resetChanges')}</button><button disabled={saving} onClick={()=>{setDraft(defaultRitualSettings());setNewTitle('');setMessage('');}}>{tr('restoreDefaults')}</button></div><p role="status">{message||tr(dirty?'unsaved':'savedState')}</p>
  </>}
 </section>;
}

/** A skippable view over existing goals, focus controls and daily journal. It does
 * not count writing time, start AI, save manuscript or manufacture word events. */
export function WritingRitual({project,phase,onDone,onSkip,onClose,onCloseRequestReady}:{project:string;phase:'start'|'end';onDone?:()=>void;onSkip?:()=>void;onClose?:()=>void;onCloseRequestReady?:(handler:(()=>void)|null)=>void}){
 useUiTranslation('ritual');const headingId=useId();
 const [data,setData]=useState<WritingRitualData|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[index,setIndex]=useState(0),[goal,setGoal]=useState(''),[reflection,setReflection]=useState(''),[checked,setChecked]=useState<Record<string,boolean>>({}),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[remember,setRemember]=useState(false);
 const serial=useRef(0),pending=useRef(false),finished=useRef(false),callbacks=useRef({onDone,onSkip,onClose});callbacks.current={onDone,onSkip,onClose};
 const [confirmClose,setConfirmClose]=useState(false);const live=useRef({project,reflection,goal});live.current={project,reflection,goal};
 const goalDirty=!!data&&Number(goal||0)!==Number(data.goals.daily||0);
 useUnsavedChanges(goalDirty,tr('unsavedGoal'));useUnsavedChanges(busy||!!reflection.trim(),tr('unsavedReflection'));
 const closeHandler=useRef<()=>void>(()=>{});closeHandler.current=()=>{if(goalDirty||reflection.trim()){setConfirmClose(true);return;}callbacks.current.onClose?.();};
 useEffect(()=>{onCloseRequestReady?.(()=>closeHandler.current());return()=>onCloseRequestReady?.(null);},[onCloseRequestReady]);
 useEffect(()=>{const id=++serial.current,controller=new AbortController();finished.current=false;pending.current=false;setLoading(true);setData(null);setIndex(0);setGoal('');setReflection('');setChecked({});setMessage('');setError('');setBusy(false);setRemember(false);setConfirmClose(false);
  void loadWritingRitual(project,controller.signal).then(value=>{if(id!==serial.current||controller.signal.aborted||finished.current)return;setData(value);setGoal(String(value.goals.daily||''));if(!shouldOfferWritingRitual(value,phase)){finished.current=true;callbacks.current.onDone?.();}}).catch(reason=>{if(id===serial.current&&!controller.signal.aborted)setError(String(reason).replace(/^Error: /,''));}).finally(()=>{if(id===serial.current&&!controller.signal.aborted)setLoading(false);});
  return()=>{controller.abort();serial.current++;};
 },[project,phase]);
 const steps=data?.settings.steps.filter(step=>step.enabled&&step.phase===phase)||[];const step=steps[index];
 function leave(skip=false,savedGoal?:unknown){if(finished.current)return;finished.current=true;setReflection('');setGoal(String((savedGoal??data?.goals.daily)||''));if(skip)(callbacks.current.onSkip||callbacks.current.onDone)?.();else callbacks.current.onDone?.();}
 async function skip(){if(finished.current)return;if(pending.current){leave(true);return;}if(!remember||!data){leave(true);return;}pending.current=true;setBusy(true);setError('');const id=serial.current;
  try{await api(base(project)+'/ritual',{etag:data.etag,settings:{...data.settings,skip_remembered:true}},'PUT');if(id===serial.current)leave(true);}
  catch(reason){if(id===serial.current){setError(String(reason).replace(/^Error: /,''));setRemember(false);}}finally{if(id===serial.current){pending.current=false;setBusy(false);}}
 }
 function nextStep(){if(step?.kind==='goal'&&goalDirty)setGoal(String(data?.goals.daily||''));if(index===steps.length-1)leave();else{setIndex(value=>value+1);setMessage('');}}
 async function saveGoal(event:React.FormEvent){
  event.preventDefault();if(pending.current||!data)return;const value=Number(goal);if(!Number.isInteger(value)||value<0||value>1000000)return;
  const advance=(event.nativeEvent as SubmitEvent).submitter?.getAttribute('data-next')==='true';
  pending.current=true;setBusy(true);setError('');setMessage('');const id=serial.current,submitted=goal;
  try{const result=await api<{goals:Record<string,unknown>}>(base(project)+'/ritual/daily-goal',{daily:value,expected_daily:Number(data.goals.daily||0)},'PUT');invalidateWritingMetrics(project,'goals');
   if(id===serial.current){setData(current=>current?{...current,goals:result.goals}:current);setMessage(tr('goalSaved'));if(advance&&live.current.goal===submitted){if(index===steps.length-1)leave(false,result.goals.daily);else setIndex(current=>current+1);}}}
  catch(reason){if(id===serial.current)setError((reason as {code?:string})?.code==='RITUAL_GOAL_CHANGED'?tr('goalConflict'):String(reason).replace(/^Error: /,''));}
  finally{if(id===serial.current){pending.current=false;setBusy(false);}}
 }
 async function refreshGoal(){if(!data||pending.current)return;pending.current=true;setBusy(true);setError('');const id=serial.current;
  try{const latest=await loadWritingRitual(project);if(id!==serial.current)return;setData(current=>current?{...current,goals:latest.goals}:current);setMessage(tr('goalRefreshed'));}
  catch(reason){if(id===serial.current)setError(String(reason).replace(/^Error: /,''));}finally{if(id===serial.current){pending.current=false;setBusy(false);}}
 }
 async function saveReflection(event:React.FormEvent){event.preventDefault();if(pending.current||!data||!reflection.trim())return;pending.current=true;setBusy(true);setError('');setMessage('');const id=serial.current,submitted=reflection;
  try{const result=await api<{note:string}>(base(project)+'/ritual/reflection',{day:data.date,text:submitted,expected_note:data.note},'PUT');invalidateWritingMetrics(project,'note');if(id===serial.current){setData(current=>current?{...current,note:result.note}:current);setReflection(current=>current===submitted?'':current);setMessage(tr('reflectionSaved'));}}
  catch(reason){if(id===serial.current)setError(String(reason).replace(/^Error: /,''));}finally{if(id===serial.current){pending.current=false;setBusy(false);}}
 }
 return <section className="writing-ritual" aria-labelledby={headingId}><header><div><small>{tr(phase==='start'?'before':'after')}</small><h2 id={headingId}>{tr(phase==='start'?'startTitle':'endTitle')}</h2><p>{tr('alwaysOptional')}</p></div>{onClose&&<button onClick={()=>closeHandler.current()}>{tr('close')}</button>}</header>
  {loading&&<p role="status">{tr('loading')}</p>}{error&&<p role="alert" className="ritual-error">{error}</p>}{confirmClose&&<div className="ritual-close-review"><strong>{tr('closeUnsaved')}</strong><p>{tr('closeUnsavedHelp')}</p><button onClick={()=>setConfirmClose(false)}>{tr('keepEditing')}</button><button onClick={()=>{setReflection('');setGoal(String(data?.goals.daily||''));setConfirmClose(false);callbacks.current.onClose?.();}}>{tr('discardAndClose')}</button></div>}
  {data&&step&&<><div className="ritual-progress" aria-label={tr('stepProgress',{current:index+1,total:steps.length})}><span>{tr('stepProgress',{current:index+1,total:steps.length})}</span><progress max={steps.length} value={index+1}/></div><div className="ritual-current-step"><h3>{stepLabel(step)}</h3>
   {step.kind==='goal'&&<form onSubmit={event=>void saveGoal(event)}><p>{tr('goalHelp')}</p><label>{tr('dailyGoal')}<input type="number" min={0} max={1000000} step={1} value={goal} onChange={event=>setGoal(event.target.value)}/></label><div className="ritual-actions"><button disabled={busy||!goalDirty}>{tr('saveGoal')}</button><button data-next="true" disabled={busy}>{tr('saveAndContinue')}</button><button type="button" disabled={busy} onClick={()=>void refreshGoal()}>{tr('refreshGoal')}</button></div><small>{tr(goalDirty?'goalUnsaved':'goalSavedState')}</small></form>}
   {step.kind==='focus'&&<><p>{tr('focusHelp')}</p><button disabled={busy} onClick={()=>{leave();requestAnimationFrame(()=>window.dispatchEvent(new CustomEvent(OPEN_FOCUS_TOOLS_EVENT,{detail:{project}})));}}>{tr('openFocus')}</button><small>{tr('focusNotAutomatic')}</small></>}
   {step.kind==='checklist'&&<label className="ritual-toggle"><input type="checkbox" checked={!!checked[step.id]} onChange={event=>setChecked(current=>({...current,[step.id]:event.target.checked}))}/>{tr('markReady')}</label>}
   {step.kind==='reflection'&&<form onSubmit={event=>void saveReflection(event)}><p>{tr('reflectionHelp',{day:data.date})}</p>{data.note&&<details><summary>{tr('existingNote')}</summary><p className="ritual-existing-note">{data.note}</p></details>}<label>{tr('reflectionLabel')}<textarea maxLength={500} rows={3} value={reflection} onChange={event=>setReflection(event.target.value)}/></label><small>{tr('reflectionAppend')}</small><button disabled={busy||!reflection.trim()}>{busy?tr('saving'):tr('saveReflection')}</button></form>}
  </div><div className="ritual-actions"><button disabled={!index||busy} onClick={()=>{setIndex(value=>value-1);setMessage('');}}>{tr('previous')}</button><button disabled={busy||!!reflection.trim()} onClick={nextStep}>{tr(step.kind==='goal'&&goalDirty?'nextWithoutGoal':index===steps.length-1?'finish':'next')}</button>{reflection.trim()&&<small>{tr('draftSkipHint')}</small>}</div></>}
  <p role="status">{message}</p><footer><label className="ritual-toggle"><input type="checkbox" checked={remember} disabled={busy||!data} onChange={event=>setRemember(event.target.checked)}/>{tr('rememberSkip')}</label>{busy&&<small className="ritual-muted">{tr('savingSkipNotice')}</small>}<button onClick={()=>void skip()}>{tr(goalDirty||reflection.trim()?'skipDiscard':phase==='start'?'skipToWriting':'skipEnd')}</button></footer>
 </section>;
}
