import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
const source=await readFile(new URL('../src/revision-hunks.ts',import.meta.url),'utf8');
const {outputText}=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
const {mergeSelectedHunks:merge}=await import('data:text/javascript;base64,'+Buffer.from(outputText).toString('base64'));
const h=(a,b,c,d)=>({originalStartLineNumber:a,originalEndLineNumber:b,modifiedStartLineNumber:c,modifiedEndLineNumber:d});
const cases=[
 ['EOF insertion without final newline','a','a\nTAIL',[h(1,0,2,2)],[0],'a\nTAIL'],
 ['EOF insertion after empty last line','a\n','a\n\nTAIL',[h(2,0,3,3)],[0],'a\n\nTAIL'],
 ['delete final line','a\nb','a',[h(2,2,1,0)],[0],'a'],
 ['remove final newline','a\n','a',[h(2,2,1,0)],[0],'a'],
 ['add final newline','a','a\n',[h(1,0,2,2)],[0],'a\n'],
 ['insert first line','a','first\na',[h(0,0,1,1)],[0],'first\na'],
 ['delete first line','first\na','a',[h(1,1,0,0)],[0],'a'],
 ['partial disjoint changes','a\nb\nc','A\nb\nC',[h(1,1,1,1),h(3,3,3,3)],[1],'a\nb\nC'],
 ['all changes match candidate','a\nb\nc','A\nb\nC',[h(1,1,1,1),h(3,3,3,3)],[0,1],'A\nb\nC'],
 ['none preserves source','a\n','A\n',[h(1,1,1,1)],[],'a\n'],
 ['empty source','', '字\n', [h(1,1,1,2)],[0],'字\n'],
 ['replace all with empty','字\n', '',[h(1,2,1,1)],[0],''],
];
for(const [name,a,b,c,d,expected] of cases){assert.equal(merge(a,b,c,d),expected,name);console.log('PASS '+name);}
assert.throws(()=>merge('a','b',[h(9,9,1,1)],[0]));
console.log('13 revision hunk boundary checks passed');
