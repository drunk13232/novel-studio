import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'vite';
import react from '@vitejs/plugin-react';
import {chromium} from 'playwright';
// Real production chart with synthetic values; no model/transport adapter or native UI.
const frontend=fileURLToPath(new URL('..',import.meta.url)),engine=path.resolve(frontend,'../..');
const index=process.argv.indexOf('--output');assert(index>=0,'Use --output with a new private-checks directory');
const output=path.resolve(process.argv[index+1]);assert(output.startsWith(path.join(engine,'docs')+path.sep)&&output.includes('private-checks'));
const labels=JSON.parse(await readFile(path.join(frontend,'public/locales/zh-CN/insights.json'),'utf8'));
const entry=`import React from 'react';import{createRoot}from'react-dom/client';import InsightChart from ${JSON.stringify(path.join(frontend,'src/insight-chart.tsx').replaceAll('\\','/'))};import i18n from ${JSON.stringify(path.join(frontend,'src/i18n.tsx').replaceAll('\\','/'))};
await i18n.init({lng:'zh-CN',resources:{'zh-CN':{insights:${JSON.stringify(labels)}}},defaultNS:'insights',interpolation:{escapeValue:false}});
const rows=Array.from({length:500},(_,i)=>({id:'sample_'+i,label:String(i+1),book:i%43===0?null:5+3*Math.sin(i/18),hero:4+2*Math.cos(i/15),track:i%79<3?null:6+2*Math.sin(i/11)}));
const start=performance.now();createRoot(document.getElementById('root')).render(React.createElement(InsightChart,{rows,series:[{id:'book',name:'全书'},{id:'hero',name:'示例人物'},{id:'track',name:'示例剧情线'}],metric:'tension',onChapter:id=>{window.__selectedChapter=id;}}));
requestAnimationFrame(()=>requestAnimationFrame(()=>{window.__sample={chapters:rows.length,firstPaintMs:performance.now()-start};}));`;
const bundle=await build({root:frontend,configFile:false,logLevel:'error',publicDir:false,plugins:[react(),{name:'isolated-chart-entry',resolveId:id=>id==='virtual:insight-sample'?'\0insight-sample.tsx':undefined,load:id=>id==='\0insight-sample.tsx'?entry:undefined}],build:{write:false,target:'es2022',minify:true,rollupOptions:{input:'virtual:insight-sample',output:{format:'es',inlineDynamicImports:true}}}});
const chunks=(Array.isArray(bundle)?bundle:[bundle]).flatMap(item=>item.output);const js=chunks.filter(item=>item.type==='chunk').map(item=>item.code).join('\n');assert(js.length>10000);
const css=chunks.filter(item=>item.type==='asset'&&item.fileName.endsWith('.css')).map(item=>String(item.source)).join('\n');
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,chromiumSandbox:true,args:['--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--no-first-run','--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=<-loopback>']});
try{
 const context=await browser.newContext({viewport:{width:1100,height:470},reducedMotion:'reduce',serviceWorkers:'block'});let requests=0;await context.route('**/*',route=>{requests++;return route.abort();});
 const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setContent('<!doctype html><html><head><style>:root{--accent:#216c68;--line:#ddd6c9;--muted:#64706d;--ink:#213b3c;--surface:#fffdf8}body{background:#fffdf8;color:#213b3c;padding:24px;font:14px sans-serif}#root{width:100%;min-height:380px}</style></head><body><div id="root"></div></body></html>');
 if(css)await page.addStyleTag({content:css});await page.addScriptTag({type:'module',content:js});
 await page.waitForFunction(()=>window.__sample&&document.querySelectorAll('.recharts-line-curve').length===3);
 const curves=page.locator('.recharts-line-curve');assert.equal(await curves.count(),3);assert.equal(await page.locator('.recharts-line-dots circle').count(),0);
 const area=await page.locator('.recharts-wrapper').boundingBox();assert(area&&area.width>900);
 await page.mouse.move(area.x+area.width*.5,area.y+135);await page.waitForFunction(()=>document.querySelector('.recharts-tooltip-wrapper')?.textContent?.includes('全书'));
 await page.mouse.click(area.x+area.width*.5,area.y+135);await page.waitForFunction(()=>/^sample_\d+$/.test(window.__selectedChapter||''));
 const result=await page.evaluate(()=>({...window.__sample,selectedChapter:window.__selectedChapter,renderedElements:document.querySelectorAll('#root *').length,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches}));
 assert.equal(result.chapters,500);assert(result.renderedElements<1500);assert(result.reducedMotion);assert.equal(requests,0);assert.deepEqual(errors,[]);
 await mkdir(output,{recursive:true});await page.screenshot({path:path.join(output,'chart-500.png')});
 const report={result:'LOCAL_HEADLESS_BROWSER_PASS',scope:'actual React + Recharts InsightChart, synthetic inputs; not desktop or AI',...result,series:3,hover:true,chapter_callback:true,large_series_dots:false,animation_enabled:false,external_requests:requests,page_errors:errors};
 await writeFile(path.join(output,'chart-500.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));await context.close();
}finally{await browser.close();}
