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
