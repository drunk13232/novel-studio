import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
const transpile=source=>ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const metrics=await import('data:text/javascript;base64,'+Buffer.from(transpile(await readFile(new URL('../src/writing-metrics-events.ts',import.meta.url),'utf8'))).toString('base64'));
globalThis.__replacementNavigation=metrics;
const source=transpile(await readFile(new URL('../src/replacement-refresh.ts',import.meta.url),'utf8')).replace(/^import \{ isManuscriptPath \} from ['"]\.\/writing-metrics-events['"];$/m,'const {isManuscriptPath}=globalThis.__replacementNavigation;');
const {replacementRefreshTarget:target}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const a='chapters/chapter-1/draft.txt',b='chapters/chapter-2/final.txt',m='chapters/chapter-2/manual-fixture.txt';
const chapters=[{versions:[{path:a}]},{versions:[{path:b},{path:m}]}];let checks=0;
const same=(actual,expected)=>{assert.deepEqual(actual,expected);checks++;};
same(target(a,[a],chapters),a);
same(target(a,[b],chapters),null); // No unrelated reload or false conflict for unsaved editor A.
same(target(a,[b,m],chapters),null);
same(target(a,[],chapters),null);
same(target(b,[m],chapters),null); // A protected source was not overwritten.
same(target(m,[m],chapters),m);
const afterUndo=[{versions:[{path:a}]},{versions:[{path:b}]}];
same(target(m,[b],afterUndo),b);
same(target(m,[a],afterUndo),null); // No jump to a different chapter after external deletion.
same(target(m,[a,b],afterUndo),b);
same(target('settings/world.md',[a],chapters),null);
same(target('chapters/chapter-2/notes.md',[b],afterUndo),null);
same(target('chapters/story/manual-fixture.txt',['chapters/story/draft.txt'],[{versions:[{path:'chapters/story/draft.txt'}]}]),'chapters/story/draft.txt');
same(target(m,['chapters/chapter-2/nonexistent.txt'],afterUndo),null);
delete globalThis.__replacementNavigation;
console.log(`${checks} LOCAL PASS shipping replacement/editor refresh decisions. No unrelated reload, false conflict, or cross-chapter undo jump.`);
