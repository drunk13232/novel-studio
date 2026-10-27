import {api} from './api';
type Position={scope:string;source:string;id:string;hash:string;unit:string;top:number;at:string};
const storage='novel-studio:reference-reading:v2';
let queue:Promise<unknown>=Promise.resolve();
let loaded:Position[]|null=null;let revision=0;
export function referencePositions():Position[]{if(loaded)return loaded;try{const value=JSON.parse(localStorage.getItem(storage)||'[]');return Array.isArray(value)?value:[];}catch{return [];}}
function cache(rows:Position[]){loaded=rows;try{localStorage.setItem(storage,JSON.stringify(rows));}catch{}window.dispatchEvent(new Event('reference-reading-changed'));}
export async function refreshReferencePositions(scope='public'){await queue.catch(()=>{});const before=revision;const rows=await api<Position[]>('/api/studio/reference-reading?scope='+encodeURIComponent(scope));if(before===revision)cache(rows);return referencePositions();}
export function referencePosition(scope:string,source:string,id:string,hash:string){return referencePositions().find(p=>p.scope===scope&&p.source===source&&p.id===id&&p.hash===hash);}
export function saveReferencePosition(p:Omit<Position,'at'>){revision++;cache([{...p,at:new Date().toISOString()},...referencePositions().filter(x=>!(x.scope===p.scope&&x.source===p.source&&x.id===p.id))].slice(0,120));queue=queue.catch(()=>{}).then(()=>api('/api/studio/reference-reading',p,'PUT'));return queue;}
