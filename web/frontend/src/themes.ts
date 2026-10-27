import type {CSSProperties} from 'react';

// Shared semantic tokens are used by the app and the live component previews.
// Images are URLs, not eagerly imported image data; only visible artwork loads.
export const themeIds=['moon','mist','night','amber','sky','plum','yoshino','rem','rem-night','manuscript','ink','observatory','gothic','cyber','greenhouse','minimal'] as const;
export type ThemeId=typeof themeIds[number];
export type ThemeFamily='study'|'botanical'|'companion'|'archive'|'ink'|'astral'|'gothic'|'technical'|'minimal';
export type ThemeCustomization={name?:string;accent?:string|null;ink?:string|null;background?:string|null;radius?:number|null;decoration?:number;texture?:number;motion?:number;density?:'comfortable'|'compact'};
export type ThemePreview={appearance:ThemeId;customization:ThemeCustomization};
type Palette={paper:string;canvas:string;surface:string;ink:string;muted:string;line:string;accent:string;wash:string;gold:string};
export type ThemeDefinition={id:ThemeId;name:string;description:string;family:ThemeFamily;dark:boolean;palette:Palette;titleFont:string;radius:number;art:string|null;ornament:string;collection:'classic'|'nature'|'fantasy'|'modern'|'companion'};
const serif='"Noto Serif SC","Source Han Serif SC","SimSun",Georgia,serif';
const inkFont='"KaiTi","STKaiti","SimSun",Georgia,serif';
const modern='"Segoe UI","Microsoft YaHei UI",sans-serif';
const p=(paper:string,canvas:string,surface:string,ink:string,muted:string,line:string,accent:string,wash:string,gold:string):Palette=>({paper,canvas,surface,ink,muted,line,accent,wash,gold});
const art=(id:string)=>'/themes/'+id+'.webp';
const ornament=(id:string)=>'/themes/'+id+'.svg';
export const themes:readonly ThemeDefinition[]=[
 {id:'moon',name:'月白纸笺',description:'墨青与暖白纸页，保留熟悉的文学书房。',family:'study',dark:false,collection:'classic',palette:p('#faf9f4','#efede5','#fffefa','#253c4c','#687985','#deded3','#1f6363','#e6eeea','#8c7040'),titleFont:serif,radius:16,art:null,ornament:ornament('folio')},
 {id:'mist',name:'青岚书房',description:'青灰书桌与清透留白，适合长时间写作。',family:'botanical',dark:false,collection:'nature',palette:p('#f1f3eb','#e5ece7','#f9faf4','#30453b','#5f7468','#cddad0','#3c705b','#dae6d9','#826d43'),titleFont:serif,radius:18,art:null,ornament:ornament('fern')},
 {id:'night',name:'夜墨星河',description:'熟悉的低光书房，柔和而清晰。',family:'study',dark:true,collection:'classic',palette:p('#242e39','#1b2530','#2b3743','#d7ddd9','#a7b6b7','#465562','#a8c7b9','#334854','#cfbb8d'),titleFont:serif,radius:16,art:null,ornament:ornament('folio')},
 {id:'amber',name:'琥珀书灯',description:'灯下暖纸与铜色细节，像翻开一本旧书。',family:'archive',dark:false,collection:'classic',palette:p('#f7f0e4','#eee8df','#fffaef','#48392b','#7b6856','#ded0bd','#8c562e','#efe2cc','#8f6838'),titleFont:serif,radius:14,art:null,ornament:ornament('folio')},
 {id:'sky',name:'雾蓝晨光',description:'清冷晨色与轻盈线框，清爽地开始新一页。',family:'study',dark:false,collection:'classic',palette:p('#f1f6fa','#e5edf4','#fbfdff','#2b4053','#586e80','#cbd9e5','#376684','#ddeaf3','#8b7454'),titleFont:modern,radius:16,art:null,ornament:ornament('folio')},
 {id:'plum',name:'紫檀夜读',description:'紫灰墨色与温柔光泽，沉静的夜读空间。',family:'study',dark:true,collection:'classic',palette:p('#282331','#201d29','#302b38','#e6dfe9','#bcb0c2','#51465b','#c0a5d5','#3c3148','#cfb495'),titleFont:serif,radius:16,art:null,ornament:ornament('folio')},
 {id:'yoshino',name:'芳乃 · 樱庭纸笺',description:'樱白浅金与和纸折角，私人角色资源保持独立。',family:'companion',dark:false,collection:'companion',palette:p('#fbf5f2','#f2ebe7','#fffaf7','#443b42','#756670','#e4d6d8','#8b4a67','#f1e3e8','#8b693d'),titleFont:inkFont,radius:18,art:null,ornament:ornament('petals')},
 {id:'rem',name:'蕾姆 · 蓝白茶笺',description:'清澈蓝白与精细蕾丝线，保留本地角色入口。',family:'companion',dark:false,collection:'companion',palette:p('#f1f7fd','#e7eef7','#fcfdff','#30425b','#5d708a','#d1dfef','#37649a','#e0ebf9','#8578a2'),titleFont:serif,radius:18,art:null,ornament:ornament('lace')},
 {id:'rem-night',name:'蕾姆 · 静蓝夜写',description:'深蓝低光与细致星光，夜间仍然清晰可读。',family:'companion',dark:true,collection:'companion',palette:p('#202c40','#172235','#27364d','#e1e9f7','#b0bfd7','#445776','#a7cafa','#334a6b','#c2b3dd'),titleFont:serif,radius:18,art:null,ornament:ornament('lace')},
 {id:'manuscript',name:'古典手稿',description:'雕版书页、皮革书脊与古铜装帧。',family:'archive',dark:false,collection:'classic',palette:p('#f5eedf','#e8deca','#fff8e9','#43342a','#77614e','#d5c3a5','#80532c','#ede0c9','#886239'),titleFont:serif,radius:12,art:art('manuscript'),ornament:ornament('folio')},
 {id:'ink',name:'远山水墨',description:'宣纸留白、细墨笔触与远山层次。',family:'ink',dark:false,collection:'nature',palette:p('#f4f4ef','#e7eae3','#fdfdf8','#293a35','#5f7069','#ccd4cb','#38665b','#e3ebe4','#865344'),titleFont:inkFont,radius:10,art:art('ink'),ornament:ornament('mountains')},
 {id:'observatory',name:'星图观测室',description:'星图轨道、银色刻度与深蓝观测窗。',family:'astral',dark:true,collection:'fantasy',palette:p('#141d34','#0b1225','#1c2943','#e6eaf7','#b0bed7','#3b4e70','#b4b7ff','#2e395b','#d0bd8a'),titleFont:serif,radius:18,art:art('observatory'),ornament:ornament('orbits')},
 {id:'gothic',name:'哥特藏书馆',description:'尖拱书窗、蔷薇深红与铜金藏书边框。',family:'gothic',dark:true,collection:'fantasy',palette:p('#241a20','#171116','#30212a','#f0e3d8','#c6aaa9','#65434b','#e2b88c','#49313a','#e2b88c'),titleFont:serif,radius:14,art:art('gothic'),ornament:ornament('arch')},
 {id:'cyber',name:'赛博霓虹',description:'切角仪表、精细网格与克制的蓝紫光。',family:'technical',dark:true,collection:'modern',palette:p('#101b2b','#09111e','#18263b','#dceafa','#a5b9d1','#36506c','#86d9ef','#203d51','#c5b0fa'),titleFont:modern,radius:10,art:art('cyber'),ornament:ornament('circuit')},
 {id:'greenhouse',name:'森林温室',description:'拱形玻璃、植物版画与明亮的橡木书桌。',family:'botanical',dark:false,collection:'nature',palette:p('#eef2e7','#dfe7d7','#fafbef','#293d2c','#586b50','#c5d1bc','#3e6843','#dce8d1','#836632'),titleFont:serif,radius:18,art:art('greenhouse'),ornament:ornament('fern')},
 {id:'minimal',name:'留白编辑室',description:'黑白排版与清晰秩序，让文字成为主角。',family:'minimal',dark:false,collection:'modern',palette:p('#f7f7f5','#ebebe8','#ffffff','#252727','#666b69','#d7d9d6','#343e3b','#ecefed','#5e6663'),titleFont:modern,radius:8,art:null,ornament:ornament('typeset')},
];
export const isThemeId=(value:unknown):value is ThemeId=>typeof value==='string'&&(themeIds as readonly string[]).includes(value);
export const getTheme=(value:unknown)=>themes.find(theme=>theme.id===value)||themes[0];
export const isDarkTheme=(value:ThemeId)=>getTheme(value).dark;
const rgb=(hex:string)=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16));
export function contrast(a:string,b:string){const l=(hex:string)=>rgb(hex).map(v=>{const n=v/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);const x=l(a),y=l(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
function mix(a:string,b:string,amount:number){const x=rgb(a),y=rgb(b);return '#'+x.map((n,i)=>Math.round(n*(1-amount)+y[i]*amount).toString(16).padStart(2,'0')).join('');}
export function resolvedPalette(theme:ThemeDefinition,custom:ThemeCustomization={}){
 const p={...theme.palette};if(custom.accent)p.accent=custom.accent;if(custom.ink)p.ink=custom.ink;
 if(custom.background){p.paper=custom.background;p.surface=mix(p.paper,theme.dark?'#000000':'#ffffff',.22);p.canvas=mix(p.paper,theme.dark?'#000000':'#888888',.12);p.wash=mix(p.paper,p.accent,.12);p.line=mix(p.paper,p.ink,.2);p.muted=mix(p.ink,p.paper,.32);}
 for(let i=0;i<20&&Math.min(contrast(p.muted,p.paper),contrast(p.muted,p.surface))<4.5;i++)p.muted=mix(p.muted,p.ink,.08);
 return p;
}
export function shapeTokens(value:number){
 const radius=Math.max(0,Math.min(20,value)),px=(factor:number)=>Math.round(radius*factor)+'px';
 return {'--radius-small':px(.35),'--radius-control':px(.6),'--radius-card':px(1),'--radius-panel':px(1.125),'--radius-popover':px(.85),'--radius-dialog':px(1.4),'--theme-radius':px(1)};
}
export function themeStyle(theme:ThemeDefinition,custom:ThemeCustomization={}):CSSProperties{
 const p=resolvedPalette(theme,custom),onAccent=contrast('#ffffff',p.accent)>contrast('#101820',p.accent)?'#ffffff':'#101820';
 const radius=custom.radius??theme.radius,decoration=(custom.decoration??70)/100,texture=(custom.texture??12)/100;
 const softShadow=theme.dark?'0 2px 8px #00000020,0 10px 28px #00000014':'0 2px 4px #253c4c04,0 7px 22px #253c4c07';
 return {
  ...Object.fromEntries(Object.entries(p).map(([key,value])=>['--'+key,value])),
  ...shapeTokens(radius),
  '--on-accent':onAccent,'--text':p.ink,'--border':p.line,'--panel':p.surface,'--bg':p.paper,'--soft-accent':p.wash,'--study-title':theme.titleFont,
  '--theme-art':theme.art?`url("${theme.art}")`:'none','--theme-ornament':`url("${theme.ornament}")`,
  '--theme-ornament-opacity':String(decoration),'--theme-texture-opacity':String(texture),'--theme-motion':`${(custom.motion??70)*2}ms`,
  '--soft-duration':`${Math.round((custom.motion??70)*1.8)}ms`,'--theme-row-space':custom.density==='compact'?'5px':'8px',
  '--success':theme.dark?'#a0d6b0':'#286640','--warning':theme.dark?'#f0cd83':'#805413','--danger':theme.dark?'#f2aca8':'#a23537','--info':theme.dark?'#a9cafa':'#335f8d',
  '--shadow':theme.dark?'0 14px 35px #00000030':`0 8px 24px ${mix(p.ink,'#ffffff',.1)}12`,
  '--study-shadow':theme.family==='minimal'?'none':softShadow,'--soft-shadow':softShadow,
  '--soft-shadow-hover':theme.dark?'0 4px 18px #00000038':'0 3px 7px #253c4c08,0 12px 28px #253c4c0c',
  '--soft-shadow-dialog':theme.dark?'0 12px 50px #00000060,0 1px 0 #ffffff0a inset':'0 12px 50px #253c4c24,0 2px 10px #253c4c10',
  colorScheme:theme.dark?'dark':'light',
 } as CSSProperties;
}
let appearanceTicket=0;
export function applyTheme(appearance:ThemeId,custom:ThemeCustomization={}){
 const theme=getTheme(appearance),root=document.documentElement,ticket=++appearanceTicket;root.dataset.themeSwitching='true';root.dataset.appearance=theme.id;root.dataset.theme=theme.dark?'dark':'light';root.dataset.visualFamily=theme.family;root.dataset.themeDensity=custom.density||'comfortable';
 for(const [name,value] of Object.entries(themeStyle(theme,custom))){if(name==='colorScheme')root.style.colorScheme=String(value);else root.style.setProperty(name,String(value));}
 window.dispatchEvent(new Event('novel-appearance-change'));
 requestAnimationFrame(()=>requestAnimationFrame(()=>{if(ticket===appearanceTicket)delete root.dataset.themeSwitching;}));
}
export function validateThemeCustomization(value:unknown):ThemeCustomization{
 if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('INVALID_THEME');const source=value as Record<string,unknown>,allowed=['name','accent','ink','background','radius','decoration','texture','motion','density'];
 if(Object.keys(source).some(k=>!allowed.includes(k)))throw new Error('INVALID_THEME');
 for(const key of ['accent','ink','background'])if(source[key]!=null&&(typeof source[key]!=='string'||!/^#[0-9a-f]{6}$/i.test(String(source[key]))))throw new Error('INVALID_THEME');
 for(const [key,max] of [['radius',20],['decoration',100],['texture',50],['motion',100]] as const)if(source[key]!=null&&(typeof source[key]!=='number'||!Number.isInteger(source[key])||Number(source[key])<0||Number(source[key])>max))throw new Error('INVALID_THEME');
 if(source.name!=null&&(typeof source.name!=='string'||source.name.length>60||/[\x00-\x1f]/.test(source.name)))throw new Error('INVALID_THEME');
 if(source.density!=null&&!['comfortable','compact'].includes(String(source.density)))throw new Error('INVALID_THEME');
 return {...source} as ThemeCustomization;
}
