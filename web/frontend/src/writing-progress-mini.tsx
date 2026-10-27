import {ChartNoAxesCombined} from 'lucide-react';
import {t,useUiTranslation,formatNumber} from './i18n';
import {useWritingProgress,type WritingProgress} from './writing-metrics-client';
import './writing-progress-mini.css';
export function WritingProgressMini({project,onOpen}:{project:string;onOpen:()=>void}){
 useUiTranslation('dashboard');const {data,error,loading,retry}=useWritingProgress(project);
 return <div className="writing-progress-mini"><button type="button" onClick={onOpen} title={t('dashboard:miniDashboardHelp')} aria-label={t('dashboard:openWritingDashboard')}><ChartNoAxesCombined size={14} aria-hidden="true"/>{data?<><span>{t(data.daily_goal>0?'dashboard:miniProgress':'dashboard:miniProgressNoGoal',{count:formatNumber(data.today),goal:formatNumber(data.daily_goal),streak:formatNumber(data.current_streak)})}</span>{data.daily_goal>0&&<span className="writing-mini-track" aria-hidden="true"><span style={{width:Math.max(0,Math.min(100,data.today/data.daily_goal*100))+'%'}}/></span>}</>:<span>{t(error?'dashboard:miniProgressFailed':'dashboard:miniProgressLoading')}</span>}</button>{error&&<button type="button" onClick={()=>void retry()} disabled={loading}>{t('dashboard:retryProgress')}</button>}</div>;
}
export function WritingTodayBadge({progress}:{progress?:WritingProgress}){
 useUiTranslation('dashboard');if(!progress)return null;
 const value=progress.today;
 return <span className={'writing-today-badge'+(value<0?' is-negative':'')} title={t('dashboard:shelfTodayHelp')} aria-label={t('dashboard:shelfTodayBadge',{count:(value>0?'+':'')+formatNumber(value)})}>{t('dashboard:shelfTodayBadge',{count:(value>0?'+':'')+formatNumber(value)})}</span>;
}
