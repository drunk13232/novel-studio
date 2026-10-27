import i18n from 'i18next';
import HttpBackend from 'i18next-http-backend';
import {initReactI18next,useTranslation} from 'react-i18next';
import {useState} from 'react';
import {activateUiLanguage} from './ui-language-switch';
import {languages,isUiLocale,type UiLocale} from './i18n-locales';
import './i18n.css';
export {languages,isUiLocale};
export function detectLocale(values:readonly string[] = navigator.languages):UiLocale {
 for(const raw of values){
  if(isUiLocale(raw))return raw;
  if(/^zh-(TW|HK|MO|Hant)/i.test(raw))return 'zh-TW';
  if(/^zh/i.test(raw))return 'zh-CN';
  if(/^pt-BR/i.test(raw))return 'pt-BR';
  if(/^pt/i.test(raw))return 'pt-PT';
  const base=raw.split('-')[0];if(isUiLocale(base))return base;
 }
 return 'zh-CN';
}
function applyDirection(code:string){const locale=languages.find(l=>l.code===code);document.documentElement.lang=code;document.title='Novel Studio';document.documentElement.dir=locale?.dir||'ltr';}
export async function initializeI18n(){
 let initial:UiLocale=detectLocale(),resourceVersion='';
 try{const r=await fetch('/api/studio/preferences');if(r.ok){const v=await r.json();resourceVersion=String(v.release?.version||'');if(isUiLocale(v.preferences?.ui_language))initial=v.preferences.ui_language;}}catch{}
 await i18n.use(HttpBackend).use(initReactI18next).init({lng:initial,supportedLngs:languages.map(l=>l.code),load:'currentOnly',fallbackLng:(code)=>code==='en'?['zh-CN']:code==='zh-CN'?['en']:['en','zh-CN'],ns:['common','navigation','errors'],defaultNS:'common',returnEmptyString:false,interpolation:{escapeValue:false},react:{useSuspense:false},backend:{loadPath:import.meta.env.BASE_URL+'locales/{{lng}}/{{ns}}.json',queryStringParams:resourceVersion?{v:resourceVersion}:{},requestOptions:{cache:'no-cache'}},saveMissing:false});
 applyDirection(i18n.language);i18n.on('languageChanged',applyDirection);
}
export function useUiTranslation(ns:string|string[]){return useTranslation(ns,{useSuspense:false});}
export const t=(key:string,options?:Record<string,unknown>)=>String(i18n.exists(key)||options?.defaultValue?i18n.t(key,options as any):i18n.t('common:loading',{defaultValue:'…'}));
export const formatNumber=(n:number,options?:Intl.NumberFormatOptions)=>new Intl.NumberFormat(i18n.language,options).format(n);
export function formatDate(value:string|number|Date,options: Intl.DateTimeFormatOptions={dateStyle:'medium',timeStyle:'short'}){const date=new Date(value);return Number.isNaN(date.valueOf())?t('common:unknown'):new Intl.DateTimeFormat(i18n.language,options).format(date);}
export function formatStoryDate(value:string){const m=value.match(/([+-]\d\d):?(\d\d)$/);const zone=m?`${m[1]}:${m[2]}`:'UTC';try{return new Intl.DateTimeFormat(i18n.language,{dateStyle:'medium',...(/^\d{4}-\d{2}-\d{2}$/.test(value)?{}:{timeStyle:'short' as const}),calendar:'gregory',timeZone:zone}).format(new Date(value));}catch{return value;}}
export function formatBytes(n:number){const units=['byte','kilobyte','megabyte','gigabyte'];const level=Math.min(3,Math.max(0,Math.floor(Math.log(Math.max(n,1))/Math.log(1024))));return new Intl.NumberFormat(i18n.language,{style:'unit',unit:units[level],unitDisplay:'short',maximumFractionDigits:1}).format(n/1024**level);}
export function formatRelative(value:string|number|Date){const seconds=(new Date(value).valueOf()-Date.now())/1000;const unit=Math.abs(seconds)>=86400?'day':Math.abs(seconds)>=3600?'hour':Math.abs(seconds)>=60?'minute':'second';const scale={day:86400,hour:3600,minute:60,second:1}[unit];return new Intl.RelativeTimeFormat(i18n.language,{numeric:'auto'}).format(Math.round(seconds/scale),unit);}
export const changeUiLanguage=(code:UiLocale)=>activateUiLanguage(i18n,code);
export function LanguageSettings({value,aiLanguage,onChange}:{value:string|null;aiLanguage:string;onChange:(values:{ui_language?:UiLocale;ai_response_language?:string})=>void}){
 useUiTranslation('common');const[q,setQ]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const current=value||i18n.language;
 async function select(code:UiLocale){setBusy(true);setError('');try{if(await changeUiLanguage(code))onChange({ui_language:code});}catch{setError(t('common:languageLoadFailed'));}finally{setBusy(false);}}
 return <section className="language-settings type-card"><h3>{t('common:interfaceLanguage')}</h3><p>{t('common:languageNotice')}</p><input aria-label={t('common:searchLanguages')} placeholder={t('common:searchLanguages')} value={q} onChange={e=>setQ(e.target.value)}/><select aria-label={t('common:interfaceLanguage')} value={current} onChange={e=>void select(e.target.value as UiLocale)} disabled={busy}>{languages.filter(l=>l.code===current||(l.name+' '+l.code).toLocaleLowerCase().includes(q.toLocaleLowerCase())).map(l=><option key={l.code} value={l.code} lang={l.code}>{l.name} · {l.status}</option>)}</select>{busy&&<p role="status">{t('common:changingLanguage')}</p>}{error&&<p role="alert">{error}</p>}<small>{t('common:machineReview')}<br/>{t('common:partialNotice')}</small><details><summary>{t('common:contentLanguages')}</summary><p>{t('common:writingLanguageInfo')}</p><label>{t('common:aiResponseLanguage')}<select value={aiLanguage} onChange={e=>onChange({ai_response_language:e.target.value})}><option value="project">{t('common:followProject')}</option>{languages.map(l=><option key={l.code} value={l.code}>{l.name}</option>)}</select></label><p>{t('common:referenceLanguageInfo')}</p></details><a href="/i18n-help/translation-guide.md" target="_blank" rel="noreferrer">{t('common:translationContribution')}</a></section>;
}
export function ProjectLanguageSelect({value,onChange,disabled=false}:{value:string;onChange:(language:UiLocale)=>void;disabled?:boolean}){
 useUiTranslation('common');return <label>{t('common:writingLanguage')}<select aria-label={t('common:writingLanguage')} value={value} disabled={disabled} onChange={e=>onChange(e.target.value as UiLocale)}>{languages.map(l=><option key={l.code} value={l.code}>{l.name}</option>)}</select></label>;
}
export default i18n;

export function formatMoney(value:number,currency:string){try{return new Intl.NumberFormat(i18n.language,{style:'currency',currency,maximumFractionDigits:6}).format(value);}catch{return formatNumber(value,{maximumFractionDigits:6})+' '+currency;}}
