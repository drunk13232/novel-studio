import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import ts from 'typescript';
const dom=new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>');
for(const key of ['window','document','navigator','HTMLElement','Node','Event','MouseEvent'])Object.defineProperty(globalThis,key,{configurable:true,value:dom.window[key]});
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const {createRoot}=await import('react-dom/client');
const jsx=await import('react/jsx-runtime');const icons=await import('lucide-react');
const strings=JSON.parse(await readFile(new URL('../public/locales/zh-CN/navigation.json',import.meta.url),'utf8'));
globalThis.__toolLinks={jsx,icons,t:key=>strings[key.split(':')[1]]||key};
let source=ts.transpileModule(await readFile(new URL('../src/writing-tool-links.tsx',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
source=source.replace(/^import \{([^}]+)\} from ['"]react\/jsx-runtime['"];$/gm,'const {$1}=globalThis.__toolLinks.jsx;').replace(/\b(jsx|jsxs|Fragment) as (_?\w+)/g,'$1:$2').replace(/^import \{([^}]+)\} from ['"]lucide-react['"];$/gm,'const {$1}=globalThis.__toolLinks.icons;').replace(/^import \{[^}]+\} from ['"]\.\/i18n['"];$/gm,'const {t}=globalThis.__toolLinks;const useUiTranslation=()=>{};');
assert(!/^import /m.test(source));
const {WritingToolLinks,matchingToolReturn}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const root=createRoot(document.querySelector('#root'));let checks=0,navigations=[],dismissed=0;
const equal=(a,b)=>{assert.deepEqual(a,b);checks++;};
const path='chapters/chapter-1/draft.txt';const origin={project:'p',page:'replace',path};
equal(matchingToolReturn(null,'p',path),null);equal(matchingToolReturn(origin,'other',path),null);equal(matchingToolReturn(origin,'p','chapters/chapter-2/draft.txt'),null);equal(matchingToolReturn(origin,'p',path),origin);
async function render(props={}){await act(async()=>{root.render(React.createElement(WritingToolLinks,{project:'p',path,focus:false,source:null,onNavigate:page=>navigations.push(page),onDismiss:()=>dismissed++,...props}));});}
async function click(text){const button=[...document.querySelectorAll('button')].find(e=>e.textContent===text||e.getAttribute('aria-label')===text);assert(button,text);await act(async()=>button.dispatchEvent(new MouseEvent('click',{bubbles:true})));}
await render();equal(document.querySelectorAll('nav').length,1);equal(document.querySelectorAll('button').length,2);await click('查找替换');equal(navigations.pop(),'replace');await click('伏笔看板');equal(navigations.pop(),'clues');
await render({source:origin});equal(document.querySelectorAll('button').length,3);await click('返回替换结果');equal(navigations.pop(),'replace');await click('收起返回提示');equal(dismissed,1);
await render({source:origin,project:'q'});equal(document.body.textContent.includes('返回替换结果'),false);
await render({source:origin,path:'chapters/chapter-2/draft.txt'});equal(document.body.textContent.includes('返回替换结果'),false);
await render({focus:true});equal(document.querySelectorAll('nav').length,0);
await render({focus:true,source:origin});equal(document.querySelectorAll('button').length,2);await click('返回替换结果');equal(navigations.pop(),'replace');
for(const page of ['clues','knowledge']){await render({source:{...origin,page}});await click(strings['returnToTool_'+page]);equal(navigations.pop(),page);}
let finds=0;
await render({selection:'春风',onFindSelection:()=>finds++});equal(document.querySelectorAll('button').length,3);await click(strings.selectionSearch);equal(finds,1);
const selectedButton=[...document.querySelectorAll('button')].find(node=>node.textContent===strings.selectionSearch),down=new MouseEvent('mousedown',{bubbles:true,cancelable:true});await act(async()=>selectedButton.dispatchEvent(down));equal(down.defaultPrevented,true,'Selection control preserves the editor focus on mouse-down');
await render({selection:'x'.repeat(301),onFindSelection:()=>finds++});equal([...document.querySelectorAll('button')].find(node=>node.textContent===strings.selectionSearch).disabled,true);await act(async()=>[...document.querySelectorAll('button')].find(node=>node.textContent===strings.selectionSearch).click());equal(finds,1,'An overlong selection never gets silently truncated');
await render({focus:true,selection:'春风',onFindSelection:()=>finds++});equal(document.querySelectorAll('button').length,1);await click(strings.selectionSearch);equal(finds,2);
await render({focus:true,selection:'   ',onFindSelection:()=>finds++});equal(document.querySelectorAll('nav').length,0);
await act(async()=>root.unmount());dom.window.close();delete globalThis.__toolLinks;
console.log(`${checks} LOCAL PASS shipping writing tool buttons, focus visibility, source return and project/file boundaries. In-memory React only; no browser or desktop UI.`);
