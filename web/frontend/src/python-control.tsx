import type {FrontendOrigin} from './api';
import {useEffect,useRef,useState} from 'react';
import {api,terminal} from './api';
import {DIRECTOR_PYTHON_SAMPLE,type DirectorHandoff} from './director-console';
import AIControls,{AIRequestReceipt} from './ai-controls';
import {t,useUiTranslation} from './i18n';
import './python-control.css';
type D=Record<string,any>;
const tr=(key:string)=>t('control:'+key);
function historyStatus(row:D){
 if(row.status!=='WAITING_CONFIRMATION')return row.status;
 return tr('pausedAtConfirmation')+' · '+tr('approvalStatus')+': '+tr('approval_'+(row.confirmation_status||'UNKNOWN'));
}
const samples={
 browse:'from novel_studio_api import Studio\n\nstudio = Studio.connect()\nprint(studio.projects.current())\nprint(studio.chapters.list())\nstudio.ui.open_chapter(2)\nstudio.ui.open_reference("chapter", number=1)\nprint(studio.characters.search())\n',
 notes:'from novel_studio_api import Studio\n\nstudio = Studio.connect()\n# 需要允许读取当前作品资料；不删除原始灵感。\nnotes = studio.notes.list()["entries"]\nids = [note["id"] for note in notes if note.get("status") == "OPEN"]\nif ids:\n    print(studio.call("inspirations_to_todos", ids=ids[:10], chapter=2))\n',
 ai:'from novel_studio_api import Studio, StudioError\n\nstudio = Studio.connect()\nprint(studio.ai.models())\ntry:\n    task = studio.ai.start("只读检查已明确选定的范围；引用原文，不编造事实。", chapters=[1, 2])\n    print(task)\n    print(studio.tasks.wait(task["id"], timeout=60))\nexcept StudioError as error:\n    print(error.result)  # 等待作者确认时停止，不自动重复付费调用。\n',
 inspect:'from novel_studio_api import Studio\n\nstudio = Studio.connect()\nprint(studio.ui.state())\nprint(studio.world.search())\nprint(studio.call("get_codex_status"))\n',
};
export default function PythonControl({directorHandoff,onReturnDirector,initialSession,open,onClose,project,persona,onPersona,getContext,onAction,onChanged,onActivity}:{directorHandoff?:DirectorHandoff|null;onReturnDirector?:(v:DirectorHandoff)=>void;initialSession?:D|null;open:boolean;onClose:()=>void;project:string;persona:string;onPersona:(v:string)=>void;getContext:()=>D;onAction:(name:string,args:D,signal?:AbortSignal,owner?:FrontendOrigin)=>Promise<D>;onChanged:()=>void;onActivity:(v:D)=>void}){
 useUiTranslation(['control','assistant','writing']);
 const [code,C]=useState(samples.browse),[name,N]=useState(''),[scripts,S]=useState<D[]>([]),[history,H]=useState<D[]>([]),[session,V]=useState<D|null>(null),[error,E]=useState(''),[busy,B]=useState(false),[cfg,F]=useState<D|null>(null),[help,Q]=useState<D[]>([]),[filter,FL]=useState(''),[grant,G]=useState<D|null>(null),[tab,T]=useState('script');
 const [savedId,SI]=useState(''),[chosen,CH]=useState<D|null>(null),[settings,SET]=useState(false);
 const [boundDirector,BD]=useState<DirectorHandoff|null>(null);
 const [analysisComment,AC]=useState('');
 const analysisSource=chosen?.director_source||(!chosen?session?.python_director_source:null),analysisRunId=chosen?.id||session?.python_run_id;

 const [aiTask,AT]=useState<D|null>(null),[aiOutput,AO]=useState('');
 useEffect(()=>{AT(null);AO('');BD(null);AC('');},[project,persona]);
 const child=[...(session?.steps||[])].reverse().find((v:D)=>v.tool==='start_text_task'&&v.status==='已完成'&&v.result?.id)?.result;
 useEffect(()=>{if(child?.id){AT({...child,project});AO('');}},[child?.id]);
 useEffect(()=>{
  if(!open||!aiTask?.id||terminal(aiTask.status))return;
  const id=aiTask.id,p=aiTask.project;let live=true;
  const read=()=>void api<D>('/api/projects/'+p+'/tasks/'+id).then(v=>{if(live)AT({...v,project:p});}).catch(e=>{if(live)E(String(e));});read();
  const source=new EventSource('/api/projects/'+p+'/tasks/'+id+'/events');
  source.onmessage=event=>{const v=JSON.parse(event.data);if(!live)return;
   AO(text=>(text+(v.message||'')+(v.type==='message'||v.type==='llm_delta'?'':'\n')).slice(-16000));
   if(['task_completed','task_cancelled'].includes(v.type)){source.close();read();}
  };
  source.onerror=()=>{source.close();if(live){read();E(tr('taskStreamClosed'));}};
  return()=>{live=false;source.close();};
 },[open,aiTask?.id,terminal(aiTask?.status)]);
 const controls=useRef<D|null>(null),sent=useRef(new Set<string>()),latest=useRef({getContext,onAction,onChanged,project,onActivity});latest.current={getContext,onAction,onChanged,project,onActivity};
 const revisionExecutions=useRef(new Map<string,{session:string;controller:AbortController}>());
 const buffers=useRef(new Map<string,D>()),scope=project+':'+persona,scopeRef=useRef(scope);scopeRef.current=scope;
 const current=useRef(session);current.current=session;
 const active=!!session&&(!!session.pending||!!session.task&&!terminal(session.task.status));
 async function refresh(){if(!project)return;const p=encodeURIComponent(project),who=encodeURIComponent(persona);const [a,b,c]=await Promise.all([api<D>('/api/control/scripts?project='+p+'&persona='+who),api<D>('/api/control/history?project='+p+'&persona='+who),api<D>('/api/assistant/settings?project='+p+'&persona='+who)]);if(scopeRef.current!==scope)return;S(a.scripts);H(b.runs);F(c);}
 useEffect(()=>{const previous=buffers.current.get(scope);C(previous?.code||samples.browse);N(previous?.name||'');SI(previous?.id||'');V(null);CH(null);G(null);E('');controls.current=null;void refresh().catch(e=>E(String(e)));},[scope]);
 useEffect(()=>{buffers.current.set(scope,{code,name,id:savedId});},[code,name,savedId]);
 useEffect(()=>{if(initialSession?.id&&initialSession.project===project&&initialSession.persona===persona){V(initialSession);C(initialSession.code||'');N(initialSession.title||'');SI('');CH(null);E('');}},[initialSession?.id,project,persona]);
 useEffect(()=>{let alive=true;void api<D>('/api/assistant/tools').then(v=>{if(alive)Q(v.tools);}).catch(e=>E(String(e)));return()=>{alive=false;};},[]);
 // One on-demand connection while the control UI has been initialized. Hidden
 // controls keep allowed read-only work alive; closing never starts new tasks.
 useEffect(()=>{if(!project)return;const source=new EventSource('/api/control/events?project='+encodeURIComponent(project));let disposed=false;
  source.onmessage=event=>{const rows: D[]=JSON.parse(event.data).sessions;for(const s of rows){
   if(s.persona!==persona||s.project!==project)continue;
   if(s.execution_status==='CANCELLED'||terminal(s.task?.status)&&!s.pending)for(const item of revisionExecutions.current.values())if(item.session===s.id)item.controller.abort('caller-ended');
   if(s.persona===persona&&(!current.current||current.current.id===s.id||terminal(current.current.task?.status)&&!current.current.pending))V(s);
   const p=s.pending;if(p?.kind!=='frontend'||sent.current.has(p.token))continue;sent.current.add(p.token);
   void (async()=>{const controller=p.tool==='propose_chapter_revision'?new AbortController():null;if(controller)revisionExecutions.current.set(p.token,{session:s.id,controller});const timeout=controller?setTimeout(()=>controller.abort('timeout'),20000):null;let result:D;
    try{const context=latest.current.getContext();await api('/api/assistant/sessions/'+s.id+'/frontend-claim',{token:p.token,context},'POST',{beforeSend:()=>{if(disposed||controller?.signal.aborted)throw new DOMException('Preparation aborted','AbortError');}});if(disposed||context.project!==p.project||latest.current.project!==p.project)throw new Error(tr('scopeChanged'));if(controller?.signal.aborted)throw new DOMException('Preparation aborted','AbortError');result=await latest.current.onAction(p.tool,{...p.arguments,project:p.project},controller?.signal,{session_id:s.id,token:p.token});if(!disposed)latest.current.onChanged();}
    catch(e){result={ok:false,error:controller?.signal.aborted?t(controller.signal.reason==='timeout'?'writing:selectionPreparationTimedOut':'writing:selectionPreparationCancelled'):String(e)};}
    finally{if(timeout)clearTimeout(timeout);revisionExecutions.current.delete(p.token);}
    if(!disposed&&(!controller?.signal.aborted||controller.signal.reason==='timeout'))await api('/api/assistant/sessions/'+s.id+'/reply',{token:p.token,approved:result.ok===true,result,context:latest.current.getContext()},'POST');})().catch(e=>{if(!disposed)E(String(e));});
  }};source.onerror=()=>{if(open)E(tr('bridgeReconnect'));};return()=>{disposed=true;for(const item of revisionExecutions.current.values())item.controller.abort('scope');revisionExecutions.current.clear();source.close();};
 },[project,persona]);
 useEffect(()=>{if(!session?.id||!active)return;let alive=true,running=false;const poll=async()=>{if(running)return;running=true;try{const s=await api<D>('/api/assistant/sessions/'+session.id);if(alive){V(s);if(terminal(s.task?.status)&&!s.pending)void refresh();}}catch(e){if(alive)E(String(e));}finally{running=false;}};void poll();const timer=setInterval(poll,650);return()=>{alive=false;clearInterval(timer);};},[session?.id,active]);
 useEffect(()=>{if(!active&&(!open||!aiTask||terminal(aiTask.status))){onActivity({active:false,state:'idle'});return;}const pending=session?.pending;const tool=[...(session?.steps||[])].reverse().find((v:D)=>v.status==='正在执行')?.tool||'';const state=pending?.kind==='confirm'?'confirm':!active&&aiTask&&!terminal(aiTask.status)?'analyzing':/search|read|list|get_/.test(tool)?'searching':'executing';onActivity({active:true,state,output:session?.output||'',persona});},[active,open,aiTask?.status,session?.pending?.kind,session?.steps?.length,session?.output]);
 async function run(){if(active||!project)return;B(true);E('');CH(null);try{const key=scope;const row=await api<D>('/api/control/run',{persona,instruction:name||'作者运行 Python 操作计划',context:getContext(),code,title:name||'Python Control',model:controls.current?.model||cfg?.model||'codex-software',ai_controls:controls.current,previous_session:session?.id,...(boundDirector&&boundDirector.project===project?{director_handoff:{id:boundDirector.id,etag:boundDirector.etag}}:{}),timeout:120},'POST');if(scopeRef.current===key)V(row);}catch(e){E(String(e));}finally{B(false);}}
 function loadDirector(){
  if(!directorHandoff||directorHandoff.project!==project||active)return;
  if(code.trim()&&code!==samples.browse&&code!==DIRECTOR_PYTHON_SAMPLE&&!window.confirm(tr('replaceScript')))return;
  C(DIRECTOR_PYTHON_SAMPLE);N(directorHandoff.title);SI('');CH(null);BD(directorHandoff);T('script');E('');
 }
 async function saveAnalysis(){
  if(active||!analysisSource?.record_id||!analysisRunId)return;B(true);E('');const owner=scope;
  try{const record=await api<D>('/api/projects/'+project+'/creative-director/'+analysisSource.record_id);const value=await api<D>('/api/control/director-note',{project,persona:chosen?.persona||session?.persona||persona,record_id:record.id,run_id:analysisRunId,etag:record.etag,comment:analysisComment},'POST');if(scopeRef.current!==owner)return;AC('');E(tr('analysisSaved'));onReturnDirector?.({project,path:value.path,id:value.id,etag:value.etag,title:value.goal,request:Date.now()});}catch(e){if(scopeRef.current===owner)E(String((e as {technicalDetail?:string})?.technicalDetail||e));}finally{B(false);}
 }
 async function reply(approved:boolean){if(!session?.pending)return;B(true);try{await api('/api/assistant/sessions/'+session.id+'/reply',{token:session.pending.token,approved,context:getContext()},'POST');V(await api<D>('/api/assistant/sessions/'+session.id));}catch(e){E(String(e));}finally{B(false);}}
 async function stop(){if(!session)return;for(const item of revisionExecutions.current.values())if(item.session===session.id)item.controller.abort('user');try{V(await api<D>('/api/assistant/sessions/'+session.id+'/cancel',{},'POST'));}catch(e){E(String(e));}}
 async function save(){try{const row=await api<D>('/api/control/scripts',{project,persona,id:savedId,name:name.trim()||'Python script',code},'POST');SI(row.id);N(row.name);await refresh();E(tr('saved'));}catch(e){E(String(e));}}
 async function makeGrant(){B(true);try{const row=await api<D>('/api/control/grants',{persona,instruction:'作者主动创建当前作品的外部 Python 临时授权',context:getContext(),model:controls.current?.model||cfg?.model||'codex-software',previous_session:session?.id},'POST');const nonce=await api<D>('/api/session');G({...row,nonce:nonce.request_token});}catch(e){E(String(e));}finally{B(false);}}
 const pending=session?.pending,output=chosen?(chosen.output??''):(session?.output??''),completed=(session?.steps||[]).find((v:D)=>v.tool==='start_text_task'&&v.status==='已完成'&&v.result?.id);
 const matches=help.filter(v=>(v.name+' '+v.description).toLowerCase().includes(filter.trim().toLowerCase()));
 if(!open)return pending?.kind==='confirm'?<button className="control-pending" onClick={()=>void onAction('show_python_control',{})}>{tr('waiting')}</button>:null;
 return <aside className="python-control" aria-label={tr('title')}>
  <header><div><small>PYTHON · ACTIONS · CODEX</small><h2>{tr('title')}</h2></div><button aria-label={tr('close')} onClick={onClose}>×</button></header>
  <p className="muted">{tr('boundary')}</p>
  <div className="control-bar"><label>{tr('persona')}<select aria-label={tr('persona')} value={persona} disabled={active} onChange={e=>onPersona(e.target.value)}><option value="yoshino">朝武芳乃</option><option value="rem">蕾姆</option><option value="assistant">Novel Studio</option></select></label><span>{tr('project')} · {project.slice(0,14)}…</span><button onClick={()=>SET(!settings)}>{tr('permissions')}</button></div>
  {settings&&cfg&&<section className="control-settings"><label>{tr('mode')}<select aria-label={tr('mode')} value={cfg.mode} onChange={e=>F({...cfg,mode:e.target.value})}><option value="suggest">{tr('suggest')}</option><option value="navigate">{tr('navigate')}</option><option value="draft">{tr('draft')}</option></select></label>{[['manuscript','readManuscript'],['setting_context','readSettings'],['references','readReferences'],['selection','readSelection']].map(([key,label])=><label className="check" key={key}><input type="checkbox" checked={!!cfg[key]} onChange={e=>F({...cfg,[key]:e.target.checked})}/>{tr(label)}</label>)}<button onClick={()=>void api('/api/assistant/settings?persona='+persona+'&project='+encodeURIComponent(project),cfg,'PUT').then(()=>{E(tr('saved'));window.dispatchEvent(new Event('assistant-settings-changed'));}).catch(e=>E(String(e)))}>{tr('savePermissions')}</button></section>}
  <AIControls key={scope} project={project} task="assistant" session={'python-'+persona} model={cfg?.model==='codex-software'?'codex':cfg?.model||'codex'} onChange={v=>{controls.current=v;}} busy={active}/>
  {directorHandoff?.project===project&&<section className="control-director-handoff"><small>{tr('directorSource')}</small><strong>{directorHandoff.title}</strong><p>{tr('directorBoundary')}</p><div className="control-bar"><button disabled={active||busy} onClick={loadDirector}>{tr('loadDirector')}</button><button disabled={active||busy} onClick={()=>onReturnDirector?.(directorHandoff)}>{tr('returnDirector')}</button></div>{boundDirector&&<><small role="status">{tr('directorBound')} · {boundDirector.etag.slice(0,12)}</small><button disabled={active||busy} onClick={()=>BD(null)}>{tr('unlinkDirector')}</button></>}</section>}
  <div className="control-tabs" role="tablist">{['script','history','actions','external'].map(value=><button key={value} role="tab" aria-selected={tab===value} onClick={()=>T(value)}>{tr(value)}</button>)}</div>
  {tab==='script'&&<><div className="control-bar"><select aria-label={tr('examples')} defaultValue="" disabled={active} onChange={e=>{if(e.target.value){BD(null);C(samples[e.target.value as keyof typeof samples]);SI('');CH(null);}}}><option value="">{tr('examples')}</option>{Object.keys(samples).map(v=><option value={v} key={v}>{tr('sample_'+v)}</option>)}</select><select aria-label={tr('savedScripts')} value={savedId} disabled={active} onChange={e=>{const row=scripts.find(v=>v.id===e.target.value);if(row){BD(null);C(row.code);N(row.name);SI(row.id);CH(null);}}}><option value="">{tr('savedScripts')}</option>{scripts.map(v=><option key={v.id} value={v.id}>{v.name}</option>)}</select></div><input aria-label={tr('scriptName')} placeholder={tr('scriptName')} value={name} onChange={e=>N(e.target.value)} maxLength={120}/><textarea className="python-source" aria-label={tr('source')} value={code} onChange={e=>C(e.target.value)} spellCheck={false} maxLength={64000}/><div className="control-bar"><button className="primary" disabled={active||busy||!code.trim()} onClick={()=>void run()}>{tr('run')}</button><button disabled={!active||busy} onClick={()=>void stop()}>{tr('stop')}</button><button disabled={busy||!code.trim()} onClick={()=>void save()}>{tr('saveScript')}</button><button onClick={()=>{BD(null);C(samples.browse);SI('');N('');}} disabled={active}>{tr('newScript')}</button></div></>}
  {tab==='actions'&&<section><input aria-label={tr('findAction')} placeholder={tr('findAction')} value={filter} onChange={e=>FL(e.target.value)}/><p>{matches.length} · {tr('sharedRegistry')}</p>{matches.map(v=><details className="control-action" key={v.name}><summary><code>{v.name}</code><span>Level {v.level}</span></summary><p>{v.description}</p><p>{v.requires_project?tr('projectOnly'):tr('appScope')} · {v.permission}</p><pre>{JSON.stringify(v.parameters,null,2)}</pre></details>)}</section>}
  {tab==='history'&&<section><button onClick={()=>void refresh().catch(e=>E(String(e)))}>{tr('refresh')}</button>{history.map(row=><button className="control-history" key={row.id} onClick={()=>CH(row)}><strong>{row.title}</strong><span>{historyStatus(row)} · {row.duration_ms??'—'} ms</span><small>{row.created_at}</small></button>)}{!history.length&&<p>{tr('noHistory')}</p>}</section>}
  {tab==='external'&&<section><p>{tr('grantHelp')}</p><button disabled={busy||!!grant} onClick={()=>void makeGrant()}>{tr('createGrant')}</button>{grant&&<><p>{grant.notice}</p><pre>{'from novel_studio_api import Studio\nstudio = Studio.connect(\n    url='+JSON.stringify(location.origin)+',\n    token='+JSON.stringify(grant.token)+',\n    nonce='+JSON.stringify(grant.nonce)+'\n)\nprint(studio.projects.current())'}</pre><button onClick={()=>void api('/api/control/revoke',{token:grant.session_id},'POST').then(()=>G(null)).catch(e=>E(String(e)))}>{tr('revoke')}</button></>}</section>}
  {pending?.kind==='confirm'&&<section className="control-confirm"><h3>{tr('waiting')}</h3><strong>{pending.tool}</strong><p>{pending.message}</p><p>{pending.affected_resources?.join(' · ')}</p><details><summary>{tr('fixedPlan')}</summary><pre>{JSON.stringify(pending.arguments,null,2)}</pre></details><button className="primary" disabled={busy} onClick={()=>void reply(true)}>{tr('approve')}</button><button disabled={busy} onClick={()=>void reply(false)}>{tr('reject')}</button></section>}
  <section className="control-output"><header><h3>{tr('output')}</h3><span role="status">{chosen?historyStatus(chosen):pending?.kind==='confirm'?tr('waiting'):session?.task?.status||tr('idle')}</span></header><pre tabIndex={0}>{output||tr('noOutput')}</pre>{chosen?.error&&<p role="alert">{chosen.error}</p>}{!chosen&&session?.task?.error&&<p role="alert">{session.task.error}</p>}{(!chosen?session?.steps||[]:[]).map((step:D)=><details key={step.id}><summary>{step.tool} · {step.status}</summary><pre>{JSON.stringify(step.result||step.error||{},null,2)}</pre></details>)}{!chosen&&completed&&<button disabled={active} onClick={()=>{C('from novel_studio_api import Studio\nstudio = Studio.connect()\nprint(studio.tasks.wait('+JSON.stringify(completed.result.id)+', timeout=60))\n');T('script');}}>{tr('readApproved')}</button>}<AIRequestReceipt value={!chosen?session?.ai_metadata:undefined}/></section>
  {analysisSource?.record_id&&analysisRunId&&<section className="control-analysis-return"><h3>{tr('analysisReturnTitle')}</h3><p>{tr('analysisReturnBoundary')}</p><label>{tr('analysisComment')}<textarea aria-label={tr('analysisComment')} maxLength={2000} rows={3} value={analysisComment} onChange={e=>AC(e.target.value)}/></label><button disabled={active||busy} onClick={()=>void saveAnalysis()}>{tr('saveAnalysisReturn')}</button></section>}
  {aiTask&&<section className='control-ai-task'><h3>Codex / AI · {aiTask.status}</h3><small>{aiTask.id}</small><AIRequestReceipt value={aiTask.ai_metadata}/><pre>{aiOutput||aiTask.error||aiTask.result?.output||tr('taskWaiting')}</pre>{!terminal(aiTask.status)&&<button onClick={()=>void api<D>('/api/projects/'+aiTask.project+'/tasks/'+aiTask.id+'/cancel',{},'POST').then(v=>AT({...v,project:aiTask.project})).catch(e=>E(String(e)))}>{tr('stopAi')}</button>}</section>}{error&&<p className="control-message" role="status">{error}</p>}
 </aside>;
}
