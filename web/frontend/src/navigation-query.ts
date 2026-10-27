/** Local display filtering only; authoritative full-text search stays in SQLite. */
export function chapterMatches(chapter:{number:number;title?:string},query:string){
 const value=query.trim().toLocaleLowerCase();
 if(!value)return true;
 const text=[chapter.title||'',chapter.number,String(chapter.number).padStart(3,'0'),`第${chapter.number}章`,`chapter ${chapter.number}`].join(' ').toLocaleLowerCase();
 return text.includes(value);
}
export function bookMatches(book:{title:string;genre?:string;writing?:{form?:string}},query:string,form=''){
 if(form&&(book.writing?.form||'novel')!==form)return false;
 const text=[book.title,book.genre||''].join(' ').toLocaleLowerCase();
 return query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean).every(value=>text.includes(value));
}
