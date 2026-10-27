/** Resolve existing editor source anchors; all offsets are UTF-16 code units. */
export type DocumentTextLocation={start?:number;end?:number;exact?:string;prefix?:string;suffix?:string;document_revision?:string;evidence?:boolean};
export function locateDocumentText(text:string,hit:DocumentTextLocation,revision?:string,unchanged=false):{from:number;to:number}|null {
 if(typeof hit.exact!=='string')return null;
 if(hit.evidence&&hit.document_revision&&hit.document_revision!==revision)return null;
 const exact=hit.exact,prefix=typeof hit.prefix==='string'?hit.prefix:'',suffix=typeof hit.suffix==='string'?hit.suffix:'';
 const from=hit.start??-1,to=hit.end??-1;
 const context=(start:number,end:number)=>text.slice(Math.max(0,start-prefix.length),start)===prefix&&text.slice(end,end+suffix.length)===suffix;
 const span=Number.isInteger(from)&&Number.isInteger(to)&&from>=0&&to>=from&&to<=text.length;
 if(!exact.length){
  // A deleted match is a caret, not a query. Never search for an empty string.
  return span&&from===to&&unchanged&&!!revision&&hit.document_revision===revision&&context(from,to)?{from,to}:null;
 }
 if(span&&text.slice(from,to)===exact&&context(from,to))return {from,to};
 let found:number|null=null;
 for(let at=text.indexOf(exact);at>=0;at=text.indexOf(exact,at+1)){
  if(!context(at,at+exact.length))continue;
  if(found!==null)return null;
  found=at;
 }
 return found===null?null:{from:found,to:found+exact.length};
}
