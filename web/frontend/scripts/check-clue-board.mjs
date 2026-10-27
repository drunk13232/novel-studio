import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import ts from 'typescript';

// Pure in-memory component interaction checks. No computer/browser UI is operated.
const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>',{url:'http://127.0.0.1/'});
for(const key of ['window','document','navigator','HTMLElement','HTMLInputElement','HTMLTextAreaElement','HTMLSelectElement','HTMLDivElement','DocumentFragment','Node','NodeFilter','CustomEvent','MutationObserver','Event','MouseEvent'])Object.defineProperty(globalThis,key,{configurable:true,value:dom.window[key]});
globalThis.IS_REACT_ACT_ENVIRONMENT=true;globalThis.getComputedStyle=dom.window.getComputedStyle.bind(dom.window);globalThis.requestAnimationFrame=callback=>setTimeout(()=>callback(Date.now()),0);globalThis.cancelAnimationFrame=clearTimeout;
const {createRoot}=await import('react-dom/client');
const jsx=await import('react/jsx-runtime');
const strings=JSON.parse(await readFile(new URL('../public/locales/zh-CN/clues.json',import.meta.url),'utf8'));
const t=(key,options={})=>String(key.split(':').slice(1).join(':').split('.').reduce((value,part)=>value?.[part],strings)||key).replace(/{{(\w+)}}/g,(_,key)=>String(options[key]??''));
const chapters=[{id:'chapter_a',number:1,title:'开端',path:'chapters/chapter-1/draft.txt',volume:'v1',position:0},{id:'chapter_b',number:22,title:'回声',path:'chapters/chapter-22/draft.txt',volume:'v2',position:21}];
const row=(id,name,extra={})=>({id,name,source:'state/foreshadowing.yaml',source_status:'OPEN',archived:false,evidenced_status:'planted',tracking_status:'planted',tracking_is_manual:false,introduced:chapters[0],background:false,actual_recovery:null,recovery_chapter:null,planned_recovery:[],planned_introduction:[],planned_window:{},elapsed_chapters:21,overdue:true,overdue_by:1,note:'',evidence:[],history:[],characters:[],...extra});
let state={etag:'a'.repeat(64),threshold:20,latest_chapter:chapters[1],chapters,volumes:[{id:'v1',number:1,title:'第一卷'},{id:'v2',number:2,title:'第二卷'}],summary:{planted:1,partial:0,recovered:0,planned:1,overdue:1,total:2},clues:[row('key','遗落的钥匙',{evidence:[{id:'anchor_a',kind:'anchor',chapter:chapters[0],located:true,exact:'原文钥匙',source:'metadata/studio/entity-anchors/anchor_a.json',location:{start:8,end:12,text:'原文钥匙',exact:'原文钥匙',prefix:'之前',suffix:'之后',document_revision:'a'.repeat(64)}},{id:'anchor_stale',kind:'anchor',chapter:chapters[1],located:false,exact:'旧引文',source:'metadata/studio/entity-anchors/anchor_stale.json',location:null}]}),row('plan','计划钟声',{evidenced_status:'planned',tracking_status:'planned',introduced:null,elapsed_chapters:null,overdue:false,overdue_by:0,planned_introduction:[chapters[1]]})]};
const writes=[],opened=[],dirtyLabels=new Set();let checks=0,heldWrite=null;
const RadixDialog=await import('@radix-ui/react-dialog');
function applyChange(clue,body){if(body.reset_tracking)Object.assign(clue,{tracking_status:clue.evidenced_status,tracking_is_manual:false});if('tracking_status'in body)Object.assign(clue,{tracking_status:body.tracking_status,tracking_is_manual:true});if('note'in body)clue.note=body.note;if('recovery_chapter_id'in body)clue.recovery_chapter=chapters.find(item=>item.id===body.recovery_chapter_id)||null;}
globalThis.__clueCheck={React,jsx,t,RadixDialog,api:async(url,body,method='GET')=>{
 assert.match(url,/\/workbench\/clue-board(?:\/batch)?$/);
 if(method==='PUT'||method==='POST'){
  if(heldWrite){const gate=heldWrite;heldWrite=null;await gate.promise;}
  writes.push({...structuredClone(body),__method:method});
  if(body.etag!==state.etag)throw Object.assign(new Error('conflict'),{code:'CLUE_BOARD_CHANGED'});
  if(method==='POST'){
   assert.equal(body.confirm,true);assert(body.updates.length<=200);
   const next=structuredClone(state);
   for(const update of body.updates){const clue=next.clues.find(item=>item.id===update.clue_id);assert(clue);applyChange(clue,update);}
   next.etag=String.fromCharCode(97+writes.length).repeat(64);state=next;
   return {...structuredClone(state),batch_summary:{updated:body.updates.length,clue_ids:body.updates.map(item=>item.clue_id)}};
  }
  if('threshold'in body)state.threshold=body.threshold;
  if(body.clue_id)applyChange(state.clues.find(item=>item.id===body.clue_id),body);
  state.etag=String.fromCharCode(97+writes.length).repeat(64);
 }
 return structuredClone(state);
},base:p=>'/api/projects/'+p,usePageState(project,page,key,initial){return React.useState(initial);},useUnsavedChanges(dirty,label){React.useEffect(()=>{if(dirty)dirtyLabels.add(label);return()=>dirtyLabels.delete(label);},[dirty,label]);},ErrorNote:({text})=>text?React.createElement('p',{role:'alert'},text):null,Empty:({text})=>React.createElement('p',{className:'empty'},text)};
let dialogSource=ts.transpileModule(await readFile(new URL('../src/studio-dialog.tsx',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
dialogSource=dialogSource.replace(/^import \{([^}]+)\} from ['"]react\/jsx-runtime['"];$/gm,'const {$1}=globalThis.__clueCheck.jsx;').replace(/\b(jsx|jsxs|Fragment) as (_?\w+)/g,'$1:$2').replace(/^import \* as Dialog from ['"]@radix-ui\/react-dialog['"];$/gm,'const Dialog=globalThis.__clueCheck.RadixDialog;').replace(/^import \{[^}]+\} from ['"]\.\/i18n['"];$/gm,'const translateUI=globalThis.__clueCheck.t;const useUiTranslation=()=>{};');
assert(!/^import /m.test(dialogSource));
globalThis.__clueCheck.StudioDialog=(await import('data:text/javascript;base64,'+Buffer.from(dialogSource).toString('base64'))).StudioDialog;
let source=ts.transpileModule(await readFile(new URL('../src/clue-board.tsx',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
source=source.replace(/^import \{([^}]+)\} from ['"]react\/jsx-runtime['"];$/gm,'const {$1}=globalThis.__clueCheck.jsx;').replace(/\b(jsx|jsxs|Fragment) as (_?\w+)/g,'$1:$2')
.replace(/^import \{([^}]+)\} from ['"]react['"];$/gm,'const {$1}=globalThis.__clueCheck.React;')
.replace(/^import \{([^}]+)\} from ['"]\.\/(?:api|library-shared)['"];$/gm,'const {$1}=globalThis.__clueCheck;')
.replace(/^import \{[^}]+\} from ['"]\.\/i18n['"];$/gm,'const {t}=globalThis.__clueCheck;const useUiTranslation=()=>{};')
.replace(/^import ['"]\.\/clue-board\.css['"];$/gm,'').replace(/^import \{ StudioDialog \} from ['"]\.\/studio-dialog['"];$/gm,'const {StudioDialog}=globalThis.__clueCheck;');
assert(!/^import /m.test(source),'All runtime imports must be explicit local test adapters.');
const {ClueBoard}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const root=createRoot(document.querySelector('#root'));
const settle=()=>new Promise(resolve=>setImmediate(resolve));
const equal=(actual,expected)=>{assert.deepEqual(actual,expected);checks++;};
async function render(project='p'){await act(async()=>{root.render(React.createElement(ClueBoard,{project,onOpen:node=>opened.push(node)}));await settle();});}
const buttons=(scope=document)=>Array.from(scope.querySelectorAll('button'));
const byText=(text,scope=document)=>{const found=buttons(scope).find(element=>element.textContent.includes(text));assert(found,'Missing button '+text);return found;};
async function click(button){await act(async()=>{button.dispatchEvent(new MouseEvent('click',{bubbles:true}));await settle();});}
async function setValue(input,value){const proto=input instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:input instanceof HTMLSelectElement?HTMLSelectElement.prototype:HTMLInputElement.prototype;await act(async()=>{Object.getOwnPropertyDescriptor(proto,'value').set.call(input,value);input.dispatchEvent(new Event(input instanceof HTMLSelectElement?'change':'input',{bubbles:true}));await settle();});}
await render();
equal(document.querySelectorAll('.clue-board-card').length,2);
equal(document.querySelectorAll('.clue-board-card.is-overdue').length,1);
assert(document.body.textContent.includes('计划不是事实'));checks++;
assert(document.body.textContent.includes('尚非事实'));checks++;
// The threshold field keeps focus/node identity across successive keystrokes.
const threshold=document.querySelector('input[type=number]');threshold.focus();
await setValue(threshold,'2');await setValue(threshold,'25');
equal(document.querySelector('input[type=number]'),threshold);equal(document.activeElement,threshold);equal(threshold.value,'25');
assert(dirtyLabels.size>0);checks++;
await click(byText('保存提醒线'));equal(writes.at(-1).threshold,25);equal(dirtyLabels.size,0);
const first=document.querySelector('.clue-board-card');
await click(byText('标记状态与备注',first));
const status=first.querySelector('select');await setValue(status,'partial');
const note=first.querySelector('textarea');await setValue(note,'作者备注：暂不改变正文。');
const recovery=first.querySelectorAll('select')[1];await setValue(recovery,'chapter_b');
await click(byText('保存追踪记录',first));
equal(writes.at(-1).clue_id,'key');equal(writes.at(-1).tracking_status,'partial');equal(writes.at(-1).recovery_chapter_id,'chapter_b');equal(writes.at(-1).note,'作者备注：暂不改变正文。');
assert(document.body.textContent.includes('作者追踪'));checks++;
assert(document.querySelector('[role=status]').textContent.includes('已保存'));checks++;
await click(byText('定位正文证据',first));equal(opened.at(-1).location.start,8);equal(opened.at(-1).location.document_revision,'a'.repeat(64));equal(opened.at(-1).path,chapters[0].path);
await click(byText('打开出处章节',first));equal(opened.at(-1).path,chapters[1].path);equal('location'in opened.at(-1),false);
assert(first.textContent.includes('锚点已经失效'));checks++;
// Search is local and does not issue any write.
await setValue(document.querySelector('input[type=search]'),'计划钟声');equal(document.querySelectorAll('.clue-board-card').length,1);
await setValue(document.querySelector('input[type=search]'),'不存在');assert(document.body.textContent.includes('当前筛选没有结果'));checks++;

// Filtering must not unmount and lose the author's unsaved card inputs.
await setValue(document.querySelector('input[type=search]'),'');
let keyCard=document.querySelector('[data-clue-id="key"]');
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));
await setValue(keyCard.querySelector('textarea'),'筛选后仍须保留的备注');
await setValue(document.querySelector('input[type=search]'),'计划钟声');
equal(document.querySelectorAll('.clue-board-card').length,1);
assert(dirtyLabels.size>0);checks++;
await click(byText('查看未保存修改'));
keyCard=document.querySelector('[data-clue-id="key"]');
equal(keyCard.querySelector('textarea').value,'筛选后仍须保留的备注');
// Discarding a draft is explicit; filter state can be cleared independently.
await click(byText('取消编辑',keyCard));await click(byText('清空筛选'));
equal(dirtyLabels.size,0);
// Volume filtering includes related evidence and plans, without promoting them.
await setValue(document.querySelector('select[aria-label="涉及卷"]'),'v1');equal(document.querySelectorAll('.clue-board-card').length,1);
await setValue(document.querySelector('select[aria-label="涉及卷"]'),'v2');equal(document.querySelectorAll('.clue-board-card').length,2);
await setValue(document.querySelector('select[aria-label="涉及卷"]'),'all');
await setValue(document.querySelector('select[aria-label="排序"]'),'name');
equal(Array.from(document.querySelectorAll('.clue-board-card h3')).map(node=>node.textContent),state.clues.map(item=>item.name).sort((a,b)=>a.localeCompare(b)));
// Two independent drafts: saving one cannot clear the other's pending note.
keyCard=document.querySelector('[data-clue-id="key"]');let planCard=document.querySelector('[data-clue-id="plan"]');
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));if(!planCard.querySelector('textarea'))await click(byText('标记状态与备注',planCard));
await setValue(keyCard.querySelector('textarea'),'准备保存的第一条');await setValue(planCard.querySelector('textarea'),'尚未保存的第二条');
await click(byText('保存追踪记录',keyCard));
equal(planCard.querySelector('textarea').value,'尚未保存的第二条');assert(dirtyLabels.size>0);checks++;
await click(byText('取消编辑',planCard));equal(dirtyLabels.size,0);
// Clearing a manual status override restores source status, keeping notes/links.
keyCard=document.querySelector('[data-clue-id="key"]');const preserved=state.clues.find(item=>item.id==='key').note;
await click(byText('恢复来源状态',keyCard));equal(state.clues.find(item=>item.id==='key').tracking_status,'planted');equal(state.clues.find(item=>item.id==='key').note,preserved);
equal(keyCard.textContent.includes('恢复来源状态'),false);


// Save several drafts in one explicit, object-listed confirmation dialog.
keyCard=document.querySelector('[data-clue-id="key"]');planCard=document.querySelector('[data-clue-id="plan"]');
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));if(!planCard.querySelector('textarea'))await click(byText('标记状态与备注',planCard));
await setValue(keyCard.querySelector('textarea'),'整批第一条备注');await setValue(planCard.querySelector('textarea'),'整批第二条备注');
let beforeBatch=writes.length;await click(byText('确认保存全部草稿'));
let batchDialog=document.querySelector('.clue-batch-dialog');assert(batchDialog);checks++;
equal(batchDialog.querySelectorAll('.clue-batch-list>li').length,2);equal(writes.length,beforeBatch);
assert(batchDialog.textContent.includes('遗落的钥匙')&&batchDialog.textContent.includes('计划钟声'));checks++;
await click(byText('取消，保留草稿与选择',batchDialog));equal(writes.length,beforeBatch);
equal(keyCard.querySelector('textarea').value,'整批第一条备注');equal(planCard.querySelector('textarea').value,'整批第二条备注');
await click(byText('确认保存全部草稿'));batchDialog=document.querySelector('.clue-batch-dialog');await click(byText('确认保存 2 条作者追踪',batchDialog));
equal(writes.length,beforeBatch+1);equal(writes.at(-1).__method,'POST');equal(writes.at(-1).updates.length,2);equal(writes.at(-1).confirm,true);equal(dirtyLabels.size,0);
equal(state.clues.find(item=>item.id==='key').note,'整批第一条备注');equal(state.clues.find(item=>item.id==='plan').note,'整批第二条备注');

// Hidden selections remain explicit, and selected drafts can be saved without the rest.
keyCard=document.querySelector('[data-clue-id="key"]');planCard=document.querySelector('[data-clue-id="plan"]');
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));
if(!planCard.querySelector('textarea'))await click(byText('标记状态与备注',planCard));
await setValue(keyCard.querySelector('textarea'),'只保存这个所选草稿');await setValue(planCard.querySelector('textarea'),'未选草稿必须保留');
const unselectedSavedNote=state.clues.find(item=>item.id==='plan').note;
await click(document.querySelector('[aria-label="选择伏笔：遗落的钥匙"]'));
await setValue(document.querySelector('input[type=search]'),'计划钟声');
assert(document.querySelector('.clue-board-selection').textContent.includes('当前结果 0 条 · 筛选外 1 条'));checks++;
// Add current results must keep the selected clue hidden outside these filters.
await click(byText('加选当前结果'));assert(document.querySelector('.clue-board-selection').textContent.includes('已选 2 条'));checks++;
await click(document.querySelector('[aria-label="选择伏笔：计划钟声"]'));
let beforeSelectedDraft=writes.length;await click(byText('确认保存所选草稿'));
let selectedDraftDialog=document.querySelector('.clue-batch-dialog');
equal(selectedDraftDialog.querySelectorAll('.clue-batch-list>li').length,1);assert(selectedDraftDialog.textContent.includes('遗落的钥匙')&&!selectedDraftDialog.textContent.includes('计划钟声'));checks++;
await click(byText('取消，保留草稿与选择',selectedDraftDialog));equal(writes.length,beforeSelectedDraft);
await click(byText('只看已选'));equal(document.querySelectorAll('.clue-board-card').length,1);equal(document.querySelector('.clue-board-card').dataset.clueId,'key');
await click(byText('确认保存所选草稿'));selectedDraftDialog=document.querySelector('.clue-batch-dialog');await click(byText('确认保存 1 条作者追踪',selectedDraftDialog));
equal(writes.length,beforeSelectedDraft+1);equal(writes.at(-1).updates.map(item=>item.clue_id),['key']);equal(state.clues.find(item=>item.id==='plan').note,unselectedSavedNote);
await click(byText('清空筛选'));planCard=document.querySelector('[data-clue-id="plan"]');equal(planCard.querySelector('textarea').value,'未选草稿必须保留');assert(dirtyLabels.size>0);checks++;
await click(byText('取消编辑',planCard));await click(byText('清除选择'));equal(dirtyLabels.size,0);

// Selected author tracking uses the same guarded batch route; no notes are overwritten.
await click(document.querySelector('[aria-label="选择伏笔：遗落的钥匙"]'));await click(document.querySelector('[aria-label="选择伏笔：计划钟声"]'));
beforeBatch=writes.length;await click(byText('批量调整作者追踪'));batchDialog=document.querySelector('.clue-batch-dialog');
equal(byText('确认保存 2 条作者追踪',batchDialog).disabled,true);equal(writes.length,beforeBatch);
await setValue(batchDialog.querySelector('[aria-label="批量作者追踪状态"]'),'recovered');await setValue(batchDialog.querySelector('[aria-label="批量关联回收章节"]'),'chapter_b');
await click(byText('取消，保留草稿与选择',batchDialog));equal(writes.length,beforeBatch);equal(document.querySelectorAll('.clue-board-select-card input:checked').length,2);
await click(byText('批量调整作者追踪'));batchDialog=document.querySelector('.clue-batch-dialog');
await setValue(batchDialog.querySelector('[aria-label="批量作者追踪状态"]'),'recovered');await setValue(batchDialog.querySelector('[aria-label="批量关联回收章节"]'),'chapter_b');await click(byText('确认保存 2 条作者追踪',batchDialog));
equal(writes.length,beforeBatch+1);equal(writes.at(-1).updates.map(item=>item.clue_id),['key','plan']);equal(writes.at(-1).updates.every(item=>item.tracking_status==='recovered'&&item.recovery_chapter_id==='chapter_b'&&!('note'in item)),true);
equal(state.clues.find(item=>item.id==='key').evidenced_status,'planted');equal(state.clues.find(item=>item.id==='plan').evidenced_status,'planned');
// A selected card with unsaved fields cannot be silently overwritten by batch edits.
keyCard=document.querySelector('[data-clue-id="key"]');if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));await setValue(keyCard.querySelector('textarea'),'未保存时不准批量覆盖');
equal(byText('批量调整作者追踪').disabled,true);await click(byText('取消编辑',keyCard));await click(byText('清除选择'));


// A stale batch confirm is rejected as a whole; edits survive refresh and can be reviewed again.
keyCard=document.querySelector('[data-clue-id="key"]');planCard=document.querySelector('[data-clue-id="plan"]');
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));
if(!planCard.querySelector('textarea'))await click(byText('标记状态与备注',planCard));
await setValue(keyCard.querySelector('textarea'),'冲突后整批第一条');await setValue(planCard.querySelector('textarea'),'冲突后整批第二条');
await click(byText('确认保存全部草稿'));batchDialog=document.querySelector('.clue-batch-dialog');
const previousNotes=state.clues.map(item=>item.note);state.etag='w'.repeat(64);
await click(byText('确认保存 2 条作者追踪',batchDialog));
equal(state.clues.map(item=>item.note),previousNotes);assert(batchDialog.querySelector('[role=alert]').textContent.includes('未覆盖任何修改'));checks++;
await click(byText('保留输入，关闭并刷新数据',batchDialog));equal(document.querySelector('.clue-batch-dialog'),null);
keyCard=document.querySelector('[data-clue-id="key"]');planCard=document.querySelector('[data-clue-id="plan"]');
equal(keyCard.querySelector('textarea').value,'冲突后整批第一条');equal(planCard.querySelector('textarea').value,'冲突后整批第二条');
await click(byText('确认保存全部草稿'));batchDialog=document.querySelector('.clue-batch-dialog');
await click(byText('确认保存 2 条作者追踪',batchDialog));equal(dirtyLabels.size,0);equal(state.clues.map(item=>item.note),['冲突后整批第一条','冲突后整批第二条']);
if(keyCard.querySelector('textarea'))await click(byText('取消编辑',keyCard));
if(planCard.querySelector('textarea'))await click(byText('取消编辑',planCard));
await click(byText('定位出处',keyCard));equal(opened.at(-1).location.start,8);

// A late threshold-save receipt must not erase a newer number typed while waiting.
let releaseThreshold;heldWrite={promise:new Promise(resolve=>{releaseThreshold=resolve;})};
await setValue(document.querySelector('input[type=number]'),'26');await click(byText('保存提醒线'));
await setValue(document.querySelector('input[type=number]'),'27');
await act(async()=>{releaseThreshold();await settle();});
equal(state.threshold,26);equal(document.querySelector('input[type=number]').value,'27');
await setValue(document.querySelector('input[type=number]'),'26');equal(dirtyLabels.size,0);

// A concurrent saved record is visible after refresh; the local draft survives.
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));await setValue(keyCard.querySelector('textarea'),'冲突时保留本地输入');
state.clues.find(item=>item.id==='key').note='其他操作保存的最新备注';state.etag='z'.repeat(64);
await click(byText('保存追踪记录',keyCard));
assert(document.querySelector('[role=alert]').textContent.includes('未覆盖任何修改'));checks++;
equal(state.clues.find(item=>item.id==='key').note,'其他操作保存的最新备注');
await click(document.querySelector('.clue-board-refresh'));
keyCard=document.querySelector('[data-clue-id="key"]');equal(keyCard.querySelector('textarea').value,'冲突时保留本地输入');
assert(keyCard.textContent.includes('这条追踪的已保存记录已经变化'));checks++;
await click(byText('取消编辑',keyCard));
if(!keyCard.querySelector('textarea'))await click(byText('标记状态与备注',keyCard));equal(keyCard.querySelector('textarea').value,'其他操作保存的最新备注');
await click(byText('取消编辑',keyCard));


// If a clue is removed elsewhere, keep the note copyable and explicitly discardable.
planCard=document.querySelector('[data-clue-id="plan"]');if(!planCard.querySelector('textarea'))await click(byText('标记状态与备注',planCard));
await setValue(planCard.querySelector('textarea'),'源线索移除后也不能静默丢弃');
state.clues=state.clues.filter(item=>item.id!=='plan');state.etag='y'.repeat(64);
await click(byText('刷新数据'));
equal(document.querySelector('.clue-board-orphan textarea').value,'源线索移除后也不能静默丢弃');
assert(dirtyLabels.size>0);checks++;
const writeCountBeforeDiscard=writes.length;await click(byText('丢弃这条本页草稿'));
equal(document.querySelectorAll('.clue-board-orphan').length,0);equal(dirtyLabels.size,0);equal(writes.length,writeCountBeforeDiscard);

state={...state,etag:'f'.repeat(64),clues:[],chapters:[],latest_chapter:null,summary:{total:0,overdue:0}};
await render('new-empty-project');assert(document.body.textContent.includes('还没有伏笔或线索'));checks++;

// Real component boundary: 201 pending drafts require an explicit selected subset,
// rather than silent auto-splitting or forcing every draft through individual saves.
state={...state,etag:'m'.repeat(64),clues:Array.from({length:201},(_,index)=>row('bulk_'+String(index).padStart(3,'0'),'批量草稿 '+String(index).padStart(3,'0'))),summary:{planted:201,partial:0,recovered:0,planned:0,overdue:201,total:201}};
await render('many-drafts-project');
for(let index=0;index<201;index++){
 const id='bulk_'+String(index).padStart(3,'0');await setValue(document.querySelector('input[type=search]'),id);
 const card=document.querySelector('[data-clue-id="'+id+'"]');if(!card.querySelector('textarea'))await click(byText('标记状态与备注',card));await setValue(card.querySelector('textarea'),'独立保留草稿 '+index);
}
equal(byText('确认保存全部草稿').disabled,true);
equal(state.clues.filter(item=>item.note).length,0); // Local drafts have not mutated the transport store.
await click(document.querySelector('[aria-label="选择伏笔：批量草稿 200"]'));
const beforeLargeSubset=writes.length;await click(byText('确认保存所选草稿'));
const largeDialog=document.querySelector('.clue-batch-dialog');equal(largeDialog.querySelectorAll('.clue-batch-list>li').length,1);equal(writes.length,beforeLargeSubset);
await click(byText('确认保存 1 条作者追踪',largeDialog));
equal(writes.length,beforeLargeSubset+1);equal(writes.at(-1).updates.length,1);equal(writes.at(-1).updates[0].clue_id,'bulk_200');
equal(byText('确认保存全部草稿').disabled,false);assert(document.querySelector('.clue-board-draft-banner').textContent.includes('200 条'));checks++;
equal(state.clues.filter(item=>item.note).length,1);assert(dirtyLabels.size>0);checks++;

await act(()=>root.unmount());dom.window.close();delete globalThis.__clueCheck;
console.log(`${checks} LOCAL PASS clue-board component checks: source/plan separation, overdue display, focus/input, tracking save, UTF-16 source callback, stale-anchor fallback, search, volume/sort, drafts retained across filters, multi-card edits, atomic-batch UI confirmation/cancel, selected edits/drafts, hidden selection counts, 201-draft subset boundary, reset override, conflict/refresh and empty project. This is jsdom, not browser or desktop UI verification.`);

