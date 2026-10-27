import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import ts from 'typescript';

// Shipping request scheduler with a deterministic local transport adapter.
// No browser, desktop, AI service or project file is used.
let checks=0,serial=0;
const equal=(actual,expected)=>{assert.deepEqual(actual,expected);checks++;};
const settle=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const response=(body={},status=200)=>({ok:status>=200&&status<300,status,json:async()=>body});
const search='/api/projects/fixture/workbench/replace/search';
const file='/api/projects/fixture/files/content';
const summary='/api/projects/fixture/experience/focus-summary';
const body={path:'chapters/story/draft.txt',content:'Local fixture'};
function driver(){
 const trace=[],notices=[],handlers=new Map();let flushes=0;
 globalThis.window={dispatchEvent:e=>{notices.push(e);return true;},confirm:()=>{throw Error('Unexpected remote consent');}};
 globalThis.__localApiCheck={t:key=>key,writingMetricsMutation:()=>null,WRITING_METRICS_CHANGED:'fixture-metrics',flushAIControlWrites:async()=>{flushes++;}};
 globalThis.fetch=async(url,options={})=>{trace.push({url,method:options.method,signal:options.signal,headers:options.headers});if(handlers.has(url))return handlers.get(url)(options);if(url==='/api/session')return response({request_token:'local-test-token'});return response({path:body.path});};
 return {trace,notices,handlers,flushes:()=>flushes};
}
async function module(source){
 let js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
 js=js.replace(/^import \{[^}]*\} from ['"]\.\/(?:i18n|writing-metrics-events|ai-control-writes)['"];?$/gm,'');
 assert(!/^import /m.test(js));
 const prefix='const {t,writingMetricsMutation,WRITING_METRICS_CHANGED,flushAIControlWrites}=globalThis.__localApiCheck;\n';
 return import('data:text/javascript;base64,'+Buffer.from(prefix+js).toString('base64')+'#'+serial++);
}
const current=await readFile(new URL('../src/api.ts',import.meta.url),'utf8');
async function previewProbe(source,expected){
 const d=driver(),{api}=await module(source),hold=deferred();
 d.handlers.set(search,()=>hold.promise);
 const preview=api(search,{query:'fixture'},'POST');await settle();
 assert(d.trace.some(x=>x.url===search));checks++;
 const save=api(file,body,'PUT');await settle();
 const blocked=!d.trace.some(x=>x.url===file);equal(blocked,expected);
 hold.resolve(response({id:'local-preview'}));await Promise.all([preview,save]);
 equal(d.trace.find(x=>x.url===search).headers['X-Novel-Request'],'local-test-token');
 return {saveQueuedBehindPreview:blocked};
}
let before=null;
if(process.argv.includes('--baseline')){
 const original=await readFile(new URL('../../../docs/daily-writing-tools/private-checks/refinement/api-before.ts',import.meta.url),'utf8');
 before=await previewProbe(original,true);
}
const after=await previewProbe(current,false);
{
 const d=driver(),{api}=await module(current),hold=deferred();let writes=0;
 d.handlers.set(file,()=>++writes===1?hold.promise:response({path:body.path}));
 const first=api(file,body,'PUT');await settle();const second=api(file,body,'PUT');await settle();
 equal(writes,1); // Actual manuscript writes remain serialized.
 await api(summary,{cursor:{event_count:0,fingerprint:'fixture'}},'POST');
 equal(writes,1);assert(d.trace.some(x=>x.url===summary));checks++;
 await api('/api/projects/fixture/experience/focus-boundary');equal(writes,1);
 hold.resolve(response({path:body.path}));await Promise.all([first,second]);equal(writes,2);
}
{
 const d=driver(),{api}=await module(current),controller=new AbortController();
 d.handlers.set(search,options=>new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(new DOMException('Cancelled','AbortError')),{once:true});}));
 const pending=api(search,{query:'fixture'},'POST',{signal:controller.signal});await settle();controller.abort();
 await assert.rejects(pending,e=>e.name==='AbortError');checks++;
 equal(d.notices.length,0); // User cancellation is not a service failure.
 await api(file,body,'PUT');equal(d.trace.filter(x=>x.url===file).length,1);
 equal(d.trace.filter(x=>x.url===search).length,1); // No preview retry after cancel.
 const expired=new AbortController();expired.abort();const n=d.trace.length;
 await assert.rejects(api(search,{},'POST',{signal:expired.signal}),e=>e.name==='AbortError');checks++;equal(d.trace.length,n);
 for(const route of [file,'/api/projects/fixture/workbench/replace/apply-selection','/api/projects/fixture/workbench/replace/batches/fixture/undo','/api/projects/fixture/tasks']){
  const n=d.trace.length;
  await assert.rejects(api(route,body,'POST',{signal:new AbortController().signal}),e=>e.code==='CANCELLATION_NOT_SUPPORTED');checks++;equal(d.trace.length,n);
 }
}
{
 const d=driver(),{api}=await module(current);let count=0;
 d.handlers.set(search,()=>++count===1?response({code:'SESSION_INVALID',detail:'fixture'},403):response({id:'ok'}));
 equal((await api(search,{},'POST')).id,'ok');equal(count,2);
 equal(d.trace.filter(x=>x.url==='/api/session').length,2);
 equal(d.trace.filter(x=>x.url===search).every(x=>x.headers['X-Novel-Request']==='local-test-token'),true);
 await api('/api/projects/fixture/tasks',{type:'fixture'},'POST');equal(d.flushes(),1);
 d.handlers.set(search,()=>{throw new TypeError('Offline fixture');});
 await assert.rejects(api(search,{},'POST'),e=>e.message==='errors:LOCAL_SERVICE_UNAVAILABLE');checks++;
}
{
 const d=driver(),{api}=await module(current),hold=deferred();
 d.handlers.set(file,()=>hold.promise);
 const save=api(file,body,'PUT');await settle();
 for(const route of ['/api/projects/fixture/book/print-preview/'+'a'.repeat(32)+'/cancel','/api/projects/fixture/audio-export/audio_'+'b'.repeat(32)+'/cancel']){
  await api(route,{},'POST');equal(d.trace.some(x=>x.url===route),true);equal(d.trace.find(x=>x.url===route).headers['X-Novel-Request'],'local-test-token');
 }
 equal(d.trace.filter(x=>x.url===file).length,1);hold.resolve(response({path:body.path}));await save;
}
if(process.argv.includes('--baseline'))await writeFile(new URL('../../../docs/daily-writing-tools/private-checks/refinement/request-scheduling.json',import.meta.url),JSON.stringify({before,after,checks,environment:'LOCAL TRANSPORT ADAPTER; no real-time performance claim'},null,2));
console.log(`${checks} LOCAL PASS shipping API scheduling/cancellation checks. Preview no longer blocks saves; write serialization and token/AI-control gates preserved. Local transport adapter only.`);
