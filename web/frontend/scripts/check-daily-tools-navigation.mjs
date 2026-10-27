import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
const dom=new JSDOM('<!doctype html><html><body><div class="studio"><div id="root"></div></div></body></html>',{url:'http://127.0.0.1/',pretendToBeVisual:true});
for(const key of ['window','document','navigator','HTMLElement','HTMLInputElement','HTMLDivElement','DocumentFragment','Node','NodeFilter','CustomEvent','MutationObserver','Event','MouseEvent'])Object.defineProperty(globalThis,key,{configurable:true,value:dom.window[key]});
globalThis.IS_REACT_ACT_ENVIRONMENT=true;globalThis.getComputedStyle=dom.window.getComputedStyle.bind(dom.window);globalThis.requestAnimationFrame=callback=>setTimeout(()=>callback(0),0);globalThis.cancelAnimationFrame=clearTimeout;
const {createRoot}=await import('react-dom/client');const jsx=await import('react/jsx-runtime');const icons=await import('lucide-react'),Dialog=await import('@radix-ui/react-dialog');
const strings=JSON.parse(await readFile(new URL('../public/locales/zh-CN/navigation.json',import.meta.url),'utf8')),common=JSON.parse(await readFile(new URL('../public/locales/zh-CN/common.json',import.meta.url),'utf8'));
const t=(key,values={})=>{const[ns,path]=key.split(':');return String(path.split('.').reduce((v,p)=>v?.[p],ns==='common'?common:strings)||key).replace(/{{(\w+)}}/g,(_,name)=>String(values[name]??''));};
globalThis.__dailyNav={jsx,React,icons,Dialog,t};
const compile=text=>ts.transpileModule(text,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const jsxImports=text=>text.replace(/^import \{([^}]+)\} from ['"]react\/jsx-runtime['"];$/gm,'const {$1}=globalThis.__dailyNav.jsx;').replace(/\b(jsx|jsxs|Fragment) as (_?\w+)/g,'$1:$2');
let dialog=jsxImports(compile(await readFile(new URL('../src/studio-dialog.tsx',import.meta.url),'utf8'))).replace(/^import \* as Dialog from ['"]@radix-ui\/react-dialog['"];$/gm,'const {Dialog}=globalThis.__dailyNav;').replace(/^import \{[^}]+\} from ['"]\.\/i18n['"];$/gm,'const translateUI=globalThis.__dailyNav.t;const useUiTranslation=()=>{};');
const load=text=>import('data:text/javascript;base64,'+Buffer.from(text).toString('base64'));
assert(!/^import /m.test(dialog));globalThis.__dailyNav.StudioDialog=(await load(dialog)).StudioDialog;
let source=jsxImports(compile(await readFile(new URL('../src/daily-tools-navigation.tsx',import.meta.url),'utf8'))).replace(/^import \{([^}]+)\} from ['"]react['"];$/gm,'const {$1}=globalThis.__dailyNav.React;').replace(/^import \{([^}]+)\} from ['"]lucide-react['"];$/gm,'const {$1}=globalThis.__dailyNav.icons;').replace(/^import \{[^}]+\} from ['"]\.\/i18n['"];$/gm,'const {t}=globalThis.__dailyNav;const useUiTranslation=()=>{};').replace(/^import \{ StudioDialog \} from ['"]\.\/studio-dialog['"];$/gm,'const {StudioDialog}=globalThis.__dailyNav;').replace(/^import ['"]\.\/daily-tools-navigation\.css['"];$/gm,'');
assert(!/^import /m.test(source));const{DailyToolsNavigation}=await load(source);
const root=createRoot(document.querySelector('#root'));let checks=0,opened=[];
const equal=(a,b)=>{assert.deepEqual(a,b);checks++;};
async function render(props={}){await act(async()=>root.render(React.createElement(DailyToolsNavigation,{page:'statistics',chapterLabel:'第八章',onNavigate:page=>opened.push(page),...props})));}
const byText=text=>{const node=[...document.querySelectorAll('button')].find(n=>n.textContent===text||n.getAttribute('aria-label')===text);assert(node,text);return node;};
async function click(text){await act(async()=>byText(text).click());}
try{
 await render();equal(document.querySelector('nav').getAttribute('aria-label'),strings.dailyTools.label);equal(document.querySelectorAll('[aria-current=page]').length,1);equal(byText(strings.dailyTools.dashboard).disabled,true);
 await click(strings.dailyTools.replace);equal(opened.pop(),'replace');await click(strings.dailyTools.clues);equal(opened.pop(),'clues');await click(strings.dailyTools.focus);equal(opened.pop(),'focusTools');await click(t('navigation:dailyTools.back',{chapter:'第八章'}));equal(opened.pop(),'write');
 await click(strings.dailyTools.help);equal(document.querySelectorAll('[role=dialog]').length,1);equal(document.querySelectorAll('[role=dialog] dl>div').length,5);equal(document.querySelector('[role=dialog]').textContent.includes('Ctrl+Shift+H'),true);equal(document.querySelector('[role=dialog]').textContent.includes(strings.dailyTools.helpSafety),true);await click(t('common:closeDialog'));equal(document.querySelectorAll('[role=dialog]').length,0);
 await render({page:'replace',chapterLabel:undefined});equal(byText(strings.dailyTools.noChapter).disabled,true);await click(strings.dailyTools.noChapter);equal(opened.length,0);equal(byText(strings.dailyTools.replace).getAttribute('aria-current'),'page');await click(strings.dailyTools.dashboard);equal(opened.pop(),'statistics');
 await render({page:'clues',chapterLabel:'很长的章节标题'.repeat(60)});equal(byText(strings.dailyTools.clues).disabled,true);await click(t('navigation:dailyTools.back',{chapter:'很长的章节标题'.repeat(60)}));equal(opened.pop(),'write');
 console.log(`${checks} LOCAL PASS production daily-tools navigation and Radix quick guide. No browser/desktop operation or network requests.`);
}finally{await act(async()=>root.unmount());dom.window.close();delete globalThis.__dailyNav;}
