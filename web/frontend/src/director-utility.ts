type Data=Record<string,any>;
export type LocatedEvidence={id:string;issue:number;quote:number;location:number;text:string;start:number;end:number;line:number;occurrence:number};
export function locatedEvidence(record:Data,report?:Data):LocatedEvidence[]{
 const text=record.draft||'',result:LocatedEvidence[]=[];
 for(const a of report?.anchors||[])for(const [quote,q] of (a.evidence||[]).entries())if(q.verified&&typeof q.quote==='string'&&q.quote.trim())for(const [location,h] of (q.locations||[]).entries()){
  if(!Number.isInteger(h.start)||!Number.isInteger(h.end)||h.start<0||h.end<=h.start||h.end>text.length||text.slice(h.start,h.end)!==q.quote)continue;
  result.push({id:a.issue+':'+quote+':'+location,issue:a.issue,quote,location,text:q.quote,start:h.start,end:h.end,line:text.slice(0,h.start).split('\n').length,occurrence:location+1});if(result.length>=500)return result;
 }
 return result;
}
export function targetPreview(text:string,hit:{start:number;end:number},scope='quote'){
 let {start,end}=hit;
 if(scope==='paragraph'){start=text.lastIndexOf('\n',start-1)+1;const tail=text.indexOf('\n',end);end=tail<0?text.length:tail;}
 return {start,end,quote:text.slice(start,end),line:text.slice(0,start).split('\n').length,before:text.slice(Math.max(0,start-100),start),after:text.slice(end,end+100)};
}
export function workflowState(row:Data|null){
 const active=!!row?.active_task,feedback=row?.feedback_state?.status||'NOT_RUN',currentReview=row?.review_validity?.status==='MATCHES_CANDIDATE';
 const generating=active&&row?.status==='GENERATING',planning=active&&row?.status==='PLANNING',reviewing=active&&row?.status==='REVIEWING';
 const reworkPlanning=planning&&row?.active_operation==='REWORK_PLAN',rewriting=generating&&row?.active_operation==='REWRITE';
 const flow=[
  {id:'setup',tab:'plan',state:row?'saved':'notRun'},
  {id:'plan',tab:'plan',state:planning&&!reworkPlanning?'active':row&&row.status!=='DRAFT'&&row.plan?.steps?.length?'prepared':'notRun'},
  {id:'draft',tab:'draft',state:generating&&!rewriting?'active':row?.draft?.trim()?'retained':'notRun'},
  {id:'review',tab:'results',state:reviewing?'active':row?.review_failed?'failed':currentReview?'reportSaved':row?.review_id?'historical':'notRun'},
  {id:'rework',tab:'results',state:reworkPlanning||rewriting?'active':feedback==='PROPOSED'?'waiting':feedback==='APPROVED'?'approved':feedback==='APPLIED'?'retained':feedback==='REJECTED'?'rejected':feedback==='HISTORICAL'?'historical':'optional'},
  {id:'adopt',tab:'draft',state:row?.delivery?.author_adopted?'adopted':'authorDecision'}
 ];
 const next=active?(row?.status==='CANCELLING'?'cancelling':row?.pause_requested?'pausing':'active'):feedback==='PROPOSED'?'checkRework':feedback==='APPROVED'?'runRework':row?.review_failed?'retryReview':currentReview?'inspectReport':row?.draft?.trim()&&row.delivery?.steps_complete?'reviewDraft':row?.status==='PLAN_REVIEW'?'checkPlan':row?'preparePlan':'setup';
 return {flow,next,targetTab:['checkRework','runRework','inspectReport'].includes(next)?'results':next==='reviewDraft'||next==='retryReview'?'draft':'plan'};
}
