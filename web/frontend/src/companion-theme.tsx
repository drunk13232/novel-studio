import {useEffect,useState} from 'react';
import {Flower2,Heart,BookOpen,X,Moon} from 'lucide-react';
import {t,useUiTranslation} from './i18n';
import type {ThemeId} from './font-settings';
import {isDarkTheme} from './themes';

type Skin='yoshino'|'rem';
const skinOf=(theme:string):Skin|null=>theme==='yoshino'?'yoshino':theme==='rem'||theme==='rem-night'?'rem':null;
export function nightVariant(theme:ThemeId):ThemeId {
 if(theme==='rem')return 'rem-night';
 if(theme==='rem-night')return 'rem';
 return isDarkTheme(theme)?'moon':'night';
}
export function useAppearance(theme?:string){
 const [current,setCurrent]=useState(()=>document.documentElement.dataset.appearance||'moon');
 useEffect(()=>{if(theme)return;const root=document.documentElement,observer=new MutationObserver(()=>setCurrent(root.dataset.appearance||'moon'));observer.observe(root,{attributes:true,attributeFilter:['data-appearance']});setCurrent(root.dataset.appearance||'moon');return()=>observer.disconnect();},[theme]);
 return theme||current;
}
// The backend resolves only named local slots, never arbitrary URLs or filesystem paths.
type PortraitAsset={url:string|null;status:'ready'|'missing';source:string|null};
type PortraitMap=Partial<Record<Skin,PortraitAsset>>;
let manifestPromise:Promise<PortraitMap>|null=null;
const resourceListeners=new Set<()=>void>();
function loadAssets():Promise<PortraitMap>{
 if(!manifestPromise)manifestPromise=fetch('/api/studio/companion/manifest',{credentials:'same-origin',cache:'no-store'}).then(r=>r.ok?r.json():{}).then((data:{assets?:PortraitMap})=>{
  const result:PortraitMap={};for(const key of ['yoshino','rem'] as const){const item=data?.assets?.[key];if(item?.url&&new RegExp('^/api/studio/companion/'+key+'\\?v=[a-f0-9]{16}$').test(item.url))result[key]=item;}return result;
 }).catch(():PortraitMap=>({}));return manifestPromise;
}
function refreshPortraits(){manifestPromise=null;for(const refresh of resourceListeners)refresh();}
function CompanionPortrait({skin}:{skin:Skin}){
 const [asset,setAsset]=useState<PortraitAsset|null>(null),[failed,setFailed]=useState(false),[revision,setRevision]=useState(0);
 useEffect(()=>{const refresh=()=>setRevision(v=>v+1);resourceListeners.add(refresh);return()=>{resourceListeners.delete(refresh);};},[]);
 useEffect(()=>{let live=true;setAsset(null);setFailed(false);void loadAssets().then(assets=>{if(live)setAsset(assets[skin]||null);});return()=>{live=false};},[skin,revision]);
 return <div className={'companion-portrait '+skin} data-portrait={asset&&!failed?'loaded':'placeholder'}>{asset?.url&&!failed?<img src={asset.url} alt={t('settings:companionPortraitAlt',{name:t('settings:companionName_'+skin)})} loading="lazy" decoding="async" onError={()=>setFailed(true)}/>:<div className="companion-placeholder"><svg viewBox="0 0 100 180" aria-hidden="true"><circle cx="50" cy="28" r="17"/><path d="M32 51Q50 43 68 51L81 111 66 117 62 159 53 169 50 125 47 169 38 159 34 117 19 111Z"/></svg><strong>{t('settings:companionName_'+skin)}</strong><small>{t('settings:companionMissingPortrait')}</small></div>}</div>;
}
export function CompanionMark({theme}:{theme:string}){
 const skin=skinOf(theme);useUiTranslation('settings');if(!skin)return null;
 return <span className="companion-mark" title={t('settings:companionVisualOnly')}>{skin==='yoshino'?<Flower2 size={15}/>:<Heart size={14}/>}<span>{t('settings:companionName_'+skin)}</span></span>;
}
export function CompanionCard({theme,variant='desk'}:{theme?:string;variant?:'welcome'|'desk'|'assistant'|'scene'}){
 const current=useAppearance(theme),skin=skinOf(current),[dismissed,setDismissed]=useState(false);useUiTranslation('settings');
 useEffect(()=>setDismissed(false),[current]);if(!skin)return null;
 if(dismissed)return <button className="companion-restore" onClick={()=>setDismissed(false)}>{t('settings:showCompanion',{name:t('settings:companionName_'+skin)})}</button>;
 return <aside className={'companion-card companion-'+variant} aria-label={t('settings:companionLabel')}><CompanionPortrait skin={skin}/><div className="companion-copy"><span className="companion-eyebrow">{t('settings:companionName_'+skin)} · {t('settings:companionLabel')}</span><strong>{t('settings:companionTitle_'+(variant==='welcome'?skin:variant))}</strong><p>{t('settings:companionText_'+(variant==='welcome'?skin:variant))}</p><button className="companion-dynamic-entry" onClick={()=>window.dispatchEvent(new CustomEvent("novel-companion-open",{detail:{character:skin}}))}>{t("settings:l2d_title")}</button></div>{<button className="companion-dismiss" onClick={()=>setDismissed(true)} aria-label={t('settings:hideCompanion')}><X size={13}/></button>}{variant==='welcome'&&<span className="companion-welcome-symbol" aria-hidden="true">{current==='rem-night'?<Moon size={36} strokeWidth={1}/>:<BookOpen size={36} strokeWidth={1}/>}</span>}</aside>;
}
export function CompanionResources({theme}:{theme:string}){
 useUiTranslation('settings');return <details className="companion-resource-help"><summary>{t('settings:companionResources')}</summary><p>{t('settings:companionResourceHelp')}</p><p>{t('settings:companionVisualOnly')}</p><code>companion/manifest.json</code><button onClick={refreshPortraits}>{t('settings:reloadPortraits')}</button><p>{t('settings:companionLocalOnly')}</p><CompanionCard theme={theme} variant="scene"/></details>;
}


