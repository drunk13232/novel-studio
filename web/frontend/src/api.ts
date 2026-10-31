import {t} from './i18n';
import {writingMetricsMutation,WRITING_METRICS_CHANGED} from './writing-metrics-events';
import {flushAIControlWrites} from './ai-control-writes';
export interface FileRow {path:string;name:string;size:number;modified_at:string;editable:boolean}
export interface Content extends FileRow {content:string;etag:string;line_ending:string;bom:boolean}
export interface Chapter {number:number;title:string|null;files:FileRow[];plan:string|null;draft:string|null;final:string|null;review:string|null;state_diff:string|null;availability?:Record<string,{enabled:boolean;reason:string|null}>}
export interface Task {provider?:string|null;skill?:string|null;result?:Record<string,unknown>|null;id:string;type:string;scope:string;chapter:number|null;status:string;created_at:string;started_at:string|null;finished_at:string|null;codex_thread_id:string|null;turn_id:string|null;error:string|null;files_changed:{path:string;change:string}[]}
export interface Event {id:number;type:string;timestamp:string;message:string;data:Record<string,unknown>}
export interface Health {backend:boolean;codex:boolean;checking:boolean;reason:string|null;version?:string;sdk_version?:string;authentication?:string;workspace:string;project_skills?:string[];plugin_skills?:string[]}
export interface Status {title:string|null;genre:string|null;volume:number|null;chapter:number|null;pov:string|null;location:string|null;story_time:string|null;open_foreshadowing:number;active_threads:number;pending_diffs:string[];recent_files:FileRow[];recent_chapters:Chapter[];recent_tasks:Task[];warnings:string[]}
let token='';
let mutations:Promise<unknown>=Promise.resolve();
/** beforeSend is synchronous and runs at actual dispatch, including queued/auth/preflight retries. */
export type LocalRequestOptions={signal?:AbortSignal;beforeSend?:()=>void;recoveryRevision?:string};
export type LocalReadOptions=LocalRequestOptions;
/** Ephemeral local operation proof. Never persist it or include it in model prompts. */
export type FrontendOrigin={session_id:string;token:string};
/** These authenticated local requests never edit manuscript or authoritative story data. */
const independentLocalOperation=(url:string,method:string)=>method==='POST'&&(url==='/api/studio/codex/check'||/^\/api\/projects\/[^/?#]+\/(?:workbench\/replace\/search|experience\/focus-summary|book\/print-preview(?:\/[0-9a-f]{32}\/cancel)?|audio-export\/audio_[0-9a-f]{32}\/cancel)$/.test(url));
async function request<T>(url:string,body:unknown,method:string,signal?:AbortSignal,beforeSend?:()=>void,recoveryRevision?:string):Promise<T>{
  if(signal?.aborted)throw new DOMException('Request cancelled','AbortError');
  const mutation=method!=='GET';
  for(let attempt=0;attempt<2;attempt++){
    if(mutation&&!token)token=(await request<{request_token:string}>('/api/session',undefined,'GET')).request_token;
    const binary=body instanceof Blob,form=body instanceof FormData;
    const headers:Record<string,string>=mutation?{'X-Novel-Request':token}:{};
    if(body!==undefined&&!form)headers['Content-Type']=binary?'application/octet-stream':'application/json';
    if(recoveryRevision!==undefined)headers['If-Match']='"'+recoveryRevision+'"';
    let response:Response;
    beforeSend?.(); // Outside the transport catch: preserve local validation errors.
    try{if(signal?.aborted)throw new DOMException('Request cancelled','AbortError');response=await fetch(url,{method,headers,signal,body:body===undefined?undefined:form||binary?body as BodyInit:JSON.stringify(body)});}catch(error){if(signal?.aborted||(error instanceof Error&&error.name==='AbortError'))throw new DOMException('Request cancelled','AbortError');throw Object.assign(new Error(t('errors:LOCAL_SERVICE_UNAVAILABLE')),{code:'LOCAL_SERVICE_UNAVAILABLE'});}
    let value:any;
    try{value=await response.json();}catch{if(signal?.aborted)throw new DOMException('Request cancelled','AbortError');throw Object.assign(new Error(t('errors:LOCAL_RESPONSE_INVALID')),{code:'LOCAL_SERVICE_RESPONSE_INVALID'});}
    if(!response.ok){
      if(response.status===409&&value.ai_notice){
        beforeSend?.();
        const n=value.ai_notice;
        if(!window.confirm(t('ai:remoteSendConfirmation',{provider:n.provider,model:n.model,host:n.host,categories:n.categories})+'\n'+(n.budget||[]).join('\n')))throw new Error(t('errors:REMOTE_SEND_CANCELLED'));
        await request('/api/ai/confirm',{token:n.token},'POST');
        return request<T>(url,body,method,signal,beforeSend,recoveryRevision); // Preflight only: no upstream request has started.
      }
      if(response.status===403&&(value.code==='SESSION_INVALID'||value.detail==='缺少本机会话请求校验')&&attempt===0){token='';continue;}
      const technical=typeof value.detail==='string'?value.detail:JSON.stringify(value.detail);
      const code=typeof value.code==='string'?value.code:response.status===422?'INVALID_REQUEST':response.status===503?'SERVICE_UNAVAILABLE':'REQUEST_REJECTED';
      const aiControlError=/^\/api\/(?:ai\/|assistant\/|plugins(?:\/|$)|drafts\/[^/]+\/creation|projects\/[^/]+\/(?:world-studio|creative))/.test(url)&&typeof value.detail==='string';
      const fallback=t('errors:'+code,{defaultValue:t('errors:REQUEST_REJECTED'),...(value.params||{})});
      const localNamespace=/^\/api\/projects\/[^/]+\/workbench\/replace(?:\/|$)/.test(url)?'replace:errors.':/^\/api\/projects\/[^/]+\/workbench\/clue-board(?:\/|$)/.test(url)?'clues:errors.':null;
      const message=localNamespace?t(localNamespace+code,{defaultValue:fallback,...(value.params||{})}):aiControlError?value.detail:fallback;
      if(mutation&&!url.includes('/studio/recovery'))window.dispatchEvent(new CustomEvent('studio-feedback',{detail:{error:true,message,diagnostic:technical}}));
      throw Object.assign(new Error(message),{code,httpStatus:response.status,technicalDetail:technical});
    }
    if(mutation){const success=url.endsWith('/data/backup')?t('common:backupSuccess'):url.endsWith('/book/export')?t('common:bookExportSuccess'):url.endsWith('/profiles')?t('common:styleProfileSaved'):method==='PATCH'&&url.includes('/documents/')?t('common:referenceMetadataSaved'):null;if(success)window.dispatchEvent(new CustomEvent('studio-feedback',{detail:{message:success}}));}
    const writingChange=mutation?writingMetricsMutation(url,body,method,value):null;
    if(writingChange)window.dispatchEvent(new CustomEvent(WRITING_METRICS_CHANGED,{detail:writingChange}));
    return value as T;
  }
  throw new Error(t('errors:SESSION_INVALID'));
}
export function api<T>(url:string,body?:unknown,method='GET',options:LocalRequestOptions={}):Promise<T>{
  const independent=method==='GET'||independentLocalOperation(url,method);
  const conditionalCleanup=method==='DELETE'&&/^\/api\/projects\/[^/?#]+\/studio\/recovery\?[^#]+$/.test(url)&&typeof options.recoveryRevision==='string'&&/^(?:[0-9a-f]{64}|missing)$/.test(options.recoveryRevision)&&new URLSearchParams(url.split('?')[1]).getAll('path').length===1&&!!new URLSearchParams(url.split('?')[1]).get('path');
  if(options.recoveryRevision!==undefined&&!conditionalCleanup)return Promise.reject(Object.assign(new Error(t('errors:REQUEST_REJECTED')),{code:'CANCELLATION_NOT_SUPPORTED'}));
  // Cancel a preview/read, never mislabel an already-submitted save or paid task as cancelled.
  if(options.signal&&!independent&&!conditionalCleanup)return Promise.reject(Object.assign(new Error(t('errors:REQUEST_REJECTED')),{code:'CANCELLATION_NOT_SUPPORTED'}));
  if(independent||url.endsWith('/cancel'))return request<T>(url,body,method,options.signal,options.beforeSend);
  // Preserve the existing backend mutation boundary, including preference saves.
  // Never retry etag conflicts or serialize GETs; tasks retain their own manager.
  const enqueue=()=>{
    const result=mutations.catch(()=>{}).then(()=>request<T>(url,body,method,conditionalCleanup?options.signal:undefined,options.beforeSend,conditionalCleanup?options.recoveryRevision:undefined));
    mutations=result.then(()=>undefined,()=>undefined);
    // A queued cleanup can stop waiting, but never release or cancel an older write.
    if(!conditionalCleanup||!options.signal)return result;
    const signal=options.signal;
    return new Promise<T>((resolve,reject)=>{
      const aborted=()=>reject(new DOMException('Recovery cleanup wait cancelled','AbortError'));
      signal.addEventListener('abort',aborted,{once:true});
      result.then(value=>{signal.removeEventListener('abort',aborted);resolve(value);},error=>{signal.removeEventListener('abort',aborted);reject(error);});
      if(signal.aborted)aborted();
    });
  };
  // Flush before joining the mutation queue: a queued request must not wait
  // for preference writes enqueued behind itself. Current generation stays frozen.
  if(method==='POST'&&/(?:\/tasks|\/sessions|\/reply|\/run|\/start|\/selection|\/control|\/creation\/context|\/assistant\/context)$/.test(url))return flushAIControlWrites().then(enqueue);
  return enqueue();
}
export const labels:Record<string,string>={get research_topic(){return t("ai:taskResearchTopic");},get pov_review(){return t("ai:taskPovReview");},get voice_preserving_revision(){return t("ai:taskVoicePreservingRevision");},get story_continuity_check(){return t("ai:taskStoryContinuityCheck");},get story_knowledge_check(){return t("ai:taskStoryKnowledgeCheck");},get story_timeline_check(){return t("ai:taskStoryTimelineCheck");},get story_voice_check(){return t("ai:taskStoryVoiceCheck");},get story_context_build(){return t("ai:taskStoryContextBuild");},get story_links_check(){return t("ai:taskStoryLinksCheck");},get story_doctor(){return t("ai:taskStoryDoctor");},get story_names_check(){return t("ai:taskStoryNamesCheck");},get story_architect(){return t("ai:taskStoryArchitect");},get story_architect_refine(){return t("ai:taskStoryArchitectRefine");},get world_expand(){return t("ai:taskWorldExpand");},get character_consistency_check(){return t("ai:taskCharacterConsistencyCheck");},get character_difference_check(){return t("ai:taskCharacterDifferenceCheck");},get character_create(){return t("ai:taskCharacterCreate");},get character_refine(){return t("ai:taskCharacterRefine");},get master_outline_generate(){return t("ai:taskMasterOutlineGenerate");},get volume_outline_generate(){return t("ai:taskVolumeOutlineGenerate");},get volume_outline_refine(){return t("ai:taskVolumeOutlineRefine");},get chapter_skeleton_generate(){return t("ai:taskChapterSkeletonGenerate");},get chapter_cards_deepen(){return t("ai:taskChapterCardsDeepen");},get chapter_plan_refine(){return t("ai:taskChapterPlanRefine");},get chapter_plan_review(){return t("ai:taskChapterPlanReview");},get chapter_plan(){return t("ai:taskChapterPlan");},get chapter_write(){return t("ai:taskChapterWrite");},get chapter_review(){return t("ai:taskChapterReview");},get chapter_revise(){return t("ai:taskChapterRevise");},get context_build(){return t("ai:taskContextBuild");},get continuity_check(){return t("ai:taskContinuityCheck");},get character_check(){return t("ai:taskCharacterCheck");},get contract_check(){return t("ai:taskContractCheck");},get sepia_review(){return t("ai:taskSepiaReview");},get sepia_refactor(){return t("ai:taskSepiaRefactor");},get story_structure_review(){return t("ai:taskStoryStructureReview");},get scene_review(){return t("ai:taskSceneReview");},get dialogue_review(){return t("ai:taskDialogueReview");},get pacing_review(){return t("ai:taskPacingReview");},get memory_extract(){return t("ai:taskMemoryExtract");},get state_validate(){return t("ai:taskStateValidate");},state_commit:'State Commit',get custom_prompt(){return t("ai:taskCustomPrompt");},get chapter_pipeline(){return t("ai:taskChapterPipeline");},final_check:'Final Check'};
export const terminal=(s:string)=>['SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'].includes(s);
