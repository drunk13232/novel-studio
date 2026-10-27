import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import {chromium} from 'playwright';
const engine=fileURLToPath(new URL('../../..',import.meta.url));
const source=await readFile(new URL('../src/writing-annual.tsx',import.meta.url),'utf8');
const ast=ts.createSourceFile('writing-annual.tsx',source,ts.ScriptTarget.ES2022,true,ts.ScriptKind.TSX);
const paint=ast.statements.find(node=>ts.isFunctionDeclaration(node)&&node.name?.text==='paintAnnualShare');assert(paint);
const built=ts.transpileModule(paint.getText(ast),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText.replace(/^export /m,'');
const labels=JSON.parse(await readFile(new URL('../public/locales/zh-CN/annual.json',import.meta.url),'utf8'));
const sourceRow=(net,saves)=>({net_han:net,added_han:Math.max(0,net),deleted_han:Math.max(0,-net),save_count:saves});
const report={year:2026,start:'2026-01-01',end:'2026-10-25',totals:{manual_han:12840,ai_han:320,restore_han:-24,unknown_han:0},sources:{manual:sourceRow(12840,90),ai:sourceRow(320,3),restore:sourceRow(-24,1),unknown:sourceRow(0,0)},streaks:{writing_days:46,longest:9,best_day:{date:'2026-09-12',han:2100}},months:Array.from({length:12},(_,i)=>({month:i+1,net_han:[600,900,1200,1500,700,1900,1800,1600,2100,-164,0,0][i]}))};
const large=process.argv.includes('--large');if(large){report.totals.manual_han=888888888888888;report.totals.ai_han=99999999999999;}
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,chromiumSandbox:true,args:['--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--no-first-run','--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=<-loopback>']});
try{const context=await browser.newContext({viewport:{width:1100,height:1320},serviceWorkers:'block'});let external=0;await context.route('**/*',route=>{external++;return route.abort();});const page=await context.newPage();await page.setContent('<!doctype html><html><body style="margin:0"><canvas id="card"></canvas></body></html>');
 await page.addScriptTag({content:`const num=value=>value.toLocaleString('zh-CN');const signed=value=>(value>0?'+':'')+num(value);${built}`});
 const data=await page.evaluate(({report,labels})=>{const translate=(key,values={})=>String(labels[key]||key).replace(/{{(\w+)}}/g,(_,name)=>String(values[name]??''));const canvas=document.getElementById('card');paintAnnualShare(canvas,report,{penName:report.totals.manual_han>1e12?'这是很长的演示作者名字'.repeat(8):'演示作者',bookTitle:report.totals.manual_han>1e12?'大数字与长名称排版测试'.repeat(8):'山间来信 · 合成示例'},translate);return canvas.toDataURL('image/png');},{report,labels});
 assert(data.startsWith('data:image/png;base64,'));const png=Buffer.from(data.split(',')[1],'base64');assert.equal(png.readUInt32BE(16),1080);assert.equal(png.readUInt32BE(20),1280);assert.equal(external,0);
 const outputIndex=process.argv.indexOf('--output');const output=outputIndex>=0?path.resolve(process.argv[outputIndex+1]):path.join(engine,'docs/daily-writing-ritual/private-checks/annual-share-local.png');assert(output.startsWith(path.join(engine,'docs')+path.sep)&&output.endsWith('.png'));await mkdir(path.dirname(output),{recursive:true});await writeFile(output,png);console.log(JSON.stringify({result:'LOCAL HEADLESS CANVAS PASS',output,width:1080,height:1280,bytes:png.length,external_requests:external,native_ui:'NOT RUN',data:'synthetic fixtures only'}));await context.close();
}finally{await browser.close();}
