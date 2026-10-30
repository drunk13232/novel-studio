import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {revisionText} from './revision-hunks';
import {base,useUnsavedChanges,saveJSON,type Data} from './library-shared';
import {t,useUiTranslation} from './i18n';

type Value={text:string;note:string;chosen_hunks:number[]|null};
type Options={project:string;id:string|null;variant?:number;text:string;note?:string;chosenHunks?:number[]|null;readOnly?:boolean;suspended?:boolean;onRestore:(value:Value)=>void};
type Session={key:string;etag:string;baseline:string;view:Data|null;initial:Value;pending:Promise<boolean>|null;checking:boolean;incoming:Data|null;recovery:Value|null;paused:boolean;controller?:AbortController};
type State={key:string;ready:boolean;saving:boolean;checking:boolean;error:string;view:Data|null;baseline:string;incoming:Data|null;recovery:Value|null;paused:boolean};
const signature=(v:Value)=>JSON.stringify({...v,text:revisionText(v.text)});
const failure=(error:unknown)=>String((error as {technicalDetail?:string;message?:string})?.technicalDetail||(error as Error)?.message||error);
const empty=(key:string):State=>({key,ready:false,saving:false,checking:false,error:'',view:null,baseline:'',incoming:null,recovery:null,paused:false});
const savedValue=(view:Data,fallback:Value):Value=>view.draft?{text:view.draft.text,note:view.draft.note||'',chosen_hunks:view.draft.chosen_hunks??null}:fallback;
export function useCandidateDraft(options:Options){
 const {project,id,variant=0,text,note='',chosenHunks=null,readOnly=false,suspended=false}=options;
 const key=id?project+':'+id+':'+variant:'';
 const value:Value={text,note,chosen_hunks:chosenHunks};
 const latest=useRef({key,value,restore:options.onRestore,readOnly});latest.current={key,value,restore:options.onRestore,readOnly};
 const session=useRef<Session|null>(null),[state,setState]=useState<State>(empty(''));
 const current=state.key===key?state:null,stamp=signature(value);
 const locked=readOnly||!!current?.view&&current.view.status!=='PROPOSED';
 const dirty=!!current?.recovery||!!key&&!locked&&!!current?.ready&&stamp!==current.baseline;
 useUnsavedChanges(dirty,t('writing:candidateUnsaved'));
 function publish(s:Session,error=''){
  if(session.current!==s||latest.current.key!==s.key)return;
  setState({key:s.key,ready:!!s.view,saving:!!s.pending,checking:s.checking,error,view:s.view,baseline:s.baseline,incoming:s.incoming,recovery:s.recovery,paused:s.paused});
 }
 async function read(s:Session,inspect:boolean){
  if(s.checking||s.pending||s.recovery)return false;const wasPaused=s.paused;s.checking=true;s.paused=inspect||s.paused;s.controller=new AbortController();publish(s);
  try{
   const view=await api<Data>(base(project)+'/studio-tools/candidates/'+id+'/draft?variant='+variant,undefined,'GET',{signal:s.controller.signal});
   if(session.current!==s||latest.current.key!==s.key)return false;
   if(inspect&&s.view){if(view.etag===s.etag){s.view=view;s.paused=wasPaused;}else s.incoming=view;}
   else{const restored=savedValue(view,s.initial);s.view=view;s.etag=view.etag;s.baseline=signature(restored);if(view.status==='PROPOSED'&&view.draft&&!latest.current.readOnly)latest.current.restore(restored);}
   s.checking=false;publish(s);return true;
  }catch(error){if(session.current===s){s.checking=false;publish(s,failure(error));}return false;}
 }
 useEffect(()=>{
  const s:Session={key,etag:'',baseline:'',view:null,initial:latest.current.value,pending:null,checking:false,incoming:null,recovery:null,paused:false};session.current=s;setState(empty(key));if(id)void read(s,false);
  return()=>{s.controller?.abort();if(session.current===s)session.current=null;};
 },[project,id,variant]);
 async function flush():Promise<boolean>{
  const s=session.current;if(!key)return true;if(!s||s.key!==key||!s.view||readOnly||s.view.status!=='PROPOSED'||s.checking||s.incoming||s.recovery)return false;
  while(s.pending){if(!await s.pending)return false;}
  if(session.current!==s||latest.current.key!==key||s.recovery)return false;
  const snapshot=latest.current.value,baseline=signature(snapshot);if(baseline===s.baseline&&(s.view.active_variant??0)===variant){s.paused=false;publish(s);return true;}
  const pending=api<Data>(base(project)+'/studio-tools/candidates/'+id+'/draft',{etag:s.etag,variant,...snapshot},'PUT').then(view=>{
   s.etag=view.etag;s.baseline=baseline;s.view=view;s.paused=false;
   window.dispatchEvent(new CustomEvent('novel-candidate-draft-saved',{detail:{project,id,path:view.path}}));return true;
  }).catch(error=>{s.paused=true;publish(s,failure(error));return false;}).finally(()=>{s.pending=null;});
  s.pending=pending;publish(s);const ok=await pending;if(ok)publish(s);else if(session.current===s)setState(v=>v.key===key?{...v,saving:false}:v);return session.current===s&&latest.current.key===s.key&&ok&&signature(latest.current.value)===s.baseline;
 }
 function loadStored(){
  const s=session.current;if(!s||s.key!==key||!s.incoming||s.pending||s.checking||s.recovery)return;
  const view=s.incoming,local=latest.current.value,stored=savedValue(view,s.initial);
  // A clean old snapshot is not an unsaved author edit. Handled receipts must
  // still protect genuine local edits, even though the candidate is now locked.
  const unsaved=!latest.current.readOnly&&s.view?.status==='PROPOSED'&&signature(local)!==s.baseline&&signature(local)!==signature(stored);
  const restored=view.status==='PROPOSED'?stored:local;
  s.recovery=unsaved?local:null;
  s.view=view;s.etag=view.etag;s.baseline=signature(restored);s.incoming=null;s.paused=false;
  if(!latest.current.readOnly)latest.current.restore(restored);publish(s);
 }
 function recoverLocal(){
  const s=session.current;if(!s||s.key!==key||!s.recovery||s.pending||s.checking||readOnly||s.view?.status!=='PROPOSED')return;
  const local=s.recovery;s.recovery=null;s.paused=true;latest.current.restore(local);publish(s);
 }
 function keepStored(){
  const s=session.current;if(!s||s.key!==key||!s.recovery||s.pending||s.checking||readOnly||s.view?.status!=='PROPOSED')return;
  s.recovery=null;publish(s);
 }
 function downloadRecovery(){
  const s=session.current;if(!s||s.key!==key||!s.recovery)return;
  saveJSON('candidate-recovery-'+(id||'local')+'.json',{schema_version:1,kind:'UNSAVED_LOCAL_RECOVERY',stored_in_project:false,project_id:project,candidate_id:id,variant,source_revision:s.view?.document_revision,...s.recovery});
 }
 useEffect(()=>{if(!dirty||locked||suspended||current?.recovery||!current?.ready||current.saving||current.checking||current.incoming||current.paused||current.error)return;const timer=setTimeout(()=>void flush(),900);return()=>clearTimeout(timer);},[key,stamp,dirty,locked,suspended,current?.ready,current?.saving,current?.checking,current?.incoming,current?.paused,current?.error]);
 return {ready:!key||!!current?.ready,dirty,readOnly:locked,blocked:!!key&&(!current?.ready||!!current.saving||!!current.checking||!!current.incoming||!!current.recovery),saving:!!current?.saving,checking:!!current?.checking,error:current?.error||'',view:current?.view||null,incoming:current?.incoming||null,stored:current?.incoming?.status==='PROPOSED'?savedValue(current.incoming,session.current?.initial||value):null,local:value,recovery:!!current?.recovery,paused:!!current?.paused,flush,checkStored:()=>{const s=session.current;return s&&s.key===key?read(s,!!s.view):Promise.resolve(false);},loadStored,recoverLocal,keepStored,downloadRecovery,etag:()=>session.current?.key===key?session.current.etag:undefined,download:()=>saveJSON('candidate-draft-'+(id||'local')+'.json',{schema_version:1,project_id:project,candidate_id:id,variant,source_revision:session.current?.view?.document_revision,...latest.current.value})};
}
export function CandidateDraftStatus({draft,readOnly=false,busy=false}:{draft:ReturnType<typeof useCandidateDraft>;readOnly?:boolean;busy?:boolean}){
 useUiTranslation('writing');const locked=readOnly||draft.readOnly,handled=draft.view?.status&&draft.view.status!=='PROPOSED';
 const status=!draft.ready?(draft.error?t('writing:candidateReadFailed'):t('writing:candidateLoading')):handled?t('writing:candidateStatus_'+draft.view?.status)+' · '+t('writing:candidateViewOnly'):locked?t('writing:candidateViewOnly'):draft.saving?t('writing:candidateSaving'):draft.dirty?t('writing:candidateUnsaved'):draft.view?.draft?t('writing:candidateSaved'):t('writing:candidateNotAdopted');
 return <div className="candidate-draft-status"><span role="status">{status}</span>{handled&&<p>{t('writing:candidateHandledHelp')}</p>}{draft.view?.source_current===false&&<p role="alert">{t('writing:candidateStale')}</p>}{draft.error&&<p role="alert">{draft.error}</p>}{draft.paused&&draft.dirty&&!draft.incoming&&<p>{t('writing:candidateManualSave')}</p>}<div className="wa-actions"><button disabled={busy||draft.blocked||locked} onClick={()=>void draft.flush()}>{t('writing:saveCandidateDraft')}</button><button disabled={busy||draft.saving||draft.checking||draft.recovery} onClick={()=>void draft.checkStored()}>{draft.checking?t('writing:candidateChecking'):!draft.ready?t('writing:candidateRetryRead'):t('writing:candidateCheckStored')}</button><button onClick={draft.download}>{t('writing:downloadCandidateDraft')}</button>{draft.recovery&&<button onClick={draft.downloadRecovery}>{t('writing:candidateDownloadRecovery')}</button>}</div>{draft.recovery&&<section className="candidate-recovery" aria-label={t('writing:candidateRecoveryUnsaved')}><p role="status">{t(locked?'writing:candidateRecoveryReadonlyHelp':'writing:candidateRecoveryUnsaved')}</p>{!locked&&<div className="wa-actions"><button disabled={busy||draft.saving||draft.checking||!!draft.incoming} onClick={draft.recoverLocal}>{t('writing:candidateRecoverLocal')}</button><button disabled={busy||draft.saving||draft.checking||!!draft.incoming} onClick={draft.keepStored}>{t('writing:candidateKeepStored')}</button></div>}</section>}{draft.incoming&&<section className="candidate-recovery" aria-label={t('writing:candidateStoredComparison')}><p>{t('writing:candidateIncomingHelp')}</p><div className="candidate-recovery-grid"><label>{t('writing:candidateLocalVersion')}<textarea aria-label={t('writing:candidateLocalVersion')} rows={5} value={draft.local.text} readOnly/><small>{draft.local.note}</small></label><label>{t('writing:candidateStoredVersion')}{draft.stored?<><textarea aria-label={t('writing:candidateStoredVersion')} rows={5} value={draft.stored.text} readOnly/><small>{draft.stored.note}</small></>:<p>{t('writing:candidateStatus_'+draft.incoming.status)} · {t('writing:candidateHandledHelp')}</p>}</label></div><p>{t('writing:candidateRecoveryHelp')}</p><button disabled={busy||draft.checking||draft.saving} onClick={draft.loadStored}>{t('writing:candidateLoadStored')}</button></section>}</div>;
}
