import {t,useUiTranslation} from './i18n';
import {useState} from 'react';
import {StudioDialog} from './studio-dialog';
import {ObjectActions,type ObjectAction} from './object-actions';
export type DeskTab={key:string;page:string;title:string;path?:string;target?:string;entityType?:string;pinned?:boolean};
export const canReference=(tab:DeskTab)=>!!(tab.path||tab.target)&&['write','card','characters','world','timeline','references','styles','gallery'].includes(tab.page);
export function DeskTabs({tabs,active,dirty,onOpen,onClose,onPin,onCloseOthers,onReopen,onSplit,onMove}:{tabs:DeskTab[];active:string;dirty?:boolean;onOpen:(t:DeskTab)=>void;onClose:(t:DeskTab)=>void;onPin:(t:DeskTab)=>void;onCloseOthers:(t:DeskTab)=>void;onReopen:()=>void;onSplit:(t:DeskTab)=>void;onMove:(t:DeskTab,delta:number)=>void}){
 useUiTranslation(['editor','interaction']);

 const [menu,setMenu]=useState<DeskTab|null>(null);
 function actions(tab:DeskTab):ObjectAction[]{const index=tabs.findIndex(row=>row.key===tab.key);return [
  {id:'open',label:t('interaction:openDocument'),run:()=>onOpen(tab)},
  ...(canReference(tab)?[{id:'split',label:t('editor:openRight'),run:()=>onSplit(tab)}]:[]),
  {id:'pin',label:t(tab.pinned?'editor:unpinWorkspaceTab':'editor:pinWorkspaceTab'),run:()=>onPin(tab)},
  {id:'left',label:t('interaction:moveTabLeft'),disabled:index===0,run:()=>onMove(tab,-1)},
  {id:'right',label:t('interaction:moveTabRight'),disabled:index===tabs.length-1,run:()=>onMove(tab,1)},
  {id:'others',label:t('editor:closeOthers'),run:()=>onCloseOthers(tab)},
  {id:'close',label:t('interaction:closeTab'),disabled:tab.pinned,run:()=>onClose(tab)}
 ];}
 return <div className="desk-tabs"><div role="tablist" aria-label={t('editor:creativeWorkspaceTabs')}>{tabs.map(tab=><ObjectActions key={tab.key} label={tab.title} actions={actions(tab)}><div className={'desk-tab '+(active===tab.key?'active':'')}><button role="tab" aria-selected={active===tab.key} onClick={()=>onOpen(tab)}>{tab.pinned?'◆ ':''}{dirty&&active===tab.key?'● ':''}{tab.title}</button><button aria-label={tab.title+t('interaction:tabActions')} onClick={()=>setMenu(tab)}>···</button>{!tab.pinned&&<button aria-label={t('interaction:closeTabNamed',{title:tab.title})} onClick={()=>onClose(tab)}>×</button>}</div></ObjectActions>)}</div><button aria-label={t('editor:reopenRecentlyClosedTab')} title={t('editor:reopenRecentlyClosedTab')} onClick={onReopen}>↶</button>{menu&&<StudioDialog title={menu.title+t('interaction:tabActions')} onClose={()=>setMenu(null)}><div className="desk-tools">{actions(menu).map(action=><button key={action.id} disabled={action.disabled} onClick={()=>{setMenu(null);action.run();}}>{action.label}</button>)}</div></StudioDialog>}</div>;
}
