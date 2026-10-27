import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';

// Run the actual client cache/event code with deterministic local transport and hook adapters.
// This verifies async state handling only; it is not a browser or desktop interaction test.
const transpile=source=>ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const dataModule=js=>'data:text/javascript;base64,'+Buffer.from(js).toString('base64');
const events=await import(dataModule(transpile(await readFile(new URL('../src/writing-metrics-events.ts',import.meta.url),'utf8'))));
let source=transpile(await readFile(new URL('../src/writing-metrics-client.ts',import.meta.url),'utf8'));
source=source.replace(/^import \{([^}]+)\} from ['"]react['"];$/gm,'const {$1}=globalThis.__writingMetricsCheck.react;')
 .replace(/^import \{([^}]+)\} from ['"]\.\/api['"];$/gm,'const {$1}=globalThis.__writingMetricsCheck;')
 .replace(/^import \{([^}]+)\} from ['"]\.\/writing-metrics-events['"];$/gm,'const {$1}=globalThis.__writingMetricsCheck.events;')
 .replace(/^export \{ invalidateWritingMetrics \} from ['"]\.\/writing-metrics-events['"];$/gm,'export const invalidateWritingMetrics=globalThis.__writingMetricsCheck.events.invalidateWritingMetrics;');
assert(!/^import /m.test(source),'All dependency seams must be explicitly provided by this local harness.');
const originals=new Map(['window','document','localStorage','CustomEvent','__writingMetricsCheck'].map(key=>[key,Object.getOwnPropertyDescriptor(globalThis,key)]));
const requests=[],notices=[],storage=new Map();let activeHook=null,checks=0;
const equal=(actual,expected)=>{assert.deepEqual(actual,expected);checks++;};
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const day=new Date(Date.now()+8*3600000).toISOString().slice(0,10);
const progress=(project,today,extra={})=>({project_id:project,date:day,timezone:'UTC+08:00',today,daily_goal:200,current_streak:1,manual_today:today,ai_today:0,restore_today:0,unknown_today:0,has_saved_events:true,...extra});
const next=project=>{
 const row=requests.find(item=>!item.settled&&item.url==='/api/projects/'+project+'/experience/writing-progress');
 assert(row,'Expected a real client read for '+project);return row;
};
async function reply(project,value){const row=next(project);row.settled=true;row.resolve(value);await flush();}
function change(project,kind='save'){window.dispatchEvent(new CustomEvent(events.WRITING_METRICS_CHANGED,{detail:{project,kind}}));}
function mount(client,project){
 const hook={cleanups:[],snapshot:null};activeHook=hook;
 try{client.useWritingProgress(project);}finally{activeHook=null;}
 return {read:()=>hook.snapshot,unmount:()=>{for(const cleanup of hook.cleanups.splice(0).reverse())cleanup();}};
}
try{
 globalThis.window=new EventTarget();globalThis.document=Object.assign(new EventTarget(),{visibilityState:'visible'});
 globalThis.CustomEvent=class extends Event{constructor(type,options={}){super(type);this.detail=options.detail;}};
 globalThis.localStorage={getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,String(value))};
 window.addEventListener('novel-writing-goal-reached',event=>notices.push(event.detail));
 globalThis.__writingMetricsCheck={events,api:url=>new Promise((resolve,reject)=>requests.push({url,resolve,reject,settled:false})),react:{
  useSyncExternalStore(subscribe,getSnapshot){const hook=activeHook;hook.snapshot=getSnapshot();hook.cleanups.push(subscribe(()=>{hook.snapshot=getSnapshot();}));return hook.snapshot;},
  useEffect(effect){const cleanup=effect();if(typeof cleanup==='function')activeHook.cleanups.push(cleanup);}
 }};
 const client=await import(dataModule(source));
 let main=mount(client,'main');await reply('main',progress('main',100));
 equal(main.read().data.today,100);equal(notices.length,0);
 // A read begins with a known baseline. A save and a note arrive before its response.
 const first=client.refreshWritingProgress('main');change('main','save');change('main','note');
 equal(requests.filter(row=>!row.settled).length,1);
 await reply('main',progress('main',250));
 equal(requests.filter(row=>!row.settled).length,1);
 await reply('main',progress('main',250));await first;
 equal(main.read().data.today,250);equal(notices.length,1);
 equal(notices[0],{project:'main',date:day,goal:200});
 equal(storage.get(events.goalNoticeKey(progress('main',250))),'1');
 // Deleting below target then crossing again cannot create a second notice that day.
 change('main');await reply('main',progress('main',100));
 change('main');await reply('main',progress('main',250));equal(notices.length,1);
 // Goal or diary writes refresh their data but are not a manuscript achievement.
 change('main','goals');await reply('main',progress('main',300,{daily_goal:290}));
 change('main','note');await reply('main',progress('main',300,{daily_goal:290}));equal(notices.length,1);
 // Keep another project subscribed while the first project's request outlives its view.
 const keeper=mount(client,'keeper');await reply('keeper',progress('keeper',0));
 const outstanding=client.refreshWritingProgress('main');main.unmount();change('main');
 await reply('main',progress('main',301,{daily_goal:290}));
 equal(requests.filter(row=>!row.settled&&row.url.includes('/main/')).length,1);
 await reply('main',progress('main',340,{daily_goal:290}));await outstanding;
 main=mount(client,'main');equal(main.read().data.today,340);
 await reply('main',progress('main',360,{daily_goal:290}));equal(main.read().data.today,360);equal(keeper.read().data.today,0);
 // Invalidating a cached but unmounted project clears stale data until the next mount.
 main.unmount();change('main');main=mount(client,'main');equal(main.read().data,null);
 await reply('main',progress('main',370,{daily_goal:290}));equal(main.read().data.today,370);
 // With no visible widgets, no requests or polling continue; reopening always reads fresh metadata.
 main.unmount();keeper.unmount();equal(requests.filter(row=>!row.settled).length,0);
 const count=requests.length;change('main');await flush();equal(requests.length,count);
 main=mount(client,'main');equal(requests.length,count+1);
 await reply('main',progress('main',400,{daily_goal:290}));equal(main.read().data.today,400);equal(notices.length,1);
 main.unmount();equal(requests.filter(row=>!row.settled).length,0);
 console.log(`${checks} LOCAL PASS async writing-cache cases: coalesced save/note, once/day, project isolation, unmount/reopen, and no idle polling. Transport and hooks are deterministic test adapters; no UI or AI verified.`);
}finally{
 for(const [key,descriptor] of originals){if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];}
}
