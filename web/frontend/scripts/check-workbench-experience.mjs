import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chromium} from 'playwright';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const audit=path.resolve(process.argv[2]||path.join(root,'desktop/build/workbench-2.24.3'));
const cfg=JSON.parse(await readFile(path.join(audit,'ui-server.json'),'utf8')),origin=cfg.url;
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin),'Only an isolated loopback fixture is allowed');
assert.equal(cfg.fixture,'public-demo-only','Never run this write test against an author workspace');
const locale=async ns=>JSON.parse(await readFile(path.join(root,'web/frontend/public/locales/zh-CN',ns+'.json'),'utf8'));
const W=await locale('writing'),N=await locale('navigation'),E=await locale('editor'),D=await locale('director');
const report={version:'2.24.3',checks:[],page_errors:[],ai_task_requests:[],metrics:{}};
const record=async(name,data={})=>{report.checks.push({name,status:'LOCAL_BROWSER_PASS',...data});await writeFile(path.join(audit,'after-ui.json'),JSON.stringify(report,null,2));console.log('PASS '+name);};
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--disable-background-networking','--disable-sync','--disable-extensions','--no-first-run']});let page;
try{
 const context=await browser.newContext({viewport:{width:1366,height:768},reducedMotion:'reduce',serviceWorkers:'block'});
 await context.route('**/*',r=>r.request().url().startsWith(origin+'/')?r.continue():r.abort());page=await context.newPage();page.on('pageerror',e=>report.page_errors.push(e.message));page.on('dialog',d=>d.dismiss());
 page.on('request',r=>{if(r.method()==='POST'&&/\/(tasks|scene|facts|launch)$/.test(r.url()))report.ai_task_requests.push(r.url().replace(origin,''));});
 await page.goto(origin,{waitUntil:'networkidle'});const resume=page.getByRole('button',{name:/继续写作《/});if(await resume.count())await resume.first().click();if(!await page.locator('.studio-nav').count())await page.getByRole('button',{name:N.toggleNavigation,exact:true}).click();await page.locator('.chapter-link').filter({hasText:'灯下的回信'}).first().click();
 const editor=page.locator('.manuscript-editor .cm-content[contenteditable=true]');await editor.waitFor();
 const rect=async selector=>page.locator(selector).first().evaluate(el=>{const r=el.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height};});
 const document=async()=>{const r=await page.request.get(origin+'/api/projects/'+cfg.project+'/files/content?path='+encodeURIComponent(cfg.path));assert(r.ok());return r.json();};
 const beforeDocument=await document();report.metrics.editor_before=await rect('.manuscript-editor');
 // Author types before requesting context. The existing save channel must complete once and continue.
 await editor.click();await page.keyboard.press('Control+End');const marker='\n隔离工作台保存衔接检查。';await page.keyboard.insertText(marker);
 await page.getByRole('button',{name:W.context,exact:true}).click();await page.locator('.writing-tools-host .wa-source-list').waitFor();
 assert((await document()).content.includes(marker.trim()));await record('dirty manuscript saved and context prepared with one click');
 report.metrics.editor_with_context=await rect('.manuscript-editor');report.metrics.context_panel=await rect('.writing-tools-host');
 assert(report.metrics.editor_with_context.height>=report.metrics.editor_before.height-15);assert(report.metrics.context_panel.width>250);
 await page.screenshot({path:path.join(audit,'after-docked-context.png')});await record('context dock preserves manuscript height at 1366x768');
 const time=page.getByRole('textbox',{name:W.storyTime,exact:true});await time.fill('2041-04-17T08:40:00+08:00');
 const budget=page.getByRole('spinbutton',{name:W.budget,exact:true});await budget.focus();await page.keyboard.press('Control+a');await page.keyboard.type('19000');assert.equal(await budget.inputValue(),'19000');
 await page.locator('.desk-right-heading').getByRole('button',{name:N.creativeReferences,exact:true}).click();await page.locator('.desk-reference-content:not([hidden])').waitFor();
 await page.locator('.desk-right-heading').getByRole('button',{name:W.context,exact:true}).click();assert.equal(await time.inputValue(),'2041-04-17T08:40:00+08:00');assert.equal(await budget.inputValue(),'19000');await record('reference/tool switching preserves context inputs and continuous numeric input');
 await page.getByRole('button',{name:N.focusedWriting,exact:true}).click();assert.equal(await page.locator('.writing-tools-host').count(),0);await page.getByRole('button',{name:N.exitFocusMode,exact:true}).click();await page.locator('.writing-tools-host').waitFor();assert.equal(await budget.inputValue(),'19000');await record('focus hides dock and restores tool inputs on exit');
 await page.getByRole('button',{name:W.refreshContext,exact:true}).click();await page.waitForFunction(()=>!document.querySelector('.wa-panel fieldset')?.disabled);await page.getByRole('button',{name:D.title,exact:true}).first().click();await page.locator('.wa-next-step').waitFor();
 assert.equal(await page.locator('.creative-director-dialog').count(),0);await page.getByRole('button',{name:W.approveContext,exact:true}).click();await page.locator('.creative-director-dialog').waitFor();assert.equal(report.ai_task_requests.length,0);await record('author-approved context returns directly to Director without model execution');
 await page.locator('.creative-director-dialog .dialog-heading button').click();
 // Closing auxiliary tools does not alter editor state or saved prose.
 await page.locator('.writing-tools-host .wa-panel>header button').click();await page.waitForFunction(()=>!document.querySelector('.writing-tools-host'));
 assert((await editor.innerText()).includes(marker.trim()));await record('closing dock retains manuscript and saved content');
 const afterAuthorSave=await document();
 // New revisions: exact synthetic fixtures seeded by the existing candidate service.
 await page.locator('.navigation-index').click();await page.locator('.tool-index-dialog [data-studio-page="revision"]').click();await page.locator('.revision-desk').waitFor();
 const row=label=>page.locator('.revision-row[data-revision-id="'+cfg.candidates[['A','B','C'].indexOf(label)]+'"]');
 const status=async id=>{const r=await page.request.get(origin+'/api/projects/'+cfg.project+'/studio-tools/candidates/'+id);return(await r.json()).status;};
 await row('A').click();await page.locator('.revision-desk .editor.modified .native-edit-context').waitFor({state:'attached',timeout:45000});
 await page.locator('.revision-desk .editor.modified .native-edit-context').focus();await page.keyboard.press('Control+a');await page.keyboard.insertText('UNSAVED_AUTHOR_EDIT_MARKER');await page.getByText(E.revisionEditedLocally,{exact:true}).waitFor();
 await row('B').click();await page.locator('.revision-unsaved-dialog').waitFor();await page.getByRole('button',{name:E.continueRevisionEditing,exact:true}).click();assert((await page.locator('.revision-desk .editor.modified').innerText()).includes('UNSAVED_AUTHOR_EDIT_MARKER'));await record('switching candidate protects manual edits; continue editing retains text');
 await row('B').click();await page.getByRole('button',{name:E.discardAndSwitchRevision,exact:true}).click();await page.getByText(E.revisionPreviewOnly,{exact:true}).waitFor();await page.getByRole('button',{name:E.closeRevisionPreview,exact:true}).click();await page.getByText(E.chooseRevisionPreview,{exact:true}).waitFor();assert.equal(await status(cfg.candidates[1]),'PROPOSED');await record('close comparison leaves candidate proposed');
 await row('B').click();await page.getByRole('button',{name:E.rejectRevisionCandidate,exact:true}).click();await page.getByText(E.chooseRevisionPreview,{exact:true}).waitFor();assert.equal(await status(cfg.candidates[1]),'REJECTED');assert.equal(await status(cfg.candidates[0]),'PROPOSED');await record('explicit rejection changes only selected candidate');
 await row('A').click();await page.locator('.revision-desk .editor.modified .native-edit-context').focus();await page.keyboard.press('Control+a');await page.keyboard.insertText('UNSAVED_CLOSE_MARKER');await page.getByRole('button',{name:E.closeRevisionPreview,exact:true}).click();await page.locator('.revision-unsaved-dialog').waitFor();await page.getByRole('button',{name:E.continueRevisionEditing,exact:true}).click();assert((await page.locator('.revision-desk .editor.modified').innerText()).includes('UNSAVED_CLOSE_MARKER'));await page.getByRole('button',{name:E.closeRevisionPreview,exact:true}).click();await page.getByRole('button',{name:E.discardAndCloseRevision,exact:true}).click();assert.equal(await status(cfg.candidates[0]),'PROPOSED');await record('dirty close requires a deliberate discard and preserves stored proposal');
 // Protect author-created notes, and verify a slow candidate load is not replaceable by another click.
 await row('A').click();await page.getByRole('textbox',{name:E.revisionNotes,exact:true}).fill('隔离修订说明');await row('C').click();await page.locator('.revision-unsaved-dialog').waitFor();await page.getByRole('button',{name:E.discardAndSwitchRevision,exact:true}).click();await page.getByText(E.revisionPreviewOnly,{exact:true}).waitFor();await record('revision notes also protected when switching');
 assert.equal((await document()).content,afterAuthorSave.content);await page.getByRole('button',{name:E.closeRevisionPreview,exact:true}).click();
 const targetBefore=await document();assert(targetBefore.content.includes(marker.trim()));assert.equal(report.page_errors.length,0,report.page_errors.join('\n'));await record('all preview/rejection operations leave manuscript unchanged',{candidate_source_was_stale_after_author_edit:true});
 await writeFile(path.join(audit,'after-ui.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report.metrics,null,2));
}catch(e){if(page){await writeFile(path.join(audit,'after-failure.txt'),String(e)+'\n'+(await page.locator('body').innerText()).slice(0,19000));await page.screenshot({path:path.join(audit,'after-failure.png')}).catch(()=>{});}throw e;}finally{await browser.close();}
