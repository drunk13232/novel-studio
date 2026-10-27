/** Local notifications contain identifiers only, never manuscript text or journal contents. */
export const WRITING_METRICS_CHANGED = 'novel-writing-metrics-changed';
export const WRITING_PROGRESS_LOADED = 'novel-writing-progress-loaded';
export type WritingMetricsChange = {project:string;kind:'save'|'goals'|'note'|'restore'};
export type WritingProgress = {
 project_id:string;date:string;timezone:string;today:number;daily_goal:number;current_streak:number;
 manual_today:number;ai_today:number;restore_today:number;unknown_today:number;has_saved_events:boolean;
};
const manuscript = (path:unknown) => typeof path === 'string' && /^chapters\/(chapter-\d+|story)\/(draft|final|manual-[a-z0-9-]+)\.(txt|md)$/.test(path);
export const isManuscriptPath=manuscript;
/** Classify real, successful mutation receipts. Rejections and recovery copies are excluded. */
export function writingMetricsMutation(url:string,body:unknown,method:string,result:unknown):WritingMetricsChange|null {
 const match = /^\/api\/projects\/([^/?#]+)\/(.+?)(?:\?.*)?$/.exec(url);
 if(!match)return null;
 const project=match[1],route=match[2],data=result as Record<string,any>|null,input=body as Record<string,any>|null;
 if(method==='PUT'&&route==='files/content'&&manuscript(input?.path)&&data?.path===input?.path)return {project,kind:'save'};
 if(method==='POST'&&/^studio-tools\/candidates\/[^/]+\/decision$/.test(route)&&data?.status==='ACCEPTED'&&manuscript(data.file?.path))return {project,kind:'save'};
 if(method==='POST'&&/^data\/revisions\/[^/]+\/restore$/.test(route)&&manuscript(data?.path))return {project,kind:'restore'};
 if(method==='POST'&&/^workbench\/replace\/(?:apply-selection|apply)$/.test(route)&&data?.status==='APPLIED'&&Array.isArray(data.paths)&&data.paths.some(manuscript))return {project,kind:'save'};
 if(method==='POST'&&/^workbench\/replace\/batches\/[^/]+\/undo$/.test(route)&&data?.status==='UNDONE'&&Array.isArray(data.paths)&&data.paths.some(manuscript))return {project,kind:'restore'};
 if(method==='PUT'&&route==='experience/goals'&&data?.saved===true)return {project,kind:'goals'};
 if(method==='PUT'&&route==='experience/daily-note'&&data?.saved===true)return {project,kind:'note'};
 return null;
}
export function goalCrossedToday(before:WritingProgress|null,after:WritingProgress,kind:WritingMetricsChange['kind']):boolean {
 if(!before||(kind!=='save'&&kind!=='restore')||before.project_id!==after.project_id||after.daily_goal<=0||before.daily_goal!==after.daily_goal)return false;
 const previous=before.date===after.date?before.today:0;
 return previous<after.daily_goal&&after.today>=after.daily_goal;
}
export function goalNoticeKey(progress:Pick<WritingProgress,'project_id'|'date'>){return 'novel-writing-goal-notice:'+progress.project_id+':'+progress.date;}
export function invalidateWritingMetrics(project:string,kind:WritingMetricsChange['kind']='goals') {
 window.dispatchEvent(new CustomEvent<WritingMetricsChange>(WRITING_METRICS_CHANGED,{detail:{project,kind}}));
}
