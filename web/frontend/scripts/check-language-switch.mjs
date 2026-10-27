import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
import i18next from 'i18next';
const source=await readFile(new URL('../src/ui-language-switch.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {activateUiLanguage}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
async function engine(failCore=false){
 const instance=i18next.createInstance();
 instance.use({type:'backend',init(){},read(language,namespace,done){
  if(language==='ar'&&(namespace==='optional-feature'||failCore&&namespace==='common'))return done(new Error('Missing namespace'),null);
  done(null,{label:language==='ar'?'العربية':'English'});
 }});
 await instance.init({lng:'en',fallbackLng:'en',ns:['common','navigation','optional-feature'],defaultNS:'common',initImmediate:false});
 return instance;
}
const complete=await engine();assert.equal(await activateUiLanguage(complete,'ar'),true);assert.equal(complete.language,'ar');assert.equal(complete.t('common:label'),'العربية');assert.equal(complete.t('optional-feature:label'),'English');
const broken=await engine(true);await assert.rejects(activateUiLanguage(broken,'ar'),/UI_LANGUAGE_RESOURCES_UNAVAILABLE/);assert.equal(broken.language,'en');
console.log('Real i18next: optional namespace fallback and core-language failure recovery PASS.');
