import {t as translateUI,useUiTranslation} from './i18n';
import {useEffect,useId,useState,type CSSProperties} from 'react';
import {BookOpen,Type} from 'lucide-react';
import {api} from './api';
export {ThemeGallery as ThemeSettings} from './theme-gallery';
export {isDarkTheme} from './themes';
export type {ThemeId} from './themes';

export type TypographyPreferences={ui_font_family:string;ui_font_size:number;font_family:string;font_size:number;line_height:number;editor_width:number};
const fonts=[
 ['Microsoft YaHei UI','微软雅黑 UI','清晰的界面字形'],
 ['Microsoft YaHei','微软雅黑','适合长时间写作'],
 ['DengXian','等线','简洁均匀'],
 ['SimSun','宋体','传统书页风格'],
 ['NSimSun','新宋体','宋体字形'],
 ['KaiTi','楷体','柔和的手写感'],
 ['FangSong','仿宋','细腻的书卷感'],
 ['SimHei','黑体','醒目的笔画'],
 ['Source Han Serif SC','思源宋体','需本机已安装'],
 ['Source Han Sans SC','思源黑体','需本机已安装'],
 ['Noto Serif SC','Noto 中文宋体','需本机已安装'],
 ['Noto Sans SC','Noto 中文黑体','需本机已安装'],
 ['Segoe UI','Segoe UI','英文界面字体'],
] as const;
export function fontStack(name:string){
 const quoted='"'+name.replace(/[\x00-\x1f\x7f]/g,'').replace(/\\/g,'\\\\').replace(/"/g,'\\"')+'"';
 const serif=/SimSun|Song|Serif|KaiTi|FangSong|宋|楷|仿/.test(name);
 return quoted+', "Segoe UI", "Nirmala UI", "Leelawadee UI", "Tahoma"'+(serif?', "SimSun", "Songti SC", serif':', "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif');
}
type FontInventory={status:'AVAILABLE'|'UNAVAILABLE';families:string[];message:string};
let inventoryRequest:Promise<FontInventory>|null=null;
function loadFonts(refresh=false){if(refresh||!inventoryRequest)inventoryRequest=api<FontInventory>('/api/studio/fonts'+(refresh?'?refresh=true':'')).catch(()=>({status:'UNAVAILABLE' as const,families:[],message:'字体检测暂不可用；使用系统回退。'}));return inventoryRequest;}
const aliases:Record<string,string[]>={'Microsoft YaHei UI':['微软雅黑 UI'],'Microsoft YaHei':['微软雅黑'],'DengXian':['等线'],'SimSun':['宋体'],'NSimSun':['新宋体'],'KaiTi':['楷体'],'FangSong':['仿宋'],'SimHei':['黑体']};
const normalizeFont=(name:string)=>name.normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim();
function FontPicker({label,value,onChange}:{label:string;value:string;onChange:(value:string)=>void}){
 useUiTranslation(["settings","navigation","characters"]);

 const id=useId(),[inventory,setInventory]=useState<FontInventory|null>(null),[custom,setCustom]=useState(!fonts.some(f=>f[0]===value)),[draft,setDraft]=useState(value),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 const available=new Set((inventory?.families||[]).map(normalizeFont));
 const detected=(name:string)=>[name,...(aliases[name]||[])].some(n=>available.has(normalizeFont(n)));
 const known=(name:string)=>fonts.some(f=>f[0]===name)||(inventory?.families||[]).includes(name);
 useEffect(()=>{let live=true;void loadFonts().then(v=>{if(live){setInventory(v);setLoading(false);}});return()=>{live=false};},[]);
 useEffect(()=>{setCustom(!known(value));setDraft(value);setError('');},[value]);
 function apply(){const name=draft.trim();if(!name||name.length>120||/[\x00-\x1f\x7f]/.test(name)){setError(translateUI("settings:localFontNameValidation"));return;}onChange(name);setError('');}
 const status=loading?'正在读取本机字体…':inventory?.status==='AVAILABLE'?(detected(value)?'已检测到本机字体':'未检测到此名称；可能使用别名字体或系统回退'):inventory?.message;
 return <div className="font-picker"><label htmlFor={id}>{label}</label><select id={id} aria-label={label} value={custom?'__custom__':value} onChange={e=>{if(e.target.value==='__custom__'){setCustom(true);setDraft(value);}else{setCustom(false);onChange(e.target.value);}setError('');}}><optgroup label={translateUI("settings:commonFonts")}>{fonts.map(([name,title,description])=><option key={name} value={name}>{title} · {inventory?.status==='AVAILABLE'?(detected(name)?'已检测到':'未检测到'):description}</option>)}</optgroup>{inventory?.status==='AVAILABLE'&&<optgroup label={translateUI("settings:otherLocalFonts")}>{inventory.families.filter(n=>!fonts.some(f=>f[0]===n)).map(n=><option key={n} value={n}>{n}</option>)}</optgroup>}<option value="__custom__">{translateUI("settings:customFont")}</option></select>{custom&&<div className="font-custom"><label htmlFor={id+'-custom'}>{translateUI("settings:localFontName")}</label><div><input id={id+'-custom'} value={draft} maxLength={120} placeholder={translateUI("settings:localFontNameExample")} onChange={e=>setDraft(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();apply();}}}/><button type="button" onClick={apply}>{translateUI("settings:applyFont")}</button></div>{error&&<small role="alert">{error}</small>}</div>}<div className="font-availability"><small role="status">{status}</small><button type="button" disabled={loading} onClick={()=>{setLoading(true);void loadFonts(true).then(v=>{setInventory(v);setLoading(false);});}}>{translateUI("settings:refreshFonts")}</button></div><small>{translateUI("settings:localFontPreviewNotice")}</small></div>;
}
export function FontSettings({kind,prefs,onChange}:{kind:'ui'|'writing';prefs:TypographyPreferences;onChange:(delta:Partial<TypographyPreferences>)=>void}){
 useUiTranslation(["settings","navigation","characters"]);

 const ui=kind==='ui';const name=ui?prefs.ui_font_family:prefs.font_family;
 const preview={fontFamily:fontStack(name),fontSize:ui?prefs.ui_font_size: prefs.font_size,lineHeight:ui?1.75:prefs.line_height} as CSSProperties;
 return <section className="type-card"><header>{ui?<Type size={20}/>:<BookOpen size={20}/>}<div><h3>{ui?translateUI("settings:uiFont"):translateUI("settings:bodyAndReadingFont")}</h3><p>{ui?translateUI("settings:interfaceFontUsage"):translateUI("settings:bodyFontUsage")}</p></div></header>{!ui&&<div className="type-presets" role="group" aria-label={translateUI("settings:bodyTypographyPreset")}>{[{name:'舒适阅读',font_size:19,line_height:1.95,editor_width:760},{name:'紧凑编辑',font_size:17,line_height:1.7,editor_width:900},{name:'大字阅读',font_size:24,line_height:2,editor_width:820}].map(({name,...delta})=><button type="button" key={name} onClick={()=>onChange(delta)}>{name}</button>)}</div>}<FontPicker label={ui?'界面字体':'正文字体'} value={name} onChange={value=>onChange(ui?{ui_font_family:value}:{font_family:value})}/>{ui&&<label className="type-range">{translateUI("settings:interfaceFontSize")}<b>{prefs.ui_font_size}px</b><input type="range" aria-label={translateUI("settings:interfaceFontSize")} min={13} max={18} step={1} value={prefs.ui_font_size} onChange={e=>onChange({ui_font_size:+e.target.value})}/></label>}<div className={'type-preview '+(ui?'type-preview-ui':'type-preview-prose')} style={preview}><span className="type-preview-label">{translateUI("settings:livePreview")}</span>{ui?<><strong>{translateUI("settings:studyWritingPreviewTitle")}</strong><p>{translateUI("settings:studyWritingPreviewDescription")}</p><div className="type-preview-tags"><span>{translateUI("navigation:manuscript")}</span><span>{translateUI("characters:profile")}</span><span>{translateUI("settings:preferencesSaved")}</span></div></>:<><p>{translateUI("settings:rainAndFootstepsPreview")}</p><p>{translateUI("settings:timeAndLamplightPreview")}</p><small>{translateUI("settings:punctuationAndNumeralsPreview")}</small></>}</div></section>;
}
