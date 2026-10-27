import {PanelsTopLeft} from 'lucide-react';
import {t,useUiTranslation} from './i18n';
export type WorkspaceView={nav_open:boolean;ai_open:boolean;focus_mode:boolean;nav_width:number;ai_width:number;reference_width:number;referenceOpen:boolean;layout:Record<string,number>};
export type LayoutPreset='writing'|'reference'|'ai'|'focus';
export const layoutPresets:LayoutPreset[]=['writing','reference','ai','focus'];
export function presetView(key:LayoutPreset):WorkspaceView{return {nav_open:key!=='focus'&&key!=='ai',ai_open:key==='ai',focus_mode:key==='focus',nav_width:248,ai_width:330,reference_width:420,referenceOpen:key==='reference',layout:{manuscript:62,reference:38}};}
export function WorkspaceLayout({hasCustom,onApply,onSave,onCustom,onReset}:{hasCustom:boolean;onApply:(key:LayoutPreset)=>void;onSave:()=>void;onCustom:()=>void;onReset:()=>void}){
 useUiTranslation('interaction');
 function close(target:EventTarget){(target as HTMLElement).closest('details')?.removeAttribute('open');}
 return <details className="toolbar-more workspace-layout-menu"><summary aria-label={t('interaction:workspaceLayout')}><PanelsTopLeft size={15}/><span>{t('interaction:layout')}</span></summary><div><small>{t('interaction:layoutHelp')}</small>{layoutPresets.map(key=><button key={key} onClick={event=>{close(event.currentTarget);onApply(key);}}>{t('interaction:layout_'+key)}</button>)}<hr/><button disabled={!hasCustom} onClick={event=>{close(event.currentTarget);onCustom();}}>{t('interaction:restorePersonalLayout')}</button><button onClick={event=>{close(event.currentTarget);onSave();}}>{t('interaction:savePersonalLayout')}</button><button onClick={event=>{close(event.currentTarget);onReset();}}>{t('interaction:resetLayout')}</button></div></details>;
}
