/** Textareas expose LF-normalized API values; source offsets remain raw UTF-16.
 * Map coordinates without rewriting persisted text or approximating quotations.
 */
export type TextRange={start:number;end:number};
export const textareaValue=(source:string)=>source.replace(/\r\n?/g,'\n');
function integerRange(start:number,end:number,length:number){return Number.isSafeInteger(start)&&Number.isSafeInteger(end)&&0<=start&&start<=end&&end<=length;}
function boundary(source:string,at:number){
 const previous=source.charCodeAt(at-1),next=source.charCodeAt(at);
 return !(previous>=0xd800&&previous<=0xdbff&&next>=0xdc00&&next<=0xdfff)&&!(source[at-1]==='\r'&&source[at]==='\n');
}
/** Map an exact source/report range into the browser's textarea coordinates. */
export function textareaRange(source:string,start:number,end:number):TextRange|null{
 if(!integerRange(start,end,source.length)||!boundary(source,start)||!boundary(source,end))return null;
 let from=start,to=end,pair=source.indexOf('\r\n');
 while(pair>=0&&pair<end){if(pair<start)from--;to--;pair=source.indexOf('\r\n',pair+2);}
 return {start:from,end:to};
}
/** Map an actual visible selection back to the unchanged authoritative source. */
export function sourceRange(source:string,value:string,start:number,end:number):(TextRange&{quote:string})|null{
 if(textareaValue(source)!==value||!integerRange(start,end,value.length))return null;
 function offset(position:number){let at=0,shown=0;while(shown<position){if(source[at]==='\r'&&source[at+1]==='\n')at++;at++;shown++;}return at;}
 const from=offset(start),to=offset(end);if(!boundary(source,from)||!boundary(source,to))return null;
 return {start:from,end:to,quote:source.slice(from,to)};
}
