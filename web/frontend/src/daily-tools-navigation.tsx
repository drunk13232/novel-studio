import {useState} from 'react';
import {ArrowLeft,ChartNoAxesCombined,Search,Network,Timer,Info} from 'lucide-react';
import {StudioDialog} from './studio-dialog';
import {t,useUiTranslation} from './i18n';
import './daily-tools-navigation.css';
const tr=(key:string,values?:Record<string,unknown>)=>t('navigation:dailyTools.'+key,values);
const items=[{page:'statistics',key:'dashboard',Icon:ChartNoAxesCombined},{page:'replace',key:'replace',Icon:Search},{page:'clues',key:'clues',Icon:Network}];
export function DailyToolsNavigation({page,chapterLabel,onNavigate}:{page:string;chapterLabel?:string;onNavigate:(page:string)=>void}){
 useUiTranslation('navigation');const[help,setHelp]=useState(false);
 return <div className="daily-tools-navigation"><nav aria-label={tr('label')}><button type="button" className="daily-tools-back" disabled={!chapterLabel} title={chapterLabel?tr('backHelp'):tr('noChapter')} onClick={()=>onNavigate('write')}><ArrowLeft size={14} aria-hidden="true"/><span>{chapterLabel?tr('back',{chapter:chapterLabel}):tr('noChapter')}</span></button><div className="daily-tools-switches">{items.map(({page:target,key,Icon})=><button type="button" key={target} disabled={page===target} aria-current={page===target?'page':undefined} onClick={()=>onNavigate(target)}><Icon size={14} aria-hidden="true"/>{tr(key)}</button>)}<button type="button" onClick={()=>onNavigate('focusTools')}><Timer size={14} aria-hidden="true"/>{tr('focus')}</button></div><button type="button" className="daily-tools-help" onClick={()=>setHelp(true)}><Info size={14} aria-hidden="true"/>{tr('help')}</button></nav>{help&&<StudioDialog title={tr('helpTitle')} className="daily-tools-help-dialog" onClose={()=>setHelp(false)}><p>{tr('helpIntro')}</p><dl>{['dashboard','focus','replace','clues','wellbeing'].map(key=><div key={key}><dt>{tr(key)}</dt><dd>{tr('help_'+key)}</dd></div>)}</dl><div className="daily-tools-keyboard">{['replaceKey','searchKey','returnKey','saveKey','focusKey'].map(key=><p key={key}>{tr(key)}</p>)}</div><p className="muted">{tr('helpSafety')}</p></StudioDialog>}</div>;
}
