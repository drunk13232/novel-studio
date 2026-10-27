import {ArrowUpRight,BookOpen,CornerDownRight} from 'lucide-react';
import {t,useUiTranslation} from './i18n';

export function BookshelfReturn({book,onOpen}:{book?:{id:string;title:string;writing?:Record<string,any>;continue_chapter:Record<string,any>|null};onOpen:(id:string)=>void}){
 useUiTranslation('dashboard');
 if(!book)return null;
 const chapter=book.continue_chapter;
 const where=chapter?.kind==='story'?t('dashboard:singleTextBody'):chapter?t('dashboard:returnChapter',{number:chapter.number,title:chapter.title}):t('dashboard:returnProject');
 return <button className="bookshelf-return" onClick={()=>onOpen(book.id)} aria-label={t('dashboard:continueNamed',{title:book.title})}><span className="return-bookmark"><BookOpen size={23}/></span><span className="return-copy"><small>{t('dashboard:returnToDesk')}</small><strong>{book.title}</strong><span><CornerDownRight size={12}/>{where}</span></span><span className="return-open"><ArrowUpRight size={20}/></span></button>;
}
