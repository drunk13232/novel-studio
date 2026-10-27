import {formatStoryDate} from './i18n';
import {t as translateUI,useUiTranslation} from './i18n';
import moment from 'moment';
import {parse} from 'yaml';
import {api, type Content} from './api';

type Row=Record<string,any>;
export type EventKind='OCCURRED'|'PLANNED'|'BACKGROUND'|'AUTHOR';
export const kindNames:Record<EventKind,string>={get OCCURRED(){return translateUI("timeline:eventOccurredLabel");},get PLANNED(){return translateUI("timeline:planned");},get BACKGROUND(){return translateUI("timeline:background");},get AUTHOR(){return translateUI("timeline:authorRecordsLabel");}};
export type NamedRef={id:string;name:string;resolved:boolean};
export type TimelineEvent={id:string;kind:EventKind;name:string;summary:string;result:string;chapter:number|null;chapterId:string;chapterName:string;chapterPath:string|null;start:number|null;end:number|null;date:string;characters:NamedRef[];locations:NamedRef[];threads:NamedRef[];settings:NamedRef[];issues:string[]};
export type TimelineModel={events:TimelineEvent[];offset:number;zoneLabel:string;lastChapter:number;uncommitted:number;hidden:number;warnings:string[]};
export type TimelineSources={timeline:Row;ledger:Row;locations:Row;threads:Row;bible:Row;chapters:Row[];characters:Row[];plans?:Row[]};
const text=(v:unknown)=>typeof v==='string'?v.trim():'';
const values=(v:unknown):string[]=>Array.isArray(v)?v.filter(x=>typeof x==='string'):typeof v==='string'?[v]:[];
const refs=(v:unknown):string[]=>Array.isArray(v)?v.flatMap(x=>typeof x==='string'?[x]:x&&typeof x==='object'?values((x as Row).id):[]):typeof v==='string'?[v]:v&&typeof v==='object'?Object.values(v).flatMap(values):[];
const hasAuthorFlag=(v:Row)=>v.author_only===true||v.secret===true||['AUTHOR','AUTHOR_ONLY','PRIVATE','SECRET'].includes(v.visibility);

// A rendering projection only. Writer knowledge is never inferred from this page.
function disclosed(row:Row,lastChapter:number):string{
 if(hasAuthorFlag(row))return '';
 if(Array.isArray(row.writer_view))return row.writer_view.filter((v:Row)=>['PUBLIC','CHARACTER'].includes(v.visibility)&&Number(v.since_chapter)<=lastChapter&&!hasAuthorFlag(v)).map((v:Row)=>text(v.text)).filter(Boolean).join('\n');
 return text(row.public_summary)||(row.visibility==='PUBLIC'?text(row.summary):'');
}
function storyDate(value:unknown,offset:number){
 const raw=text(value);
 if(!/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$/.test(raw))return null;
 const explicit=/T.*(?:Z|[+-]\d{2}:?\d{2})$/.test(raw);
 const m=explicit?moment.parseZone(raw,moment.ISO_8601,true):moment.utc(raw,moment.ISO_8601,true).utcOffset(offset,true);
 return m.isValid()?{time:m.valueOf(),label:formatStoryDate(/^\d{4}-\d{2}-\d{2}$/.test(raw)?raw:m.format()),explicit}:null;
}
export function projectTimeline(sources:TimelineSources):TimelineModel{
 const rawEvents:Array<Row>=Array.isArray(sources.timeline.events)?sources.timeline.events:[];
 const committed=new Set<number>((sources.ledger.entries||[]).filter((r:Row)=>r.committed_at||r.status==='COMMITTED').map((r:Row)=>Number(r.chapter)));
 const lastChapter=Math.max(0,...committed);
 const dateSource=rawEvents.find(r=>/T.*(?:Z|[+-]\d{2}:?\d{2})$/.test(text(r.story_time)));
 const offset=dateSource?moment.parseZone(dateSource.story_time,moment.ISO_8601,true).utcOffset():0;
 const validOffset=Number.isFinite(offset)?offset:0;
 const zoneLabel=dateSource?'UTC'+moment.utc().utcOffset(validOffset).format('Z'):translateUI('timeline:noDeclaredTimeZone');
 const characterNames=new Map<string,string>(sources.characters.map(c=>[String(c.canonical?.id||c.id),text(c.canonical?.name||c.name)]));
 const locationNames=new Map<string,string>(Object.entries<Row>(sources.locations.locations||{}).map(([id,r])=>[id,text(r.name)]));
 const entities=new Map<string,Row>();
 for(const e of sources.bible.entities||[])if(['FORMAL','LOCKED'].includes(e.status)&&!hasAuthorFlag(e)){entities.set(e.id,e);if(['locations','location','places','place','city','building','region','continent','village','special_location'].includes(e.category))locationNames.set(e.id,text(e.name));}
 const threadNames=new Map<string,string>();
 for(const [id,r] of Object.entries<Row>(sources.threads.threads||{}))if(disclosed(r,lastChapter))threadNames.set(id,text(r.title||r.name));
 const reference=(id:string,names:Map<string,string>,fallback:string):NamedRef=>({id,name:names.get(id)||fallback,resolved:!!names.get(id)});
 const settingNames=new Map<string,string>(Array.from(entities,([id,e])=>[id,text(e.name)]));
 const chapterInfo=(chapter:number|null,stableId='')=>sources.chapters.find(c=>stableId&&c.card_id===stableId)||sources.chapters.find(c=>Number(c.number)===chapter);
 const events:TimelineEvent[]=[];let uncommitted=0,hidden=0;const warnings:string[]=[];const seen=new Set<string>();
 function make(row:Row,kind:EventKind,summary:string,id:string,chapter:number|null){
  if(seen.has(id)){warnings.push(translateUI('timeline:duplicateEventId'));return;}seen.add(id);
  const start=storyDate(row.story_time||row.story_start||row.start_time,validOffset),endRaw=row.story_end||row.end_time||row.story_time_end;
  const end=endRaw?storyDate(endRaw,validOffset):null;const issues:string[]=[];
  if(!start)issues.push(translateUI('timeline:missingStoryDate'));
  if(endRaw&&(!end||start&&end.time<start.time))issues.push(translateUI('timeline:invalidEndDate'));
  const info=chapterInfo(chapter,text(row.chapter_id));
  const characters=values(row.characters).map(id=>reference(id,characterNames,translateUI('timeline:unknownCharacter')));
  const locations=values(row.locations||row.location).map(id=>reference(id,locationNames,translateUI('timeline:unnamedLocation')));
  const threads=refs(row.plot_threads||row.threads).map(id=>reference(id,threadNames,translateUI('timeline:privateOrUnnamedThread')));
  const settings=refs(row.related_entities||row.related_settings||row.settings).map(id=>reference(id,settingNames,translateUI('timeline:privateOrUnnamedSetting')));
  for(const relation of sources.bible.relations||[])if(relation.source_type==='event'&&relation.source_id===row.id&&relation.target_type==='entity')settings.push(reference(relation.target_id,settingNames,translateUI('timeline:privateOrUnnamedSetting')));
  if([...characters,...locations].some(r=>!r.resolved))issues.push(translateUI('timeline:unresolvedReferences'));
  const name=(kind==='PLANNED'?text(row.title):kind==='AUTHOR'?translateUI('timeline:authorRecord'):text(row.public_title)||(row.visibility==='PUBLIC'?text(row.name||row.title):''))||summary.split(/[；;。\n]/)[0]||kindNames[kind];
  events.push({id,kind,name:name.length>30?name.slice(0,30)+'…':name,summary,result:kind==='PLANNED'?translateUI('timeline:planNotFact'):text(row.public_result)||(row.visibility==='PUBLIC'?text(row.actual_result||row.result):'')||translateUI('timeline:noSeparateOutcome'),chapter,chapterId:text(info?.card_id||row.chapter_id),chapterName:chapter===0?translateUI('timeline:beforeStoryStart'):chapter!==null?translateUI('timeline:chapterReferenceTitle',{number:chapter,title:info?.title?' · '+info.title:''}):translateUI('timeline:chapterNotLinked'),chapterPath:committed.has(Number(chapter))?(info?.final_path||info?.path||null):null,start:start?.time??null,end:end&&start&&end.time>=start.time?end.time:null,date:start?.label||translateUI('timeline:dateNotRecorded'),characters,locations,threads,settings,issues});
 }
 for(const row of rawEvents){
  if(!text(row.id)){warnings.push(translateUI('timeline:missingStableId'));continue;}
  const chapter=Number.isInteger(row.chapter)?row.chapter:null;
  let kind:EventKind=['AUTHOR','AUTHOR_METADATA','METADATA','SYSTEM'].includes(row.type||row.event_type)||hasAuthorFlag(row)?'AUTHOR':['PLANNED','PLAN'].includes(row.type||row.event_type)?'PLANNED':chapter===0?'BACKGROUND':'OCCURRED';
  if(kind==='OCCURRED'&&!committed.has(Number(chapter))){uncommitted++;continue;}
  const summary=disclosed(row,lastChapter);
  if(kind!=='AUTHOR'&&!summary){hidden++;continue;}
  make(row,kind,kind==='AUTHOR'?'作者或系统记录。详细内容仅在高级数据视图中查看。':summary,row.id,chapter);
 }
 for(const plan of sources.plans||[]){
  if(committed.has(Number(plan.number))||plan.status==='ARCHIVED'||!plan.id)continue;
  // Deliberate author-plan opt-in. Never copy must_not_include, secrets, payoff,
  // scene exit_state, expected State or hidden motivations into the normal view.
  const refsByKind=plan.plot_threads||{};
  make({id:plan.id,title:plan.title,chapter_id:plan.id,story_time:plan.story_time,story_end:plan.story_end,location:plan.location,characters:plan.characters,plot_threads:refsByKind},'PLANNED','这是大纲中的章节计划，尚未成为已发生的剧情。','plan:'+plan.id,Number(plan.number));
 }
 events.sort((a,b)=>(a.start??Infinity)-(b.start??Infinity)||(a.chapter??0)-(b.chapter??0)||a.id.localeCompare(b.id));
 const offsetMismatch=rawEvents.some(r=>{const d=storyDate(r.story_time,validOffset);return d?.explicit&&moment.parseZone(r.story_time).utcOffset()!==validOffset;});
 if(offsetMismatch)warnings.push('事件包含不同原始时区；时间轴使用 '+zoneLabel+'，详情保留各事件的原始时区。');
 return {events,offset:validOffset,zoneLabel,lastChapter,uncommitted,hidden,warnings};
}
export async function loadTimelineSources(project:string):Promise<TimelineSources>{
 const base='/api/projects/'+encodeURIComponent(project);
 const yaml=async(path:string,optional=false)=>{try{const r=await api<Content>(base+'/files/content?path='+encodeURIComponent(path));return parse(r.content,{maxAliasCount:100})||{};}catch(e){if(optional&&String(e).includes('不存在'))return {};throw e;}};
 const [timeline,ledger,locations,threads,bible,board,characters]=await Promise.all([yaml('state/timeline.yaml'),yaml('state/chapter-ledger.yaml'),yaml('state/locations.yaml',true),yaml('state/plot-threads.yaml',true),api<Row>(base+'/bible'),api<Row>(base+'/studio'),api<Row[]>(base+'/characters')]);
 return {timeline,ledger,locations,threads,bible,chapters:board.chapters,characters};
}
