import {useEffect,useId,useRef,useState} from 'react';
import {Play,Pause,Square,Keyboard,Volume2,VolumeX,PanelLeftClose,X} from 'lucide-react';
import {api} from './api';
import {t,useUiTranslation} from './i18n';
import {CountdownClock,ForegroundActivityClock,TypingAudio,EDITOR_ACTIVITY_EVENT,FOCUS_SETTINGS_EVENT,TYPING_AUDIO_EVENT,OPEN_FOCUS_TOOLS_EVENT,clockText,focusDefaults,loadFocusSettings,saveFocusSettings,loadWellbeingToday,saveWellbeingToday,localDay,type ActivityScope,type EditorFocusOptions,type FocusSettings} from './focus-runtime';
import './focus-tools.css';
const tr=(key:string,options?:Record<string,unknown>)=>t('focus:'+key,options);
type Cursor={event_count:number;fingerprint:string};
type Boundary={project_id:string;cursor:Cursor;started_at:string;timezone:string};
type Summary={project_id:string;net_han:number;manual_han:number;ai_han:number;restore_han:number;unknown_han:number;save_count:number;recorded_until:string};
type FrozenSummaryRequest={readonly cursor:Readonly<Cursor>;readonly end_cursor:Readonly<Cursor>};
type FocusSession={id:number;project:string;boundary:Boundary|null;ended:boolean;elapsedMs:number;summaryRequest:FrozenSummaryRequest|null;summaryPending:boolean};
type Reminder='sit'|'eye'|'both';
const editorOptions=(settings:FocusSettings):EditorFocusOptions=>({typewriter:settings.typewriter,typingSound:settings.typingSound,typingVolume:settings.typingVolume});
const signed=(value:number)=>value>0?'+'+value.toLocaleString():value.toLocaleString();

/** User-controlled focus tools; wellbeing below has no backend or AI requests. */
export function FocusTools({project,path,visible=true,onEditorOptions,focusMode=false,onFocusMode}:{project:string|null;path?:string|null;visible?:boolean;onEditorOptions?:(options:EditorFocusOptions)=>void;focusMode?:boolean;onFocusMode?:(enabled:boolean)=>void}) {
 useUiTranslation('focus');
 const controlId=useId();
 const [settings,setSettings]=useState<FocusSettings>(()=>loadFocusSettings());
 const [clockView,setClockView]=useState({status:'IDLE' as CountdownClock['status'],remainingMs:0});
 const [phase,setPhase]=useState<'focus'|'break'>('focus');
 const [starting,setStarting]=useState(false),[externalOpen,setExternalOpen]=useState(false),[expanded,setExpanded]=useState(false);
 const [summary,setSummary]=useState<Summary|null>(null);
 const [summaryStatus,setSummaryStatus]=useState<'NONE'|'PENDING'|'FAILED'|'READY'>('NONE');
 const [message,setMessage]=useState(''),[settingsNotice,setSettingsNotice]=useState('');
 const [storageWarning,setStorageWarning]=useState(false),[audioWarning,setAudioWarning]=useState(false);
 const [healthNotice,setHealthNotice]=useState<Reminder|null>(null),[muted,setMuted]=useState(false);
 const [activeMs,setActiveMs]=useState(()=>loadWellbeingToday().activeMs);
 const [,refreshHealthView]=useState(0);
 const [foreground,setForeground]=useState(()=>document.visibilityState!=='hidden'&&document.hasFocus());
 const countdown=useRef(new CountdownClock());
 const wellbeing=useRef<ForegroundActivityClock|null>(null);
 if(!wellbeing.current)wellbeing.current=new ForegroundActivityClock(loadWellbeingToday());
 const sampleAudio=useRef<TypingAudio|null>(null),session=useRef<FocusSession|null>(null),serial=useRef(0);
 const details=useRef<HTMLDetailsElement|null>(null),panel=useRef<HTMLDivElement|null>(null),trigger=useRef<HTMLElement|null>(null),previousFocus=useRef<HTMLElement|null>(null);
 const live=useRef({project,path,visible,settings,phase});live.current={project,path,visible,settings,phase};
 const onOptions=useRef(onEditorOptions);onOptions.current=onEditorOptions;
 const disposed=useRef(false),lastPersist=useRef(0),completed=useRef(false);
 const [focusInput,setFocusInput]=useState(String(settings.focusMinutes)),[breakInput,setBreakInput]=useState(String(settings.breakMinutes));
 const state=()=>({visible:document.visibilityState!=='hidden',focused:document.hasFocus(),editorVisible:live.current.visible&&!!live.current.project&&!!live.current.path});
 const announce=(text:string)=>window.dispatchEvent(new CustomEvent('studio-feedback',{detail:{message:text}}));
 const refreshClock=()=>setClockView({status:countdown.current.status,remainingMs:countdown.current.remainingMs});
 const persistHealth=()=>{if(wellbeing.current&&!saveWellbeingToday(wellbeing.current.snapshot))setStorageWarning(true);};
 const apply=(values:Partial<FocusSettings>)=>{setSettingsNotice('');if(values.sittingReminder===false)wellbeing.current!.clearDeferred('sit');if(values.eyeReminder===false)wellbeing.current!.clearDeferred('eye');if(values.wellbeing===false)wellbeing.current!.clearDeferred();setSettings(current=>({...current,...values}));};
 const noticeText=(kind:Reminder)=>tr(kind==='both'?'bothNotice':kind==='sit'?'sitNotice':'eyeNotice');
 const healthTick=()=>{
  const clock=wellbeing.current!,now=performance.now();
  const result=clock.sample(now,localDay(),state(),live.current.settings);
  setActiveMs(clock.snapshot.activeMs);refreshHealthView(value=>value+1);
  if(result.reminders.length){const kind:Reminder=result.reminders.length>1?'both':result.reminders[0];setHealthNotice(kind);announce(noticeText(kind));}
  if(now-lastPersist.current>10000){lastPersist.current=now;persistHealth();}
 };
 function openPanel(focusContent=false){
  if(!details.current?.open)previousFocus.current=document.activeElement as HTMLElement|null;
  setExternalOpen(true);setExpanded(true);if(details.current)details.current.open=true;
  healthTick();
  if(focusContent)requestAnimationFrame(()=>{if(!disposed.current&&details.current?.open)panel.current?.focus({preventScroll:true});});
 }
 function closePanel(restoreFocus=false){
  if(details.current)details.current.open=false;setExternalOpen(false);setExpanded(false);
  if(restoreFocus){const target=live.current.visible?trigger.current:previousFocus.current;if(target?.isConnected)target.focus({preventScroll:true});}
 }
 async function readFrozenSummary(current:FocusSession){
  if(disposed.current||session.current?.id!==current.id||!current.ended||!current.summaryRequest||current.summaryPending)return;
  current.summaryPending=true;setSummaryStatus('PENDING');
  try{
   // Retrying this read must retain both boundaries and the original project.
   const result=await api<Summary>('/api/projects/'+encodeURIComponent(current.project)+'/experience/focus-summary',current.summaryRequest,'POST');
   if(disposed.current||session.current?.id!==current.id)return;
   setSummary(result);setSummaryStatus('READY');
  }catch{if(!disposed.current&&session.current?.id===current.id)setSummaryStatus('FAILED');}
  finally{current.summaryPending=false;}
 }
 async function finishFocus(current:FocusSession|null,elapsedMs=countdown.current.elapsedMs){
  if(!current||current.ended)return;
  current.ended=true;current.elapsedMs=elapsedMs;
  if(!current.boundary){setSummaryStatus('FAILED');return;}
  setSummaryStatus('PENDING');
  try{
   // Freeze once before queuing the read-only POST. Missing bounds cannot be recreated later.
   const end=await api<Boundary>('/api/projects/'+encodeURIComponent(current.project)+'/experience/focus-boundary');
   if(disposed.current||session.current?.id!==current.id)return;
   current.summaryRequest=Object.freeze({cursor:Object.freeze({...current.boundary.cursor}),end_cursor:Object.freeze({...end.cursor})});
   await readFrozenSummary(current);
  }catch{if(!disposed.current&&session.current?.id===current.id)setSummaryStatus('FAILED');}
 }
 function detectCompletion(){
  if(countdown.current.status!=='COMPLETE'||completed.current)return;
  completed.current=true;const text=tr(live.current.phase==='focus'?'focusComplete':'breakComplete');setMessage(text);announce(text);
  if(live.current.phase==='focus')void finishFocus(session.current);
 }
 const tick=()=>{countdown.current.sample(performance.now());detectCompletion();refreshClock();if(live.current.settings.wellbeing)healthTick();};
 useEffect(()=>{
  disposed.current=false;
  return()=>{disposed.current=true;saveWellbeingToday(wellbeing.current!.snapshot);sampleAudio.current?.dispose();};
 },[]);
 useEffect(()=>{
  if(!saveFocusSettings(settings))setStorageWarning(true);
  wellbeing.current!.setEnabled(settings.wellbeing);onOptions.current?.(editorOptions(settings));
  window.dispatchEvent(new CustomEvent(FOCUS_SETTINGS_EVENT,{detail:editorOptions(settings)}));
  sampleAudio.current?.configure(settings.typingSound,settings.typingVolume);
  if(!settings.wellbeing)setHealthNotice(null);
 },[settings]);
 useEffect(()=>{
  const activity=(event:Event)=>{const detail=(event as CustomEvent<ActivityScope>).detail;if(detail?.project!==live.current.project||detail.path!==live.current.path||!live.current.visible)return;const foreground=state();if(foreground.visible&&foreground.focused)wellbeing.current!.typing(performance.now());};
  const foregroundChanged=()=>{healthTick();setForeground(document.visibilityState!=='hidden'&&document.hasFocus());persistHealth();};
  const audioStatus=()=>setAudioWarning(true),flush=()=>persistHealth(),open=()=>openPanel(true);
  const outside=(event:PointerEvent)=>{if(details.current?.open&&!details.current.contains(event.target as Node))closePanel();};
  window.addEventListener(EDITOR_ACTIVITY_EVENT,activity);document.addEventListener('visibilitychange',foregroundChanged);window.addEventListener('focus',foregroundChanged);window.addEventListener('blur',foregroundChanged);window.addEventListener('pagehide',flush);window.addEventListener(TYPING_AUDIO_EVENT,audioStatus);window.addEventListener(OPEN_FOCUS_TOOLS_EVENT,open);document.addEventListener('pointerdown',outside);
  return()=>{window.removeEventListener(EDITOR_ACTIVITY_EVENT,activity);document.removeEventListener('visibilitychange',foregroundChanged);window.removeEventListener('focus',foregroundChanged);window.removeEventListener('blur',foregroundChanged);window.removeEventListener('pagehide',flush);window.removeEventListener(TYPING_AUDIO_EVENT,audioStatus);window.removeEventListener(OPEN_FOCUS_TOOLS_EVENT,open);document.removeEventListener('pointerdown',outside);};
 },[]);
 useEffect(()=>{healthTick();},[visible,project,path,settings.wellbeing]);
 useEffect(()=>{
  // One small local clock serves both tools. No heartbeat when all tools are off.
  if(clockView.status!=='RUNNING'&&!(settings.wellbeing&&visible&&foreground&&project&&path))return;
  const timer=window.setInterval(tick,1000);return()=>window.clearInterval(timer);
 },[clockView.status,settings.wellbeing,visible,foreground,project,path]);
 async function startFocus(){
  if(!project||starting||countdown.current.status==='RUNNING'||countdown.current.status==='PAUSED')return;
  const current:FocusSession={id:++serial.current,project,boundary:null,ended:false,elapsedMs:0,summaryRequest:null,summaryPending:false};session.current=current;setSummary(null);setSummaryStatus('NONE');setMessage('');setStarting(true);completed.current=false;setPhase('focus');
  try{current.boundary=await api<Boundary>('/api/projects/'+encodeURIComponent(project)+'/experience/focus-boundary');}
  catch{if(!disposed.current&&!current.ended&&session.current?.id===current.id)setMessage(tr('boundaryUnavailable'));}
  if(disposed.current||current.ended||session.current?.id!==current.id)return;
  setStarting(false);countdown.current.start(live.current.settings.focusMinutes*60000,performance.now());refreshClock();
 }
 function cancelPreparation(showMessage=true){if(session.current)session.current.ended=true;setStarting(false);if(showMessage)setMessage(tr('preparationCancelled'));}
 function startBreak(){if(starting||countdown.current.status==='RUNNING'||countdown.current.status==='PAUSED')return;setPhase('break');setMessage('');completed.current=false;countdown.current.start(settings.breakMinutes*60000,performance.now());refreshClock();}
 function pauseOrResume(){if(countdown.current.status==='RUNNING')countdown.current.pause(performance.now());else countdown.current.resume(performance.now());detectCompletion();refreshClock();}
 function end(){countdown.current.sample(performance.now());if(countdown.current.status==='COMPLETE'){detectCompletion();refreshClock();return;}const focus=phase==='focus',elapsed=countdown.current.elapsedMs;countdown.current.end();refreshClock();setMessage(tr(focus?'focusEnded':'breakEnded'));if(focus)void finishFocus(session.current,elapsed);}
 function disableAll(){if(starting)cancelPreparation(false);if(countdown.current.status==='RUNNING'||countdown.current.status==='PAUSED')end();apply({typewriter:false,typingSound:false,wellbeing:false,sittingReminder:false,eyeReminder:false});sampleAudio.current?.stop();setHealthNotice(null);persistHealth();}
 function restoreDefaults(){if(starting||countdown.current.status==='RUNNING'||countdown.current.status==='PAUSED')return;setSettings({...focusDefaults});setFocusInput(String(focusDefaults.focusMinutes));setBreakInput(String(focusDefaults.breakMinutes));wellbeing.current!.muted=false;setMuted(false);setAudioWarning(false);setHealthNotice(null);setSettingsNotice(tr('defaultsRestored'));}
 function restNow(){wellbeing.current!.rest();setHealthNotice(null);healthTick();}
 function postponeReminder(){if(!healthNotice||muted)return;wellbeing.current!.defer(healthNotice==='both'?['sit','eye']:[healthNotice]);setHealthNotice(null);healthTick();}
 function cancelPostponement(){wellbeing.current!.clearDeferred();healthTick();}
 function toggleTypingSound(){setAudioWarning(false);apply({typingSound:!settings.typingSound});}
 function testSound(){if(!settings.typingSound)return;setAudioWarning(false);if(!sampleAudio.current)sampleAudio.current=new TypingAudio(import.meta.env.BASE_URL+'sounds/typewriter-soft.wav');sampleAudio.current.configure(false,settings.typingVolume);sampleAudio.current.configure(true,settings.typingVolume);sampleAudio.current.play();}
 const activeTimer=clockView.status==='RUNNING'||clockView.status==='PAUSED';
 const health=wellbeing.current.inspect(performance.now(),state(),settings);
 const pendingNotice=settings.wellbeing&&healthNotice&&!muted;
 return <div className={'focus-tools'+(!visible?' focus-tools-global':'')} hidden={!visible&&!externalOpen}>
  {visible&&<div className="focus-quick-controls" role="group" aria-label={tr('quickControls')}>
   <button type="button" className="focus-quick-primary" data-focus-action="timer" disabled={!project&&!activeTimer&&!starting} onMouseDown={event=>event.preventDefault()} onClick={()=>starting?cancelPreparation():activeTimer?pauseOrResume():void startFocus()} title={starting?tr('cancelPreparation'):activeTimer?tr(clockView.status==='RUNNING'?'pause':'resume'):tr('quickStartTitle',{count:settings.focusMinutes})} aria-label={starting?tr('cancelPreparation'):activeTimer?tr(clockView.status==='RUNNING'?'pause':'resume'):tr('startFocus')}>{starting?<Square size={12} aria-hidden="true"/>:clockView.status==='RUNNING'?<Pause size={13} aria-hidden="true"/>:<Play size={13} aria-hidden="true"/>}<span>{tr(starting?'quickCancel':activeTimer?clockView.status==='RUNNING'?'pause':'resume':'quickStart')}</span></button>
   {activeTimer&&<button type="button" data-focus-action="end" className="focus-quick-icon" title={tr('end')} aria-label={tr('end')} onMouseDown={event=>event.preventDefault()} onClick={end}><Square size={12} aria-hidden="true"/></button>}
   {clockView.status==='COMPLETE'&&phase==='focus'&&<button type="button" data-focus-action="break" className="focus-quick-short" title={tr('startBreak')} onMouseDown={event=>event.preventDefault()} onClick={startBreak}>{tr('quickBreak')}</button>}
   {onFocusMode&&<button type="button" data-focus-action="layout" className="focus-quick-icon" aria-pressed={focusMode} title={tr(focusMode?'exitFocusLayout':'enterFocusLayout')} aria-label={tr('focusLayout')} onMouseDown={event=>event.preventDefault()} onClick={()=>onFocusMode(!focusMode)}><PanelLeftClose size={15} aria-hidden="true"/></button>}
   <button type="button" data-focus-action="typewriter" className="focus-quick-icon" aria-pressed={settings.typewriter} title={tr('typewriter')} aria-label={tr('typewriter')} onMouseDown={event=>event.preventDefault()} onClick={()=>apply({typewriter:!settings.typewriter})}><Keyboard size={15} aria-hidden="true"/></button>
   <button type="button" data-focus-action="sound" className="focus-quick-icon" aria-pressed={settings.typingSound} title={settings.typingSound&&settings.typingVolume===0?tr('soundZeroVolume'):tr('typingSound')} aria-label={tr('typingSound')} onMouseDown={event=>event.preventDefault()} onClick={toggleTypingSound}>{settings.typingSound&&settings.typingVolume>0?<Volume2 size={15} aria-hidden="true"/>:<VolumeX size={15} aria-hidden="true"/>}</button>
  </div>}
  <details key="focus-settings" ref={details} className="focus-tools-popover" onToggle={()=>{const open=!!details.current?.open;setExpanded(open);if(!open)setExternalOpen(false);}} onKeyDown={event=>{if(event.key==='Escape'&&details.current?.open){event.preventDefault();event.stopPropagation();closePanel(true);}}}>
   <summary ref={trigger} aria-expanded={expanded} aria-controls={controlId}><span aria-hidden="true">◷</span> <span className="focus-trigger-label">{tr('title')}</span>{activeTimer?<span className="focus-mini-countdown">{clockText(clockView.remainingMs)}{clockView.status==='PAUSED'?' · '+tr('paused'):''}</span>:clockView.status==='COMPLETE'?<span className="focus-mini-countdown">{tr(phase==='focus'?'focusDoneBadge':'breakDoneBadge')}</span>:null}{pendingNotice&&<span className="focus-notice-dot" aria-label={tr('restReminder')}/>}</summary>
   <div id={controlId} ref={panel} tabIndex={-1} className="focus-tools-panel" aria-label={tr('title')}>
    <header><h3>{tr('title')}</h3><div className="focus-header-actions"><button type="button" disabled={activeTimer||starting} title={tr(activeTimer||starting?'defaultsWait':'defaultsHelp')} onClick={restoreDefaults}>{tr('restoreDefaults')}</button><button type="button" onClick={disableAll}>{tr('disableAll')}</button><button type="button" className="focus-close-button" title={tr('closePanel')} aria-label={tr('closePanel')} onClick={()=>closePanel(true)}><X size={15} aria-hidden="true"/></button></div></header><p className="focus-help">{tr('intro')}</p>
    <section aria-label={tr('timerTitle')}><h4>{tr('timerTitle')}</h4><p className="focus-help">{tr('timerHelp')}</p>
     <details className="focus-config"><summary>{tr('timerSettings')}</summary><div className="focus-duration-fields"><label>{tr('focusMinutes')}<input type="number" min={1} max={180} step={1} value={focusInput} onChange={event=>setFocusInput(event.target.value)} onBlur={()=>{const value=Math.min(180,Math.max(1,Math.round(Number(focusInput)||25)));setFocusInput(String(value));apply({focusMinutes:value});}} disabled={activeTimer||starting}/></label><label>{tr('breakMinutes')}<input type="number" min={1} max={60} step={1} value={breakInput} onChange={event=>setBreakInput(event.target.value)} onBlur={()=>{const value=Math.min(60,Math.max(1,Math.round(Number(breakInput)||5)));setBreakInput(String(value));apply({breakMinutes:value});}} disabled={activeTimer||starting}/></label></div></details>
     <div className="focus-countdown"><span>{tr(phase==='focus'?'focusPhase':'breakPhase')}</span><strong role="timer" aria-live="off" aria-label={tr('countdownLabel',{phase:tr(phase==='focus'?'focusPhase':'breakPhase'),time:clockText(clockView.remainingMs)})}>{clockText(clockView.remainingMs)}</strong><small>{tr(clockView.status==='RUNNING'?'running':clockView.status==='PAUSED'?'paused':clockView.status==='COMPLETE'?'completed':'notStarted')}</small></div>
     <div className="focus-actions">{starting?<><span className="focus-help" role="status">{tr('starting')}</span><button type="button" onClick={()=>cancelPreparation()}>{tr('cancelPreparation')}</button></>:!activeTimer?<><button className="primary" type="button" disabled={!project} onClick={()=>void startFocus()}>{tr('startFocus')}</button><button type="button" onClick={startBreak}>{tr('startBreak')}</button></>:<><button type="button" onClick={pauseOrResume}>{tr(clockView.status==='RUNNING'?'pause':'resume')}</button><button type="button" onClick={end}>{tr('end')}</button></>}</div>
     {message&&<p className="focus-inline-notice" role="status">{message}</p>}{session.current&&session.current.project!==project&&<p className="focus-help">{tr('otherProject')}</p>}
     {summaryStatus==='PENDING'&&<p role="status">{tr('summaryLoading')}</p>}{summaryStatus==='FAILED'&&<div className="focus-summary-failure" role="status"><p className="focus-help">{tr(session.current?.summaryRequest?'summaryRetryHelp':'summaryBoundsUnavailable')}</p>{session.current?.summaryRequest&&<button type="button" onClick={()=>{const current=session.current;if(current)void readFrozenSummary(current);}}>{tr('retrySummary')}</button>}</div>}{summaryStatus==='READY'&&summary&&<div className="focus-result"><b>{tr('summaryNet',{time:clockText(session.current?.elapsedMs||0),net:signed(summary.net_han)})}</b><p>{tr('summarySources',{manual:signed(summary.manual_han),ai:signed(summary.ai_han),restore:signed(summary.restore_han),unknown:signed(summary.unknown_han)})}</p><small>{tr('summaryHelp',{count:summary.save_count})}</small></div>}
    </section>
    <details className="focus-config focus-writing-config"><summary>{tr('writingFeel')}</summary><section aria-label={tr('writingFeel')}><label className="focus-check"><input type="checkbox" checked={settings.typewriter} onChange={event=>apply({typewriter:event.target.checked})}/><span>{tr('typewriter')}<small>{tr('typewriterHelp')}</small></span></label><label className="focus-check"><input type="checkbox" checked={settings.typingSound} onChange={event=>{setAudioWarning(false);apply({typingSound:event.target.checked});}}/><span>{tr('typingSound')}<small>{tr('typingSoundHelp')}</small></span></label><div className="focus-volume"><label>{tr('volume')}<input type="range" min={0} max={1} step={0.05} value={settings.typingVolume} aria-valuetext={Math.round(settings.typingVolume*100)+'%'} onChange={event=>apply({typingVolume:Number(event.target.value)})} disabled={!settings.typingSound}/></label><span>{Math.round(settings.typingVolume*100)}%</span><button type="button" onClick={testSound} disabled={!settings.typingSound}>{tr('previewSound')}</button></div>{audioWarning&&<p className="focus-help" role="status">{tr('audioUnavailable')}</p>}</section></details>
    <section aria-label={tr('wellbeingTitle')}><h4>{tr('wellbeingTitle')}</h4><p className="focus-help">{tr('wellbeingHelp')}</p><p className="focus-local-clock">{tr('todayActive',{time:clockText(activeMs)})}</p><label className="focus-check"><input type="checkbox" checked={settings.wellbeing} onChange={event=>apply({wellbeing:event.target.checked})}/><span>{tr('enableWellbeing')}<small>{tr('independentReminders')}</small></span></label>
     {settings.wellbeing&&<><p className="focus-activity-state" data-active={health.reason==='ACTIVE'}><span aria-hidden="true"/>{tr('activity'+health.reason)}</p><details className="focus-config"><summary>{tr('reminderSettings')}</summary><small className="focus-help">{tr('activityDefinition')}</small><div className="focus-reminder-options"><label className="focus-check"><input type="checkbox" checked={settings.sittingReminder} onChange={event=>apply({sittingReminder:event.target.checked})}/>{tr('sittingReminder')}</label><select aria-label={tr('sittingInterval')} value={settings.sittingMinutes} disabled={!settings.sittingReminder} onChange={event=>apply({sittingMinutes:Number(event.target.value) as 45|60|90})}>{[45,60,90].map(minutes=><option key={minutes} value={minutes}>{tr('minutes',{count:minutes})}</option>)}</select><label className="focus-check"><input type="checkbox" checked={settings.eyeReminder} onChange={event=>apply({eyeReminder:event.target.checked})}/>{tr('eyeReminder')}</label></div><p className="focus-help">{tr('eyeRule')}</p></details>
      {!settings.sittingReminder&&!settings.eyeReminder?<p className="focus-help">{tr('remindersOff')}</p>:<div className="focus-next-reminders">{settings.sittingReminder&&<span>{tr('nextSitting',{time:clockText(health.sittingRemainingMs)})}</span>}{settings.eyeReminder&&<span>{tr('nextEye',{time:clockText(health.eyeRemainingMs)})}</span>}</div>}{health.deferredRemainingMs>0&&<p className="focus-help">{tr('deferredRemaining',{time:clockText(health.deferredRemainingMs)})} <button type="button" onClick={cancelPostponement}>{tr('cancelPostponement')}</button></p>}{pendingNotice&&<div className="focus-inline-notice" role="status"><p>{noticeText(healthNotice)}</p></div>}<div className="focus-actions"><button type="button" onClick={restNow}>{tr('rested')}</button>{pendingNotice&&<button type="button" onClick={postponeReminder}>{tr('postpone')}</button>}<button type="button" onClick={()=>{const value=!wellbeing.current!.muted;wellbeing.current!.muted=value;setMuted(value);setHealthNotice(null);}}>{tr(muted?'resumeReminders':'muteForRun')}</button></div>{muted&&<p className="focus-help">{tr('mutedForRun')}</p>}</>}
     <small className="focus-help">{tr('localPrivacy')}</small>
    </section>{settingsNotice&&<p role="status" className="focus-help">{settingsNotice}</p>}{storageWarning&&<p role="status" className="focus-help">{tr('storageUnavailable')}</p>}
   </div>
  </details>{pendingNotice&&!expanded&&<div className="focus-inline-controls" role="group" aria-label={tr('restReminder')}><button type="button" className="focus-reminder-entry" onClick={()=>openPanel(true)} aria-label={tr('openReminder')}>{tr('restReminder')}</button><button type="button" data-focus-action="rested" onMouseDown={event=>event.preventDefault()} onClick={restNow}>{tr('quickRested')}</button><button type="button" data-focus-action="postpone" title={tr('postponeHelp')} onMouseDown={event=>event.preventDefault()} onClick={postponeReminder}>{tr('quickPostpone')}</button></div>}
  {visible&&!expanded&&settings.wellbeing&&!muted&&health.deferredRemainingMs>0&&<button type="button" className="focus-deferred-chip" title={tr('postponeHelp')} onClick={()=>openPanel(true)}>{tr('deferredChip',{time:clockText(health.deferredRemainingMs)})}</button>}
 </div>;
}
