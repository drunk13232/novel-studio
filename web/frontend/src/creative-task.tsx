import {useEffect,useRef,useState} from 'react';
import {api,type Task,terminal} from './api';
import {t,useUiTranslation} from './i18n';
export function useCreativeTask(project:string,task:Task|null,onDone:(task:Task)=>void,onProgress?:()=>void,onEvent?:(event:Record<string,any>)=>void){
 const [stage,setStage]=useState(''),callbacks=useRef({onDone,onProgress,onEvent});callbacks.current={onDone,onProgress,onEvent};
 useEffect(()=>{
  if(!task||terminal(task.status))return;
  let alive=true,completed=false,polling=false,errors=0,timer:ReturnType<typeof setTimeout>|undefined;
  const controller=new AbortController(),prefix='/api/projects/'+project+'/tasks/'+task.id,stream=new EventSource(prefix+'/events');
  setStage('');
  async function finish(){
   if(!alive||completed||polling)return;polling=true;
   try{
    const value=await api<Task>(prefix,undefined,'GET',{signal:controller.signal});if(!alive||completed)return;errors=0;
    if(terminal(value.status)){completed=true;stream.close();if(timer)clearTimeout(timer);callbacks.current.onDone(value);}
    else timer=setTimeout(finish,3000);
   }catch{
    if(alive&&!completed){errors++;setStage(t('plans:connectionPaused'));if(errors<6)timer=setTimeout(finish,Math.min(15000,1500*2**errors));}
   }finally{polling=false;}
  }
  stream.onmessage=e=>{
   if(!alive||completed)return;let event;
   try{event=JSON.parse(e.data);}catch{stream.close();void finish();return;}
   callbacks.current.onEvent?.(event);
   if(['status','warning','error'].includes(event.type))setStage(event.message);
   if(event.type==='roleplay_reply')callbacks.current.onProgress?.();
   if(['task_completed','task_cancelled','task_interrupted'].includes(event.type)){stream.close();void finish();}
  };
  stream.onerror=()=>{if(alive){stream.close();void finish();}};
  const reconnect=(e:Event)=>{if(e.type==='online'||(e as CustomEvent).detail===task.id){if(timer)clearTimeout(timer);errors=0;void finish();}};
  window.addEventListener('online',reconnect);window.addEventListener('creative-task-reconnect',reconnect);
  return()=>{alive=false;controller.abort();stream.close();if(timer)clearTimeout(timer);window.removeEventListener('online',reconnect);window.removeEventListener('creative-task-reconnect',reconnect);};
 },[task?.id,project]);
 return stage;
}
export function modelLabel(meta:Record<string,any>|null|undefined){return meta?`${meta.provider_name||meta.provider_id||'Codex'} / ${meta.observed_model||meta.model||'UNKNOWN'}`:'UNKNOWN';}

export function TaskReceipt({task}:{task:Record<string,any>}){
 useUiTranslation('plans');const meta=task.ai_metadata||{},tr=(key:string)=>t('plans:'+key),parameters=meta.effective_parameters||{},observed=meta.observed_model||meta.request_model,context=meta.context||meta.context_receipt;
 return <details className="task-receipt"><summary>{tr('receipt')}</summary><dl><dt>{tr('requestedModel')}</dt><dd>{meta.model||tr('unknown')}</dd><dt>{tr('observedModel')}</dt><dd>{observed||tr('unknown')}</dd><dt>{tr('backend')}</dt><dd>{meta.backend||task.provider||tr('unknown')}</dd><dt>{tr('executionState')}</dt><dd>{task.status||tr('unknown')}</dd><dt>{tr('effort')}</dt><dd>{parameters.reasoning_effort||parameters.reasoning?.effort||meta.reasoning_effort||tr('unknown')}</dd></dl><p>{tr('receiptBoundary')}</p>{Object.keys(parameters).length>0&&<pre className="bounded-log">{JSON.stringify(parameters,null,2)}</pre>}{context&&<pre className="bounded-log">{JSON.stringify(context,null,2)}</pre>}{meta.usage&&<pre className="bounded-log">{JSON.stringify(meta.usage,null,2)}</pre>}{!terminal(task.status)&&<button onClick={()=>window.dispatchEvent(new CustomEvent('creative-task-reconnect',{detail:task.id}))}>{tr('refreshTask')}</button>}</details>;
}
