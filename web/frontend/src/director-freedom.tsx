import {useEffect,useState} from 'react';
import AIControls from './ai-controls';
import {SceneIntentFields} from './director-delivery';
import {t} from './i18n';
type D=Record<string,any>;
const tr=(key:string)=>t('director:'+key);

export function StepExecution({project,step,index,model,controls,blocked,editingBlocked,canRun,onPatch,onRun,onInspect,onDuplicate,canDuplicate}:{project:string;step:D;index:number;model:string;controls:D|null;blocked:boolean;editingBlocked:boolean;canRun:boolean;onPatch:(patch:D)=>void;onRun:()=>void;onInspect:()=>void;onDuplicate:()=>void;canDuplicate:boolean}){
 const [open,setOpen]=useState(false),custom=!!step.executor||!!step.request_controls;
 return <section className="director-step-execution"><SceneIntentFields value={step.scene} disabled={editingBlocked} onChange={scene=>onPatch({scene})}/>
  <div className="director-controls"><button disabled={!canRun} onClick={onRun}>{tr('runThisStep')} {index+1}</button><button disabled={blocked} onClick={onInspect}>{tr('inspectThisStep')}</button><button disabled={!canDuplicate} onClick={onDuplicate}>{tr('duplicateStep')}</button></div>
  <small>{tr('selectedStepBoundary')}</small>
  <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>{tr('stepModel')} · {custom?(step.executor||step.request_controls?.model||model):tr('inheritModel')}</summary>{open&&<fieldset disabled={editingBlocked}>
   <label className="check"><input type="checkbox" checked={custom} onChange={e=>onPatch(e.target.checked?{executor:model,request_controls:{...controls,model,parameters:{...(controls?.parameters||{})}}}:{executor:null,request_controls:null})}/>{tr('customStepModel')}</label>
   {custom&&<AIControls key={step.step_id||index} persist={false} project={project} task="cowrite" model={step.executor||step.request_controls?.model||model} initial={step.request_controls||{...controls,model:step.executor||model,parameters:{}}} onModelChange={v=>{if(v!==(step.executor||model))onPatch({executor:v});}} onChange={v=>onPatch({executor:v.model||step.executor||model,request_controls:v})}/>}
   <small>{tr('stepModelBoundary')}</small>
  </fieldset>}</details>
 </section>;
}

export function ForkAttempt({row,blocked,onFork,onOriginal}:{row:D;blocked:boolean;onFork:(goal:string,keep:boolean)=>void;onOriginal:(id:string)=>void}){
 const [goal,setGoal]=useState(''),[keep,setKeep]=useState(true);
 useEffect(()=>{setGoal(row.goal);setKeep(true);},[row.id]);
 return <section className="director-fork"><h3>{tr('forkTitle')}</h3><p className="muted">{tr('forkBoundary')}</p>
  {row.forked_from&&<p>{tr('forkOrigin')} <button disabled={blocked} onClick={()=>onOriginal(row.forked_from.id)}>{tr('openOriginal')}</button></p>}
  <label>{tr('forkGoal')}<input aria-label={tr('forkGoal')} maxLength={2500} value={goal} onChange={e=>setGoal(e.target.value)}/></label>
  <label className="check"><input type="checkbox" checked={keep} onChange={e=>setKeep(e.target.checked)}/>{tr('forkKeepDraft')}</label>
  <small>{keep?tr('forkContinueBoundary'):tr('forkFreshBoundary')}</small>
  <button disabled={blocked||!goal.trim()} onClick={()=>onFork(goal,keep)}>{tr('forkCreate')}</button>
 </section>;
}

export function AnalysisNotes({notes,blocked,onRemove}:{notes:D[];blocked:boolean;onRemove:(id:string)=>void}){
 return <section className="director-analysis"><h3>{tr('analysisTitle')}</h3><p className="muted">{tr('analysisBoundary')}</p>{!notes.length&&<p>{tr('analysisEmpty')}</p>}
 {notes.map(n=><article key={n.run_id}><header><strong>{n.title}</strong><small>{n.created_at} · {n.persona} · {n.status}</small></header>{n.stale&&<p className="studio-notice">{tr('analysisStale')}</p>}{n.comment&&<blockquote>{n.comment}</blockquote>}<pre>{n.output}</pre>{n.output_truncated&&<small>{tr('analysisTruncated')}</small>}<small>{tr('candidateFingerprint')} {n.candidate_sha256.slice(0,12)}</small><button disabled={blocked} onClick={()=>onRemove(n.run_id)}>{tr('removeAnalysis')}</button></article>)}
 </section>;
}
