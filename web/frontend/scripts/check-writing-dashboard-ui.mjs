import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
import {JSDOM} from 'jsdom';

// Actual dashboard React forms and the existing unsaved-form registry in memory.
// Local API responses are fixtures. This is neither a browser/desktop run nor a
// verification of the backend's word-count calculations.
const moduleUrl=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
const dom=new JSDOM('<!doctype html><html><body><div id="dashboard"></div></body></html>',{url:'http://127.0.0.1/',pretendToBeVisual:true});
for(const key of ['window','document','navigator','Node','HTMLElement','Event','CustomEvent','MouseEvent'])Object.defineProperty(globalThis,key,{configurable:true,value:key==='window'?dom.window:dom.window[key]});
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
globalThis.requestAnimationFrame=callback=>setImmediate(()=>callback(0));globalThis.cancelAnimationFrame=clearImmediate;
let intervals=0;window.setInterval=()=>{intervals++;throw Error('Dashboard must not poll');};
const {createElement,act}=await import('react');const {createRoot}=await import('react-dom/client');
const dictionary=JSON.parse(await readFile(new URL('../public/locales/zh-CN/dashboard.json',import.meta.url),'utf8'));
const common={date:'日期',loading:'加载中'};
const translate=(key,options={})=>{const [ns,path]=key.split(':');const row=path.split('.').reduce((value,part)=>value?.[part],ns==='common'?common:dictionary);return String(row??key).replace(/{{(\w+)}}/g,(_match,name)=>String(options[name]??''));};
const requests=[];
globalThis.__dashboardCheck={t:translate,api:(url,body,method='GET')=>new Promise((resolve,reject)=>requests.push({url,body,method,resolve,reject,done:false})),invalidate:project=>window.dispatchEvent(new CustomEvent('novel-writing-metrics-changed',{detail:{project}}))};
const sharedSource=await readFile(new URL('../src/library-shared.tsx',import.meta.url),'utf8');
const registry=sharedSource.slice(sharedSource.indexOf('const unsavedForms='),sharedSource.indexOf('export const base='));assert(registry.includes('export function useUnsavedChanges'));
const sharedUrl=moduleUrl(`import {useEffect,useId} from ${JSON.stringify(import.meta.resolve('react'))};\n${ts.transpileModule(registry,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText}`);const {unsavedMessage}=await import(sharedUrl);
const i18nUrl=moduleUrl("export default {language:'zh-CN'};export const t=globalThis.__dashboardCheck.t;export const useUiTranslation=()=>({ready:true});");
const apiUrl=moduleUrl('export const api=globalThis.__dashboardCheck.api;');
const metricsUrl=moduleUrl('export const invalidateWritingMetrics=globalThis.__dashboardCheck.invalidate;');
const chartUrl=moduleUrl('export default function Chart(){return null;}');
const compiled=ts.transpileModule(await readFile(new URL('../src/writing-statistics.tsx',import.meta.url),'utf8'),{reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});assert.equal(compiled.diagnostics.filter(item=>item.category===ts.DiagnosticCategory.Error).length,0);
let source=compiled.outputText.replace(/^import ['"].+\.css['"];?$/gm,'').replace("import('./writing-chart')",`import(${JSON.stringify(chartUrl)})`);
source=source.replace(/(from\s*['"])([^'"]+)(['"])/g,(_all,left,spec,right)=>left+({'./i18n':i18nUrl,'./api':apiUrl,'./library-shared':sharedUrl,'./writing-metrics-client':metricsUrl}[spec]||import.meta.resolve(spec))+right);
const {WritingStatistics}=await import(moduleUrl(source));
let checks=0;
const equal=(actual,expected,message)=>{assert.deepEqual(actual,expected,message);checks++;};
const flush=async()=>{await act(async()=>{await Promise.resolve();await new Promise(resolve=>setImmediate(resolve));});};
const root=createRoot(document.getElementById('dashboard'));let project='fixture';
const render=async()=>{await act(async()=>root.render(createElement(WritingStatistics,{project,animate:false})));await flush();};
const clone=value=>JSON.parse(JSON.stringify(value));
const snapshot=()=>({project_id:project,form:'short',today:0,week:0,month:0,total_han:0,total_characters:0,completed:0,unfinished:0,chapters:[],volumes:[],quality:{recorded_saves:0},goals:{daily:100,weekly:0,volume:0,book:0,volume_id:''},notes:{'2041-10-03':'已保存的今日记录','2041-10-02':'已保存的昨日记录'},calendar:{start:'2041-10-01',end:'2041-10-03',days:['2041-10-01','2041-10-02','2041-10-03'].map(date=>({date,han:0,manual:0,ai:0,restore:0,unknown:0,save_count:0,level:0,note:date==='2041-10-03'?'已保存的今日记录':date==='2041-10-02'?'已保存的昨日记录':''}))},trend:[],hourly:[],streaks:{current:0,longest:0,writing_days:0,best_day:null},sources:{},pace:{status:'NO_TARGET'}});
const pending=(method='GET')=>{const row=requests.find(row=>!row.done&&row.method===method);assert(row,'No pending '+method+' request');return row;};
async function reply(method,value){const request=pending(method);request.done=true;await act(async()=>request.resolve(clone(value)));await flush();return request;}
async function refresh(value){await act(async()=>window.dispatchEvent(new CustomEvent('novel-writing-metrics-changed',{detail:{project}})));await flush();await reply('GET',value);}
function setInput(node,value){const prototype=node.tagName==='TEXTAREA'?dom.window.HTMLTextAreaElement.prototype:dom.window.HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(prototype,'value').set.call(node,String(value));node.dispatchEvent(new dom.window.Event('input',{bubbles:true}));}
const goalForm=()=>document.querySelector('.wd-goal-settings form');const noteForm=()=>document.querySelector('textarea').closest('form');
const goalInput=()=>goalForm().querySelector('input[type=number]');const noteInput=()=>noteForm().querySelector('textarea');
const button=(label,scope=document)=>{const result=[...scope.querySelectorAll('button')].find(node=>node.textContent===label);assert(result,'Missing button '+label);return result;};
const click=async(label,scope=document)=>{await act(async()=>button(label,scope).click());await flush();};
const edit=async(node,value)=>{await act(async()=>setInput(node,value));await flush();};
const submit=async form=>{await act(async()=>form.dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true})));await flush();};
const wd=dictionary.writingDashboard;
try{
 await render();await reply('GET',snapshot());equal(unsavedMessage(),'');equal(goalInput().value,'100');equal(noteInput().value,'已保存的今日记录');equal(button(dictionary.saveGoals,goalForm()).disabled,true);equal(button(dictionary.saveNote,noteForm()).disabled,true);
 document.querySelector('.wd-goal-settings').open=true;await act(async()=>goalInput().focus());const retained=goalInput();await edit(goalInput(),'5');await edit(goalInput(),'500');equal(document.activeElement,retained);equal(goalInput(),retained);equal(unsavedMessage(),wd.unsavedGoalsLabel);equal(goalForm().textContent.includes(wd.goalsUnsaved),true);
 await refresh(snapshot());equal(goalInput().value,'500','A saved-event refresh preserves unsaved goal input');await click(wd.resetGoals,goalForm());equal(goalInput().value,'100');equal(unsavedMessage(),'');
 await edit(goalInput(),'200');await submit(goalForm());equal(pending('PUT').body.daily,200);equal(unsavedMessage().includes(wd.unsavedGoalsLabel),true);await edit(goalInput(),'300');await reply('PUT',{saved:true});equal(goalInput().value,'300','The save response cannot replace newer goal input');equal(unsavedMessage(),wd.unsavedGoalsLabel);equal(document.body.textContent.includes(wd.earlierSubmissionSaved),true);await click(wd.resetGoals,goalForm());equal(goalInput().value,'200','Reset returns to the last successful submission');equal(unsavedMessage(),'');
 await edit(noteInput(),'今日未保存');equal(unsavedMessage(),wd.unsavedNotesLabel);await act(async()=>document.querySelectorAll('.wd-cells button')[1].click());await flush();equal(noteInput().value,'已保存的昨日记录');await edit(noteInput(),'昨日未保存');equal(document.querySelector('.wd-pending-notes').textContent.includes('2'),true);await click('2041-10-03',document.querySelector('.wd-pending-notes'));equal(noteInput().value,'今日未保存','Changing dates restores the correct draft');
 const latest=snapshot();latest.goals.daily=200;latest.notes['2041-10-03']='后台已保存记录';await refresh(latest);equal(noteInput().value,'今日未保存','A statistics refresh cannot replace a journal draft');await submit(noteForm());equal(pending('PUT').body,{day:'2041-10-03',text:'今日未保存'});await edit(noteInput(),'提交后继续输入');await reply('PUT',{saved:true});equal(noteInput().value,'提交后继续输入');equal(unsavedMessage(),wd.unsavedNotesLabel);equal(document.body.textContent.includes(wd.earlierSubmissionSaved),true);await click(wd.resetNote,noteForm());equal(noteInput().value,'今日未保存');equal(document.querySelector('.wd-pending-notes').textContent.includes('2041-10-02'),true,'Reset affects only the current date');equal(unsavedMessage(),wd.unsavedNotesLabel);
 await click('2041-10-02',document.querySelector('.wd-pending-notes'));equal(noteInput().value,'昨日未保存');await submit(noteForm());await reply('PUT',{saved:true});equal(unsavedMessage(),'');equal(button(dictionary.saveNote,noteForm()).disabled,true);await click(wd.backToToday);equal(noteForm().querySelector('input[type=date]').value,'2041-10-03');equal(noteInput().value,'今日未保存');equal(document.querySelector('.wd-day-detail').textContent.includes('今日未保存'),true,'Successful saves update the displayed stored note immediately');
 await edit(noteInput(),'保存失败的草稿');await submit(noteForm());const failed=pending('PUT');failed.done=true;await act(async()=>failed.reject(Error('隔离保存失败')));await flush();equal(noteInput().value,'保存失败的草稿');equal(unsavedMessage(),wd.unsavedNotesLabel);equal(document.querySelector('[role=alert]').textContent.includes('隔离保存失败'),true);await click(wd.resetNote,noteForm());equal(unsavedMessage(),'');
 // Local form shortcuts must respect HTML validation, IME and in-flight writes.
 const key=async(node,options={})=>{const event=new dom.window.KeyboardEvent('keydown',{key:'s',ctrlKey:true,bubbles:true,cancelable:true,...options});await act(async()=>node.dispatchEvent(event));await flush();return event;};
 await click(wd.setBookGoalNow);equal(document.querySelector('.wd-goal-settings').open,true);equal(document.activeElement.dataset.goal,'book');
 await click(wd.editSelectedNote);equal(document.activeElement,noteInput());
 await edit(goalInput(),'600');const putCount=()=>requests.filter(row=>row.method==='PUT').length;let initialCount=putCount();
 const composing=await key(goalInput(),{isComposing:true});equal(composing.defaultPrevented,false);equal(putCount(),initialCount);
 const modified=await key(goalInput(),{altKey:true});equal(modified.defaultPrevented,false);equal(putCount(),initialCount);
 const savedByKey=await key(goalInput());equal(savedByKey.defaultPrevented,true);equal(putCount(),initialCount+1);equal(pending('PUT').body.daily,600);
 await key(goalInput());equal(putCount(),initialCount+1,'A second key while saving does not duplicate the write');await reply('PUT',{saved:true});equal(unsavedMessage(),'');
 await edit(goalInput(),'-5');initialCount=putCount();await key(goalInput());equal(putCount(),initialCount,'requestSubmit retains numeric constraint validation');await click(wd.resetGoals,goalForm());
 await edit(noteInput(),'快捷保存的日记');equal(document.querySelector('.wd-day-detail').textContent.includes(wd.notePreviewUnsaved),true);equal(document.querySelector('.wd-day-detail').textContent.includes('快捷保存的日记'),true);
 initialCount=putCount();await key(noteInput(),{key:'Enter',ctrlKey:false});equal(putCount(),initialCount,'Plain Enter must remain a text newline');
 const noteShortcut=await key(noteInput(),{key:'Enter'});equal(noteShortcut.defaultPrevented,true);equal(pending('PUT').body.text,'快捷保存的日记');await reply('PUT',{saved:true});equal(unsavedMessage(),'');equal(document.querySelector('.wd-day-detail').textContent.includes(wd.notePreviewUnsaved),false);
 await edit(noteInput(),'Mac 快捷键');await key(noteInput(),{ctrlKey:false,metaKey:true});equal(pending('PUT').body.text,'Mac 快捷键');await reply('PUT',{saved:true});
 const readCount=requests.length;await flush();await flush();equal(requests.length,readCount,'No request is scheduled merely by waiting');equal(intervals,0,'The dashboard never polls');
 project='other_fixture';await render();const other=snapshot();other.notes={};other.calendar.days=other.calendar.days.map(row=>({...row,note:''}));other.goals.daily=0;await reply('GET',other);equal(noteInput().value,'');equal(goalInput().value,'');equal(unsavedMessage(),'','Project changes do not inherit another project’s draft registry');
 await edit(noteInput(),'另一作品草稿');equal(unsavedMessage(),wd.unsavedNotesLabel);await act(async()=>root.unmount());equal(unsavedMessage(),'','Unmount releases only this component’s unsaved registrations');
 console.log(`${checks} LOCAL PASS writing-dashboard form and unsaved-registry checks. Actual React and existing registry, fixture API only; no browser/desktop or real project writes.`);
}finally{try{await act(async()=>root.unmount());}catch{}dom.window.close();}
