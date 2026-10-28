import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {base,useUnsavedChanges,saveJSON,type Data} from './library-shared';
import {t,useUiTranslation} from './i18n';

type Value={text:string;note:string;chosen_hunks:number[]|null};
type Options={project:string;id:string|null;variant?:number;text:string;note?:string;chosenHunks?:number[]|null;readOnly?:boolean;onRestore:(value:Value)=>void};
const signature=(v:Value)=>JSON.stringify(v);
export function useCandidateDraft(options:Options){
 const {project,id,variant=0,text,note='',chosenHunks=null,readOnly=false}=options;
 const key=id?project+':'+id+':'+variant:'';
 const value:Value={text,note,chosen_hunks:chosenHunks};
 const latest=useRef({key,value,restore:options.onRestore});latest.current={key,value,restore:options.onRestore};
 const session=useRef<{key:string;etag:string;baseline:string;view:Data;pending:Promise<boolean>|null}|null>(null);
 const [state,setState]=useState<{key:string;ready:boolean;saving:boolean;error:string;view:Data|null;baseline:string}>({key:'',ready:false,saving:false,error:'',view:null,baseline:''});
 const current=state.key===key?state:null,stamp=signature(value);
 const dirty=!!key&&!!current?.ready&&stamp!==current.baseline;
 useUnsavedChanges(dirty,t('writing:candidateUnsaved'));
 useEffect(()=>{
  let active=true;session.current=null;setState({key,ready:false,saving:false,error:'',view:null,baseline:''});if(!id)return;
  void api<Data>(base(project)+'/studio-tools/candidates/'+id+'/draft?variant='+variant).then(view=>{
   if(!active||latest.current.key!==key)return;
   const draft=view.status==='PROPOSED'?view.draft:null;
   const restored:Value=draft?{text:draft.text,note:draft.note||'',chosen_hunks:draft.chosen_hunks??null}:latest.current.value;
   const baseline=signature(restored);session.current={key,etag:view.etag,baseline,view,pending:null};
   if(draft)latest.current.restore(restored);
   setState({key,ready:true,saving:false,error:'',view,baseline});
  }).catch(error=>{if(active)setState({key,ready:false,saving:false,error:String(error.message||error),view:null,baseline:''});});
  return()=>{active=false;};
 },[project,id,variant]);
 async function flush():Promise<boolean>{
  const s=session.current;if(!s||s.key!==key||readOnly||s.view.status!=='PROPOSED')return !dirty;
  while(s.pending){if(!await s.pending)return false;}
  if(session.current!==s||latest.current.key!==key)return false;
  const snapshot=latest.current.value,baseline=signature(snapshot);
  if(baseline===s.baseline)return true;
  setState(v=>v.key===key?{...v,saving:true,error:''}:v);
  const pending=api<Data>(base(project)+'/studio-tools/candidates/'+id+'/draft',{etag:s.etag,variant,...snapshot},'PUT').then(view=>{
   s.etag=view.etag;s.baseline=baseline;s.view=view;
   if(session.current===s)setState({key,ready:true,saving:false,error:'',view,baseline});
   window.dispatchEvent(new CustomEvent('novel-candidate-draft-saved',{detail:{project,id,path:view.path}}));return true;
  }).catch(error=>{if(session.current===s)setState(v=>({...v,saving:false,error:String(error.technicalDetail||error.message||error)}));return false;}).finally(()=>{s.pending=null;});
  s.pending=pending;const ok=await pending;return ok&&signature(latest.current.value)===s.baseline;
 }
 useEffect(()=>{if(!dirty||readOnly||!current?.ready||current.saving||current.error)return;const timer=setTimeout(()=>void flush(),900);return()=>clearTimeout(timer);},[key,stamp,dirty,readOnly,current?.ready,current?.saving,current?.error]);
 return {ready:!key||!!current?.ready,dirty,saving:!!current?.saving,error:current?.error||'',view:current?.view||null,flush,etag:()=>session.current?.key===key?session.current.etag:undefined,download:()=>saveJSON('candidate-draft-'+(id||'local')+'.json',{schema_version:1,project_id:project,candidate_id:id,variant,source_revision:session.current?.view.document_revision,...latest.current.value})};
}
export function CandidateDraftStatus({draft,readOnly=false}:{draft:ReturnType<typeof useCandidateDraft>;readOnly?:boolean}){
 useUiTranslation('writing');return <div className="candidate-draft-status"><span role="status">{!draft.ready?t('writing:candidateLoading'):draft.saving?t('writing:candidateSaving'):draft.dirty?t('writing:candidateUnsaved'):draft.view?.draft?t('writing:candidateSaved'):t('writing:candidateNotAdopted')}</span>{draft.view?.source_current===false&&<p role="alert">{t('writing:candidateStale')}</p>}{draft.error&&<p role="alert">{draft.error}</p>}<button disabled={!draft.ready||draft.saving||readOnly} onClick={()=>void draft.flush()}>{t('writing:saveCandidateDraft')}</button><button onClick={draft.download}>{t('writing:downloadCandidateDraft')}</button></div>;
}
