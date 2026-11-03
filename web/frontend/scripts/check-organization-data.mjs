import assert from 'node:assert/strict';import ts from 'typescript';import {readFile} from 'node:fs/promises';
const source=ts.transpileModule(await readFile(new URL('../src/organization-data.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {tableCSV,displayValue,fieldValue}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const columns=[{id:'name',name:'名称',type:'text'},{id:'n',name:'数值',type:'number'},{id:'q',name:'质量',type:'quantity'},{id:'b',name:'启用',type:'boolean'}];
const out=tableCSV(columns,[{name:'=SUM(A1)',n:-3,q:{value:0,unit:'kg'},b:false},{name:'带"引号\n换行',n:null,q:null}]);
assert(out.startsWith('\ufeff'));assert(out.includes('"\'=SUM(A1)"'));assert(out.includes('"-3","0","kg","false"'));assert(out.includes('带""引号\n换行'));assert(out.includes('质量 (value)'));assert(out.includes('质量 (unit)'));
for(const name of [' +CMD','@formula','-CMD','\t=1'])assert(tableCSV([{id:'x',name:'x',type:'text'}],[{x:name}]).includes("'"+name));
assert.equal(displayValue(0,'UNKNOWN'),'0');assert.equal(displayValue(false,'UNKNOWN'),'false');assert.equal(displayValue(null,'UNKNOWN'),'UNKNOWN');assert.equal(fieldValue({values:[{id:'x',value_json:'0'}]},'x'),0);assert.equal(fieldValue({values:[{id:'x',value_json:'bad'}]},'x'),null);
console.log('LOCAL PASS: CSV Unicode, quantities, null/zero/false, formula injection and quotes/newlines');
