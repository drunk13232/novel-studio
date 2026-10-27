import {BookOpen,Feather,Users,Network,Layers,Lightbulb,Heart,Compass} from 'lucide-react';
import type {CSSProperties} from 'react';
import seal from './assets/study/brand-seal.svg';
import tide from './assets/study/cover-tide.webp';
import garden from './assets/study/cover-garden.webp';
import {useAppearance} from './companion-theme';
import {getTheme} from './themes';
export function BrandSeal(){return <img src={seal} alt="" aria-hidden="true" width="38" height="38"/>;}
export function CoverArtwork({identity}:{identity:string}){const theme=getTheme(useAppearance());let n=0;for(const x of identity)n=(n*31+x.charCodeAt(0))|0;return <img className="study-cover-art" data-fallback-cover loading="lazy" decoding="async" src={theme.art||(Math.abs(n)%2?tide:garden)} style={theme.art?{objectPosition:'right center'}:undefined} alt="" aria-hidden="true"/>;}
export function DimensionIcon({id}:{id:string}){const Icon=({style:Feather,character:Users,structure:Layers,thought:Lightbulb,clue:Compass,logic:Network,emotion:Heart,innovation:BookOpen} as Record<string,typeof Feather>)[id]||BookOpen;return <Icon className="dimension-icon" size={18} strokeWidth={1.6} aria-hidden="true"/>;}
export function ScoreMedallion({score,label,stale=false}:{score:number|null|undefined;label:string;stale?:boolean}){const valid=typeof score==='number'&&Number.isFinite(score);return <div className={'score-medallion '+(stale?'is-stale':'')} role="img" aria-label={label+': '+(valid?score+'/100':'—')}><svg viewBox="0 0 120 120" aria-hidden="true"><circle className="score-track" cx="60" cy="60" r="52"/><circle className="score-value" cx="60" cy="60" r="52" pathLength="100" style={{strokeDasharray:(valid?Math.max(0,Math.min(100,score!)):0)+' 100'} as CSSProperties}/></svg><div><strong>{valid?score:'—'}</strong><small>/ 100</small></div></div>;}
