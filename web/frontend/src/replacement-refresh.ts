import {isManuscriptPath} from './writing-metrics-events';
/** Resolve only the editor affected by a real replacement receipt. */
export function replacementRefreshTarget(currentPath:string,changedPaths:readonly string[],chapters:readonly {versions:readonly {path:string}[]}[]):string|null {
 if(!isManuscriptPath(currentPath)||!changedPaths.length)return null;
 const available=new Set(chapters.flatMap(chapter=>chapter.versions.map(version=>version.path)));
 if(available.has(currentPath))return changedPaths.includes(currentPath)?currentPath:null;
 // Undo may remove a revision copy. Restore its own source, never an unrelated chapter.
 const folder=currentPath.slice(0,currentPath.lastIndexOf('/')+1);
 return changedPaths.find(path=>isManuscriptPath(path)&&path.startsWith(folder)&&available.has(path))||null;
}
