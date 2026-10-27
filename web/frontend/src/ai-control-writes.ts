// Preference writes only. Never launches a model or retries a generation.
const pending=new Map<string,()=>Promise<unknown>>();
let active:Promise<void>|null=null;
export function deferAIControlWrite(key:string,save:()=>Promise<unknown>){pending.set(key,save);}
export async function flushAIControlWrites():Promise<void>{
 if(active){await active;if(pending.size)return flushAIControlWrites();return;}
 if(!pending.size)return;
 const rows=[...pending];pending.clear();
 active=(async()=>{for(let i=0;i<rows.length;i++){const [,save]=rows[i];try{await save();}catch(error){for(const [key,retry] of rows.slice(i))if(!pending.has(key))pending.set(key,retry);throw error;}}})();
 try{await active;}finally{active=null;}
 if(pending.size)await flushAIControlWrites();
}
