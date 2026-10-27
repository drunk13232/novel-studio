// Local catalog QA, complementary to the official CLI; not a translation engine.
import fs from 'node:fs';import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..'),base=path.join(root,'public/locales');
const localeSource=fs.readFileSync(path.join(root,'src/i18n-locales.ts'),'utf8');
const locales=[...localeSource.matchAll(/"code": "([^"]+)"/g)].map(m=>m[1]);
const namespaces=fs.readdirSync(path.join(base,'zh-CN')).filter(f=>f.endsWith('.json')).map(f=>f.slice(0,-5));
const flat=(v,p='',r={})=>{for(const[k,value]of Object.entries(v)){const key=p?p+'.'+k:k;if(typeof value==='string')r[key]=value;else if(value&&typeof value==='object'&&!Array.isArray(value))flat(value,key,r);else throw Error('Non-text translation '+key);}return r;};
const read=(l,ns)=>flat(JSON.parse(fs.readFileSync(path.join(base,l,ns+'.json'),'utf8')));
const marks=t=>[...t.matchAll(/{{\s*([^}]+?)\s*}}/g)].map(m=>m[1]).sort().join('|');
const plural=/_(zero|one|two|few|many|other)$/;
const reference={};for(const ns of namespaces)reference[ns]={...read('zh-CN',ns),...read('en',ns)};
let failures=[],rows=[];
for(const locale of locales){let total=0,translated=0,missing=0,empty=0,unknown=0;const categories=new Intl.PluralRules(locale).resolvedOptions().pluralCategories;
 for(const ns of namespaces){let values={};try{values=read(locale,ns);}catch(e){failures.push(locale+'/'+ns+': '+e.message);}
  const logical=new Set(Object.keys(reference[ns]).map(k=>k.replace(plural,'')));
  for(const key of logical){total++;const variants=Object.keys(reference[ns]).filter(k=>k.startsWith(key+'_')&&plural.test(k));
   if(variants.length){const actual=categories.map(c=>key+'_'+c);if(actual.every(k=>typeof values[k]==='string'&&values[k].trim()))translated++;else missing++;}
   else if(typeof values[key]==='string'&&values[key].trim())translated++;else missing++;
  }
  for(const[key,value]of Object.entries(values)){
   if(!value.trim())empty++;
   const ref=reference[ns][key]??reference[ns][key.replace(plural,'_other')];
   if(ref===undefined){unknown++;failures.push(locale+'/'+ns+': unknown key '+key);}
   else if(marks(value)!==marks(ref))failures.push(locale+'/'+ns+': placeholder mismatch '+key);
   if(/<script|javascript:|onerror=|<iframe/i.test(value))failures.push(locale+'/'+ns+': executable HTML '+key);
  }
 }
 rows.push({locale,total_keys:total,translated_keys:translated,missing_keys:missing,fallback_keys:missing,coverage: +(100*translated/Math.max(1,total)).toFixed(2),status:'PARTIAL',needs_native_review:locale==='zh-CN'?0:translated,empty_keys:empty,unknown_keys:unknown,plural_categories:categories});
}
const report={scope:'Registered i18next semantic catalog only. Advanced hardcoded UI strings are additional untranslated scope.',framework:'i18next 26.4.3',namespace_count:namespaces.length,locales:rows,failures};
const output=process.argv.find(x=>x.startsWith('--output='))?.slice(9);if(output)fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({namespaces:namespaces.length,locales:rows.length,failures:failures.length,coverage:rows.map(r=>({locale:r.locale,translated:r.translated_keys,total:r.total_keys,percent:r.coverage}))},null,2));
if(failures.length){console.error(failures.slice(0,40).join('\n'));process.exitCode=1;}
