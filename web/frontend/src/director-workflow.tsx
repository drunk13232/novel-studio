import {t} from './i18n';
import {workflowState} from './director-utility';
type Data=Record<string,any>;
export default function DirectorWorkflow({row,onTab,unsaved}:{row:Data|null;onTab:(value:string)=>void;unsaved:boolean}){
 const v=workflowState(row),tr=(key:string)=>t('director:usability.'+key);
 const latest=(phases:string[])=>[...(row?.usage||[])].reverse().find(x=>phases.includes(x.phase));
 return <section className="director-workflow" aria-label={tr('workflow')}>
  <div className="director-role-strip">{row&&[[row?.mode==='quick'?(row.auto_review?'reviewer':'directorOptional'):'director',row?.commander||'codex',latest(['PLAN','REVIEW','FEEDBACK'])],['writer',row?.executor||'—',latest(['WRITE'])]].map(([role,ref,receipt])=><div key={role as string}><small>{tr(role as string)}</small><strong>{ref as string}</strong>{receipt&&<small>{tr('lastRequest')} · {(receipt as Data).model||'UNKNOWN'}</small>}</div>)}</div>
  <ol className="director-route">{v.flow.map((step,i)=><li key={step.id} data-state={step.state}><button type="button" onClick={()=>onTab(step.tab)} aria-label={tr('stage_'+step.id)+' · '+tr('state_'+step.state)}><span aria-hidden="true">{i+1}</span><strong>{tr('stage_'+step.id)}</strong><small>{tr('state_'+step.state)}</small></button></li>)}</ol>
  <p className="director-next" role="status"><b>{tr('next_'+v.next)}</b>{!row?.active_task&&<button type="button" onClick={()=>onTab(v.targetTab)}>{tr('viewNext')}</button>}</p>{unsaved&&<small>{tr('saveFirst')}</small>}<small className="muted">{tr('workflowBoundary')}</small>
 </section>;
}
