/** Local, opt-in focus tools. No AI, filesystem or network access in this runtime. */
export const EDITOR_ACTIVITY_EVENT='novel-editor-activity';
export const FOCUS_SETTINGS_EVENT='novel-focus-settings-changed';
export const TYPING_AUDIO_EVENT='novel-typing-audio-status';
export const OPEN_FOCUS_TOOLS_EVENT='novel-open-focus-tools';
export const FOCUS_SETTINGS_KEY='novel-focus-tools:v1';
export const WELLBEING_TODAY_KEY='novel-wellbeing-today:v1';
export const RECENT_TYPING_MS=60000;
const sittingLimitMs=(minutes:number)=>[45,60,90].includes(minutes)?minutes*60000:60*60000;
export type ActivityScope={project:string;path:string};
export type EditorFocusOptions={typewriter:boolean;typingSound:boolean;typingVolume:number};
export type FocusSettings=EditorFocusOptions&{focusMinutes:number;breakMinutes:number;wellbeing:boolean;sittingReminder:boolean;eyeReminder:boolean;sittingMinutes:45|60|90};
export const focusDefaults:FocusSettings={typewriter:false,typingSound:false,typingVolume:0.25,focusMinutes:25,breakMinutes:5,wellbeing:false,sittingReminder:false,eyeReminder:false,sittingMinutes:60};
const finite=(value:unknown,fallback:number,min:number,max:number)=>typeof value==='number'&&Number.isFinite(value)?Math.min(max,Math.max(min,value)):fallback;
export function normalizeFocusSettings(value:unknown):FocusSettings {
 const row=value&&typeof value==='object'?value as Partial<FocusSettings>:{};
 const bool=(key:keyof FocusSettings)=>typeof row[key]==='boolean'?row[key] as boolean:focusDefaults[key] as boolean;
 return {typewriter:bool('typewriter'),typingSound:bool('typingSound'),typingVolume:finite(row.typingVolume,focusDefaults.typingVolume,0,1),focusMinutes:Math.round(finite(row.focusMinutes,25,1,180)),breakMinutes:Math.round(finite(row.breakMinutes,5,1,60)),wellbeing:bool('wellbeing'),sittingReminder:bool('sittingReminder'),eyeReminder:bool('eyeReminder'),sittingMinutes:([45,60,90].includes(Number(row.sittingMinutes))?Number(row.sittingMinutes):60) as 45|60|90};
}
export function loadFocusSettings(storage:Pick<Storage,'getItem'>=localStorage):FocusSettings {try{return normalizeFocusSettings(JSON.parse(storage.getItem(FOCUS_SETTINGS_KEY)||'null'));}catch{return {...focusDefaults};}}
export function saveFocusSettings(settings:FocusSettings,storage:Pick<Storage,'setItem'>=localStorage):boolean {try{storage.setItem(FOCUS_SETTINGS_KEY,JSON.stringify(normalizeFocusSettings(settings)));return true;}catch{return false;}}
export function localDay(date=new Date()){return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');}
export function clockText(ms:number){const seconds=Math.max(0,Math.ceil(ms/1000));return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');}
export function notifyEditorActivity(scope:ActivityScope|undefined){if(scope)window.dispatchEvent(new CustomEvent<ActivityScope>(EDITOR_ACTIVITY_EVENT,{detail:{project:scope.project,path:scope.path}}));}

/** Monotonic user-started countdown; it never claims to measure writing duration. */
export class CountdownClock {
 status:'IDLE'|'RUNNING'|'PAUSED'|'COMPLETE'='IDLE';
 remainingMs=0;
 private deadline=0;
 private durationMs=0;
 get elapsedMs(){return Math.max(0,this.durationMs-this.remainingMs);}
 start(durationMs:number,now:number){this.remainingMs=Math.max(0,Number.isFinite(durationMs)?durationMs:0);this.durationMs=this.remainingMs;this.deadline=now+this.remainingMs;this.status=this.remainingMs?'RUNNING':'COMPLETE';}
 sample(now:number){if(this.status==='RUNNING'){this.remainingMs=Math.max(0,this.deadline-now);if(!this.remainingMs)this.status='COMPLETE';}return this.remainingMs;}
 pause(now:number){this.sample(now);if(this.status==='RUNNING')this.status='PAUSED';}
 resume(now:number){if(this.status==='PAUSED'){this.deadline=now+this.remainingMs;this.status='RUNNING';}}
 end(){this.status='IDLE';this.remainingMs=0;this.deadline=0;}
}
export type ForegroundState={visible:boolean;focused:boolean;editorVisible:boolean};
export type WellbeingSnapshot={day:string;activeMs:number};
export type ActivityReason='DISABLED'|'BACKGROUND'|'NO_EDITOR'|'IDLE'|'ACTIVE';
export function loadWellbeingToday(day=localDay(),storage:Pick<Storage,'getItem'>=localStorage):WellbeingSnapshot {try{const value=JSON.parse(storage.getItem(WELLBEING_TODAY_KEY)||'null');if(value?.day===day)return {day,activeMs:finite(value.activeMs,0,0,86400000)};}catch{}return {day,activeMs:0};}
export function saveWellbeingToday(snapshot:WellbeingSnapshot,storage:Pick<Storage,'setItem'>=localStorage):boolean {try{storage.setItem(WELLBEING_TODAY_KEY,JSON.stringify({day:snapshot.day,activeMs:Math.round(snapshot.activeMs)}));return true;}catch{return false;}}

/** Approximate foreground recent-input activity, never application uptime or writing time. */
export class ForegroundActivityClock {
 snapshot:WellbeingSnapshot;
 private enabled=false;
 private lastTick:number|null=null;
 private lastTyped:number|null=null;
 private activeStart:number|null=null;
 private previousEligible=false;
 private sittingMs=0;
 private eyeMs=0;
 private deferred:{kinds:('sit'|'eye')[];remainingMs:number}|null=null;
 muted=false;
 constructor(snapshot:WellbeingSnapshot){this.snapshot={...snapshot};}
 setEnabled(enabled:boolean){if(this.enabled===enabled)return;this.enabled=enabled;this.lastTick=null;this.lastTyped=null;this.activeStart=null;this.previousEligible=false;this.sittingMs=0;this.eyeMs=0;this.deferred=null;}
 typing(now:number){if(!this.enabled)return;if(this.lastTyped===null||now-this.lastTyped>RECENT_TYPING_MS)this.activeStart=now;this.lastTyped=now;}
 inspect(now:number,state:ForegroundState,settings:Pick<FocusSettings,'sittingMinutes'>&Partial<Pick<FocusSettings,'wellbeing'>>){
  const reason:ActivityReason=!(settings.wellbeing??this.enabled)?'DISABLED':!state.visible||!state.focused?'BACKGROUND':!state.editorVisible?'NO_EDITOR':this.lastTyped===null||now-this.lastTyped>=RECENT_TYPING_MS?'IDLE':'ACTIVE';
  return {reason,sittingRemainingMs:Math.max(0,sittingLimitMs(settings.sittingMinutes)-this.sittingMs),eyeRemainingMs:Math.max(0,20*60000-this.eyeMs),deferredRemainingMs:this.deferred?.remainingMs??0};
 }
 defer(kinds:('sit'|'eye')[],delayMs=5*60000){if(!this.enabled||this.muted||!kinds.length)return;this.deferred={kinds:[...new Set(kinds)],remainingMs:Math.min(30*60000,Math.max(1000,Number.isFinite(delayMs)?delayMs:5*60000))};}
 clearDeferred(kind?:'sit'|'eye'){if(!this.deferred)return;if(!kind){this.deferred=null;return;}this.deferred.kinds=this.deferred.kinds.filter(value=>value!==kind);if(!this.deferred.kinds.length)this.deferred=null;}
 rest(){this.deferred=null;this.lastTick=null;this.lastTyped=null;this.activeStart=null;this.previousEligible=false;this.sittingMs=0;this.eyeMs=0;}
 sample(now:number,day:string,state:ForegroundState,settings:Pick<FocusSettings,'sittingReminder'|'eyeReminder'|'sittingMinutes'>):{addedMs:number;reminders:('sit'|'eye')[]} {
  if(this.snapshot.day!==day){this.snapshot={day,activeMs:0};this.sittingMs=0;this.eyeMs=0;this.lastTick=null;this.previousEligible=false;this.deferred=null;}
  const eligible=this.enabled&&state.visible&&state.focused&&state.editorVisible;
  let added=0;
  if(eligible&&this.previousEligible&&this.lastTick!==null&&this.lastTyped!==null){
   // A delayed/background callback cannot count past the recent-input window.
   const start=Math.max(this.lastTick,this.activeStart??this.lastTyped);
   const end=Math.min(now,this.lastTyped+RECENT_TYPING_MS);
   added=Math.max(0,Math.min(end-start,RECENT_TYPING_MS));
  }
  this.lastTick=now;this.previousEligible=eligible;
  this.snapshot.activeMs=Math.min(86400000,this.snapshot.activeMs+added);
  this.sittingMs+=added;this.eyeMs+=added;
  const reminders=new Set<'sit'|'eye'>();
  const sitLimit=sittingLimitMs(settings.sittingMinutes),eyeLimit=20*60000;
  if(this.sittingMs>=sitLimit){this.sittingMs%=sitLimit;if(settings.sittingReminder&&!this.muted&&!this.deferred?.kinds.includes('sit'))reminders.add('sit');}
  if(this.eyeMs>=eyeLimit){this.eyeMs%=eyeLimit;if(settings.eyeReminder&&!this.muted&&!this.deferred?.kinds.includes('eye'))reminders.add('eye');}
  if(this.deferred){this.deferred.remainingMs=Math.max(0,this.deferred.remainingMs-added);if(!this.deferred.remainingMs){for(const kind of this.deferred.kinds){if(!this.muted&&(kind==='sit'?settings.sittingReminder:settings.eyeReminder))reminders.add(kind);}this.deferred=null;}}
  return {addedMs:added,reminders:[...reminders]};
 }
}

/** A tiny bundled sound, initialized only after an enabled real typing event. */
export class TypingAudio {
 private voices:HTMLAudioElement[]=[];
 private enabled=false;
 private volume=0.25;
 private failed=false;
 private lastAt=-Infinity;
 private next=0;
 private generation=0;
 constructor(private readonly source:string){}
 configure(enabled:boolean,volume:number){const was=this.enabled;this.enabled=enabled;this.volume=finite(volume,0.25,0,1);if(!enabled||this.volume===0)this.stop();if(enabled&&!was)this.failed=false;for(const voice of this.voices)voice.volume=this.volume;}
 play(now=performance.now()){
  if(!this.enabled||this.volume<=0||this.failed||now-this.lastAt<35)return;
  this.lastAt=now;
  try{
   if(!this.voices.length){for(let i=0;i<2;i++){const audio=new Audio(this.source);audio.preload='auto';audio.volume=this.volume;this.voices.push(audio);}}
   const voice=this.voices[this.next++%this.voices.length];voice.pause();voice.currentTime=0;voice.volume=this.volume;
   const generation=this.generation;
   const pending=voice.play();if(pending&&typeof pending.catch==='function')void pending.catch(()=>{if(generation===this.generation&&this.enabled&&this.volume>0)this.unavailable();});
  }catch{this.unavailable();}
 }
 private unavailable(){if(this.failed)return;this.failed=true;this.stop();window.dispatchEvent(new CustomEvent(TYPING_AUDIO_EVENT,{detail:{status:'UNAVAILABLE'}}));}
 stop(){this.generation++;for(const voice of this.voices){voice.pause();try{voice.currentTime=0;}catch{}}}
 dispose(){this.stop();for(const voice of this.voices){voice.removeAttribute('src');voice.load();}this.voices=[];}
}
