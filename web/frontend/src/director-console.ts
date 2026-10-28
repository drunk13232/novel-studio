// Local console presentation and explicit handoff; never schedules AI or writes prose.
export type DirectorHandoff={project:string;path:string;id:string;etag:string;title:string;request:number};
type D=Record<string,any>;
export function stepProgress(row:D|null){
 const steps:D[]=row?.plan?.steps||[],completed=new Set<number>(row?.completed||[]);
 const enabled=steps.map((s,index)=>({...s,index})).filter(s=>steps[s.index].enabled);
 return {done:enabled.filter(s=>completed.has(s.index)).length,total:enabled.length,next:enabled.find(s=>!completed.has(s.index))?.index??null};
}
export function filterDirectorRecords(rows:D[],query:string,state:string){
 const q=query.trim().toLocaleLowerCase();
 return rows.filter(r=>(!q||[r.goal,r.executor,r.mode].join(' ').toLocaleLowerCase().includes(q))&&(state==='all'||(state==='active'?!!r.active_task:state==='attention'?['FAILED','INTERRUPTED','PAUSED','PLAN_REVIEW'].includes(r.status):['CANDIDATE','REVIEW_READY'].includes(r.status))));
}
export const DIRECTOR_PYTHON_SAMPLE=`from novel_studio_api import Studio
import re

studio = Studio.connect()
# Only the author-selected frozen candidate is available to this call.
result = studio.call("get_director_result")
text = result["draft"]
paragraphs = [p for p in text.splitlines() if p.strip()]
print("record:", result["record_id"])
print("sha256:", result["draft_sha256"])
print("characters:", len(text))
print("Chinese characters:", len(re.findall(r"[\u4e00-\u9fff]", text)))
print("paragraphs:", len(paragraphs))
print("longest paragraph:", max(map(len, paragraphs), default=0))
print("completed steps:", result["completed_steps"])
print("Read-only local analysis. No AI call or manuscript change.")
`;
export function directorExport(row:D){
 // Exclude Writer context, credentials, raw source and unrelated task records.
 return {format:'novel-studio-director-report/1',record_id:row.id,source_path:row.path,source_revision:row.revision,
  goal:row.goal,status:row.status,mode:row.mode,models:{commander:row.commander,executor:row.executor},
  controls:{commander:row.commander_controls,executor:row.request_controls},plan:row.plan,completed_steps:row.completed,
  draft:row.draft,analysis_notes:row.analysis_notes,forked_from:row.forked_from,usage:row.usage,limits:row.limits,last_error:row.last_error,created_at:row.created_at,updated_at:row.updated_at,
  notice:'Private candidate report. Not Canon or an adopted manuscript. Check before sharing.'};
}
