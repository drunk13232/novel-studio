import {useState} from 'react';
import {api} from './api';
import {t,useUiTranslation} from './i18n';
type Data=Record<string,any>;
const tr=(k:string)=>t('reliability:'+k);
export function ManualAcceptance({project,report,onUpdated}:{project:string;report:Data;onUpdated:(r:Data)=>void}){
 useUiTranslation(['reliability']);
 const [notes,setNotes]=useState<Record<string,string>>({}),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const rules=(report.acceptance_results||[]).filter((r:Data)=>r.manual);
 if(!rules.length)return null;
 async function decide(rule:Data,status:'PASS'|'FAIL'){
  setBusy(true);setError('');
  try{const v=await api<Data>('/api/projects/'+project+'/world-logic/reports/'+report.id+'/manual-review',{
   rule_id:rule.id,status,note:notes[rule.id]?.trim(),definition_fingerprint:report.definition_fingerprint,
   acceptance_fingerprint:report.acceptance_fingerprint,rule_fingerprint:rule.rule_fingerprint,review_revision:report.review_revision,confirm:true
  },'POST');onUpdated(v);}catch(e){setError(String(e));}finally{setBusy(false);}
 }
 return <section className="wll-card" data-reliability="manual"><h3>{tr('manualTitle')}</h3><p>{tr('manualHelp')}</p><p>{tr('mathStatus')}：{report.mathematical_status} · {tr('pendingManual')}：{report.manual_pending}</p>{error&&<p role="alert">{error}</p>}{rules.map((r:Data)=><article className="wll-rule-result" key={r.id}><strong>{r.name}</strong><p>{r.status==='NOT RUN'?tr('pendingManual'):tr('authorDecision')+'：'+r.status}</p><p>{r.basis||tr('noBasis')}</p>{r.review&&<p>{r.review.note} · {new Date(r.review.at).toLocaleString()}</p>}{r.stale?<p className="wll-notice">{tr('manualStale')}</p>:<><label>{tr('manualNote')}<textarea aria-label={tr('manualNote')+' '+r.name} maxLength={1500} value={notes[r.id]||''} onChange={e=>setNotes({...notes,[r.id]:e.target.value})}/></label><div className="wll-actions"><button disabled={busy||!report.finished_at||!notes[r.id]?.trim()} onClick={()=>void decide(r,'PASS')}>{tr('authorPass')}</button><button disabled={busy||!report.finished_at||!notes[r.id]?.trim()} onClick={()=>void decide(r,'FAIL')}>{tr('authorFail')}</button></div></>}</article>)}{!!report.manual_reviews?.length&&<details><summary>{tr('reviewHistory')}</summary>{report.manual_reviews.map((r:Data)=><p key={r.id}>{r.rule_id} · {r.status} · {r.note} · {new Date(r.at).toLocaleString()}</p>)}</details>}</section>;
}
