export type Row=Record<string,any>;
export function tableCSV(columns:Row[],rows:Row[]):string{
 const expanded:Row[]=columns.flatMap(c=>c.type==='quantity'?[{...c,part:'value',name:c.name+' (value)'},{...c,part:'unit',name:c.name+' (unit)'}]:[{...c,part:''}]);
 const quote=(value:any)=>{let s=value==null?'':typeof value==='object'?JSON.stringify(value):String(value);if(typeof value!=='number'&&/^\s*[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
 return '\ufeff'+[expanded.map(c=>quote(c.name)).join(','),...rows.map(r=>expanded.map(c=>{const v=r[c.id];return quote(c.part?v?.[c.part]:v);}).join(','))].join('\r\n');
}
export function downloadLocal(name:string,body:string,type='application/json'){
 const url=URL.createObjectURL(new Blob([body],{type:type+';charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function fieldDefinition(f:Row):Row{return {...f,children:(f.columns||[]).map((c:Row)=>({...c}))};}
export function fieldValue(record:Row,id:string):any{const f=record.values.find((v:Row)=>v.id===id);try{return f?JSON.parse(f.value_json):null;}catch{return null;}}
export function displayValue(value:any,unknown:string):string{if(value==null||value==='')return unknown;if(typeof value==='object'&&!Array.isArray(value)&&'value'in value)return String(value.value)+' '+value.unit;return typeof value==='object'?JSON.stringify(value):String(value);}
