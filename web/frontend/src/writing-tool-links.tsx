import {ArrowLeft,Search,Network,X,TextSearch} from 'lucide-react';
import {t,useUiTranslation} from './i18n';
export type WritingToolReturn={project:string;path:string;page:'replace'|'clues'|'knowledge'|'plans'};
export function matchingToolReturn(source:WritingToolReturn|null,project:string,path:string):WritingToolReturn|null{
 return source?.project===project&&source.path===path?source:null;
}
export function WritingToolLinks({project,path,focus,source,onNavigate,onDismiss,selection,onFindSelection}:{project:string;path:string;focus:boolean;source:WritingToolReturn|null;onNavigate:(page:string)=>void;onDismiss:()=>void;selection?:string;onFindSelection?:()=>void}){
 useUiTranslation('navigation');
 const back=matchingToolReturn(source,project,path),hasSelection=!!selection?.trim()&&!!onFindSelection;
 if(focus&&!back&&!hasSelection)return null;
 return <nav className="writing-tool-links" aria-label={t('navigation:writingToolsQuick')}>
  {back&&<span className="writing-tool-return"><button type="button" onClick={()=>onNavigate(back.page)} title={t('navigation:returnToToolHelp')}><ArrowLeft size={13} aria-hidden="true"/>{t('navigation:returnToTool_'+back.page)}</button><button type="button" className="writing-tool-dismiss" onClick={onDismiss} aria-label={t('navigation:dismissToolReturn')}><X size={12} aria-hidden="true"/></button></span>}
  {hasSelection&&<button type="button" disabled={selection!.length>300} title={t(selection!.length>300?'navigation:selectionSearchTooLong':'navigation:selectionSearchHelp')} onMouseDown={event=>event.preventDefault()} onClick={onFindSelection}><TextSearch size={13} aria-hidden="true"/>{t('navigation:selectionSearch')}</button>}
  {!focus&&<><button type="button" onClick={()=>onNavigate('plans')}>{t('navigation:planningCenter')}</button>{back?.page!=='replace'&&<button type="button" onClick={()=>onNavigate('replace')} title={t('navigation:replaceQuickHelp')}><Search size={13} aria-hidden="true"/>{t('navigation:replaceQuick')}</button>}{back?.page!=='clues'&&<button type="button" onClick={()=>onNavigate('clues')} title={t('navigation:cluesQuickHelp')}><Network size={13} aria-hidden="true"/>{t('navigation:cluesQuick')}</button>}</>}
 </nav>;
}
