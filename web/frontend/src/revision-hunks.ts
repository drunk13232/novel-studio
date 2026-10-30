/** Monaco uses inclusive line ranges and end=0 for empty insertion/deletion ranges.
 * Splice logical lines, including the final empty line, so EOF changes retain newlines. */
export const revisionText=(value:string)=>value.replace(/\r\n?/g,'\n');
export type RevisionHunk={originalStartLineNumber:number;originalEndLineNumber:number;modifiedStartLineNumber:number;modifiedEndLineNumber:number};
export function mergeSelectedHunks(original:string,modified:string,changes:RevisionHunk[],chosen:number[]):string{
 const lines=revisionText(original).split('\n'),replacement=revisionText(modified).split('\n'),selected=new Set(chosen);
 for(let i=changes.length-1;i>=0;i--){
  if(!selected.has(i))continue;
  const c=changes[i],start=c.originalEndLineNumber===0?c.originalStartLineNumber:c.originalStartLineNumber-1;
  const count=c.originalEndLineNumber===0?0:c.originalEndLineNumber-c.originalStartLineNumber+1;
  const insert=c.modifiedEndLineNumber===0?[]:replacement.slice(c.modifiedStartLineNumber-1,c.modifiedEndLineNumber);
  if(start<0||start>lines.length||count<0||start+count>lines.length)throw new Error('Invalid revision range');
  lines.splice(start,count,...insert);
 }
 return lines.join('\n');
}

/** Preserve explicit choices using immutable original-line coverage.
 * New/expanded or ambiguous merged changes require another author choice. */
export function retainHunkChoices(previous:RevisionHunk[],chosen:number[],next:RevisionHunk[]):number[]{
 const span=(h:RevisionHunk):[number,number]|null=>{
  const a=h.originalStartLineNumber,b=h.originalEndLineNumber;
  if(!Number.isSafeInteger(a)||!Number.isSafeInteger(b)||a<0||b<0||b!==0&&(a<1||b<a))return null;
  return b===0?[a,a]:[a-1,b];
 };
 const old=previous.map(span),current=next.map(span),selected=new Set(chosen);
 if(old.some(x=>!x)||current.some(x=>!x))return [];
 const related=([a,b]:[number,number],[c,d]:[number,number])=>a===b?c<=a&&a<=d:c===d?a<=c&&c<=b:Math.max(a,c)<Math.min(b,d);
 return current.flatMap((v,index)=>{
  const [a,b]=v!,touching=old.flatMap((range,i)=>related(v!,range!)?[i]:[]);
  if(!touching.length||touching.some(i=>!selected.has(i)))return [];
  if(a===b)return touching.some(i=>{const [c,d]=old[i]!;return c===d?c===a:c<a&&a<d;})?[index]:[];
  let covered=a;
  for(const range of touching.map(i=>old[i]!).sort((x,y)=>x[0]-y[0])){
   if(range[0]>covered)break;covered=Math.max(covered,range[1]);
  }
  return covered>=b?[index]:[];
 });
}
