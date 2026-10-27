import {LiteraryArt} from './literary-art';
import i18n,{formatBytes} from './i18n';
import {t as translateUI,useUiTranslation} from './i18n';
import {useEffect,useId,useState} from 'react';
import {api} from './api';
import type {Data} from './domain';
export type {Data};
// Temporary UI choices are namespaced by novel, separate from story records.
export function usePageState<T>(project:string,page:string,key:string,initial:T){
 const storageKey='novel-studio:view:'+project+':'+page+':'+key;
 const [value,setValue]=useState<T>(()=>{try{const raw=sessionStorage.getItem(storageKey);return raw===null?initial:JSON.parse(raw);}catch{return initial;}});
 useEffect(()=>{try{sessionStorage.setItem(storageKey,JSON.stringify(value));}catch{}},[storageKey,value]);
 return [value,setValue] as const;
}
const unsavedForms=new Map<string,string>();
export const unsavedMessage=()=>Array.from(new Set(unsavedForms.values())).join('、');
export function useUnsavedChanges(dirty:boolean,label:string){
 const id=useId();
 useEffect(()=>{if(dirty)unsavedForms.set(id,label);else unsavedForms.delete(id);return()=>{unsavedForms.delete(id);};},[id,dirty,label]);
}
export const base=(p:string)=>'/api/projects/'+p;
export const size=formatBytes;
export const date=(s:string)=>s?new Date(s).toLocaleString(i18n.language):'—';
export const imageUrl=(p:string,id:string,thumbnail=false)=>base(p)+'/assets/'+id+'/file'+(thumbnail?'?thumbnail=true':'');
export const saveJSON=(name:string,value:unknown)=>{const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
export async function upload<T>(url:string,file:File):Promise<T>{return api<T>(url,file,'POST');}
export function useRemote<T>(url:string,initial:T){const [value,setValue]=useState(initial),[error,setError]=useState(''),[busy,setBusy]=useState(false);const refresh=async()=>{const v=await api<T>(url);setValue(v);return v;};useEffect(()=>{let active=true;void api<T>(url).then(v=>{if(active)setValue(v);}).catch(e=>{if(active)setError(String(e));});return()=>{active=false};},[url]);const run=async(fn:()=>Promise<unknown>)=>{setBusy(true);setError('');try{await fn();}catch(e){setError(String(e).replace(/^Error: /,''));}finally{setBusy(false);}};return {value,setValue,error,setError,busy,refresh,run};}
export function ErrorNote({text}:{text:string}){
 useUiTranslation(["common","editor"]);
return text?<p role="alert" className="studio-alert">{text}</p>:null;}
export function Empty({text}:{text:string}){
 useUiTranslation(["common","editor"]);
return <div className="v12-empty"><LiteraryArt kind="empty"/><span>{text}</span></div>;}
export function HistoryPanel({project,path,onRestored}:{project:string;path?:string;onRestored?:(path:string)=>void}){
 useUiTranslation(["common","editor"]);

 const url=base(project)+'/data',r=useRemote<Data[]>(url+'/revisions'+(path?'?path='+encodeURIComponent(path):''),[]);const [selected,setSelected]=useState<Data|null>(null),[note,setNote]=useState('');
 return <section className="v12-history"><h3>{translateUI("editor:history")}</h3><p className="muted">{translateUI("common:restoreVersionBehaviorNotice")}</p><ErrorNote text={r.error}/>{path&&<div className="v12-inline"><input aria-label={translateUI("common:checkpointName")} placeholder={translateUI("common:checkpointNameExample")} value={note} onChange={e=>setNote(e.target.value)}/><button disabled={r.busy} onClick={()=>void r.run(async()=>{await api(url+'/checkpoint',{path,note},'POST');await r.refresh();})}>{translateUI("common:createCheckpoint")}</button></div>}<div className="v12-history-list">{!r.value.length&&<Empty text="第一次修改或建立检查点后，版本将保存在这里。"/>}{r.value.slice(0,150).map(v=><button className={selected?.id===v.id?'selected':''} key={v.id} onClick={()=>void r.run(async()=>setSelected(await api<Data>(url+'/revisions/'+v.id)))}><strong>{v.note||v.source}</strong><small>{date(v.created_at)} · {size(v.size)}</small>{!path&&<small>{v.path}</small>}</button>)}</div>{selected&&<><div className="v12-inline"><h4>{date(selected.created_at)}</h4><button disabled={r.busy} onClick={()=>void r.run(async()=>{const v=await api<Data>(url+'/revisions/'+selected.id+'/restore',{etag:selected.current_etag},'POST');setSelected(null);await r.refresh();onRestored?.(v.path);})}>{translateUI("common:restoreAsNewVersion")}</button></div><details open><summary>{translateUI("common:compareWithCurrentVersion")}</summary><pre className="v12-code">{selected.diff||'内容相同'}</pre></details><details><summary>{translateUI("common:viewFullHistoricalText")}</summary><pre className="v12-code">{selected.content}</pre></details></>}</section>;
}
export function Relations({project,type,id,onChange,onTarget}:{project:string;type:string;id:string;onChange?:()=>void;onTarget?:(type:string,id:string)=>void}){
 useUiTranslation(["common","editor"]);

 const r=useRemote<Data>(base(project)+'/bible',{targets:[],relations:[]});const [target,setTarget]=useState(''),[kind,setKind]=useState('相关'),[description,setDescription]=useState('');const outgoing=r.value.relations.filter((x:Data)=>x.source_type===type&&x.source_id===id),incoming=r.value.relations.filter((x:Data)=>x.target_type===type&&x.target_id===id);const name=(id:string)=>r.value.targets.find((x:Data)=>x.id===id)?.name||'未命名关联';
 return <section><ErrorNote text={r.error}/><h3>{translateUI("common:linkedContent")}</h3>{outgoing.length?outgoing.map((x:Data)=><p key={x.id}>{x.relation_type} → <button disabled={!onTarget} onClick={()=>onTarget?.(x.target_type,x.target_id)}>{name(x.target_id)}</button> · {x.description} <button disabled={x.derived} title={x.derived?'在对应设定字段中编辑此关系':''} onClick={()=>void r.run(async()=>{await api(base(project)+'/bible/relations/'+x.id,{},'DELETE');await r.refresh();onChange?.();})}>{translateUI("common:removeLink")}</button></p>):<Empty text="还没有关联。关系仅代表这一方向。"/>}<h3>{translateUI("common:settingsReferencingThisItem")}</h3>{incoming.length?incoming.map((x:Data)=><p key={x.id}><button disabled={!onTarget} onClick={()=>onTarget?.(x.source_type,x.source_id)}>{name(x.source_id)}</button> → {x.relation_type} · {x.description}</p>):<p className="muted">{translateUI("common:referencesEmptyLocationHint")}</p>}<div className="v12-fields"><label>{translateUI("common:linkedItem")}<select value={target} onChange={e=>setTarget(e.target.value)}><option value="">{translateUI("common:selectCharacterLocationOrChapter")}</option>{r.value.targets.filter((x:Data)=>x.id!==id).map((x:Data)=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>{translateUI("common:relationshipType")}<input value={kind} onChange={e=>setKind(e.target.value)} placeholder={translateUI("common:relationshipTypeExamples")}/></label><label>{translateUI("common:relationshipDescription")}<input value={description} onChange={e=>setDescription(e.target.value)}/></label></div><button disabled={!target||r.busy} onClick={()=>void r.run(async()=>{const t=r.value.targets.find((x:Data)=>x.id===target);await api(base(project)+'/bible/relations',{source_type:type,source_id:id,target_type:t.type,target_id:target,relation_type:kind,description},'POST');await r.refresh();onChange?.();})}>{translateUI("common:addRelationship")}</button></section>;
}
