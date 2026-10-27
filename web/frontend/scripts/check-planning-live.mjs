import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const frontend=fileURLToPath(new URL('..',import.meta.url)),root=path.resolve(frontend,'../..'),audit=path.join(root,'docs/daily-reliability/private-checks/v2.23.0-20261026');
const connection=JSON.parse(await readFile(path.join(audit,'ui-server.json'),'utf8')),origin=connection.url;
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin));
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--no-first-run']});
const title='隔离计划_'+Date.now();
let page;const errors=[],external=[],calls=[],checks=[];
try{
 const context=await browser.newContext({viewport:{width:1366,height:768},reducedMotion:'reduce',serviceWorkers:'block'});
 await context.route('**/*',route=>{const url=route.request().url();if(url.startsWith(origin+'/'))return route.continue();external.push(new URL(url).origin);return route.abort();});
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()!=='GET')calls.push({url:r.url().replace(origin,''),method:r.method()});});
 await page.goto(origin,{waitUntil:'networkidle'});
 async function planner(){if(await page.locator('.planning-center').count())return;const resume=page.getByRole('button',{name:/继续写作《/});if(await resume.count())await resume.first().click();await page.getByRole('button',{name:'计划中心',exact:true}).first().click();await page.locator('.planning-center h1').waitFor();}
 await planner();checks.push('actual_demo_project_and_plan_entry');
 await page.getByRole('button',{name:'新建计划',exact:true}).first().click();
 const dialog=page.getByRole('dialog');await dialog.getByLabel('计划或目标',{exact:true}).fill(title);
 await dialog.getByLabel('开始日期',{exact:true}).fill('2026-10-26');await dialog.getByLabel('截止日期',{exact:true}).fill('2026-10-30');
 const number=dialog.getByLabel('作者填写的进度',{exact:true});await number.fill('');await number.pressSequentially('25',{delay:40});assert.equal(await number.inputValue(),'25');assert(await number.evaluate(el=>el===document.activeElement));checks.push('continuous_numeric_input_keeps_focus');
 await dialog.getByRole('button',{name:'增加子项',exact:true}).click();await dialog.getByLabel('第 1 个子项',{exact:true}).fill('核对原文证据');
 await dialog.getByRole('button',{name:'保存计划',exact:true}).click();await dialog.waitFor({state:'hidden'});await page.getByRole('button',{name:'全部计划',exact:true}).click();
 await page.getByRole('heading',{name:title,exact:true}).waitFor();checks.push('plan_real_persistence');
 await page.reload({waitUntil:'networkidle'});await planner();await page.getByRole('button',{name:'全部计划',exact:true}).click();await page.getByRole('heading',{name:title,exact:true}).waitFor();checks.push('reload_restores_plan');
 const card=page.locator('.plan-card').filter({has:page.getByRole('heading',{name:title,exact:true})});await card.getByRole('button',{name:'编辑计划',exact:true}).click();
 assert.equal(await dialog.getByLabel('作者填写的进度',{exact:true}).inputValue(),'25');assert.equal(await dialog.getByLabel('第 1 个子项',{exact:true}).inputValue(),'核对原文证据');
 await dialog.getByLabel('开始日期',{exact:true}).fill('');await dialog.getByLabel('截止日期',{exact:true}).fill('');await dialog.getByRole('button',{name:'保存计划',exact:true}).click();await dialog.waitFor({state:'hidden'});
 await page.getByRole('button',{name:'未安排',exact:true}).click();await page.getByRole('heading',{name:title,exact:true}).waitFor();checks.push('reschedule_to_backlog');
 await page.getByRole('button',{name:'日历',exact:true}).click();assert.equal(await page.locator('.plan-month-grid button').count(),42);assert.equal(await page.locator('.plan-weekdays small').count(),7);checks.push('calendar_and_empty_state');
 await page.getByRole('button',{name:'未完成事项',exact:true}).click();await page.getByText('当前已读取范围内没有待处理事项。',{exact:true}).waitFor();checks.push('empty_unfinished_work');
 await page.getByRole('button',{name:'变更影响',exact:true}).click();await page.getByLabel('查找人物、设定或章节',{exact:true}).fill('江予');await page.locator('.plan-impact').getByRole('button',{name:'搜索',exact:true}).click();await page.getByRole('button',{name:'江予 · character',exact:true}).click();await page.locator('.plan-impact h3').filter({hasText:'江予'}).waitFor();checks.push('recorded_impact_with_real_project_data');
 await page.getByRole('button',{name:'正文',exact:true}).first().click();
 if((await page.locator('.manuscript-meta').innerText()).includes('受保护')){checks.push('final_stays_read_only');await page.locator('.chapter-link').filter({hasText:'灯下的回信'}).click();}
 const editor=page.locator('.cm-content[contenteditable="true"]').first();await editor.waitFor();await editor.click();await editor.press('Control+End');await page.keyboard.insertText('\n隔离保存验证：计划不代表事实。');
 const saved=page.waitForResponse(r=>r.request().method()==='PUT'&&r.url().includes('/files/content')&&r.status()===200);await editor.press('Control+s');const response=await saved;assert((await response.json()).content.includes('隔离保存验证：计划不代表事实。'));checks.push('actual_manuscript_save_with_ai_offline');
 await page.reload({waitUntil:'networkidle'});const resume=page.getByRole('button',{name:/继续写作《/});if(await resume.count())await resume.first().click();const reopened=page.locator('.cm-content[contenteditable="true"]').first();await reopened.waitFor();await reopened.click();await reopened.press('Control+End');await page.getByText('隔离保存验证：计划不代表事实。',{exact:false}).first().waitFor();checks.push('manuscript_reopen');
 await planner();await page.getByRole('button',{name:'全部计划',exact:true}).click();await page.screenshot({path:path.join(audit,'planning-live.png')});
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert(!calls.some(v=>/\/(tasks|reply|run|assistant\/sessions)$/.test(v.url)));
 const result={result:'BROWSER_PASS_REAL_LOCAL_BACKEND',checks,external_requests:external,page_errors:errors,viewport:{width:1366,height:768},reduced_motion:true,real_ai:false,native_ime:false};await writeFile(path.join(audit,'browser-live.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}catch(error){await writeFile(path.join(audit,'browser-partial.json'),JSON.stringify({checks,error:String(error),errors,external},null,2));if(page){await page.screenshot({path:path.join(audit,'planning-live-failure.png')}).catch(()=>{});await writeFile(path.join(audit,'browser-failure.txt'),String(error)+'\n'+(await page.locator('body').innerText()).slice(0,16000));}throw error;}finally{await browser.close();}
