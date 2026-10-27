import {Clock3,Target,BookOpen} from 'lucide-react';
import i18n from './i18n';
import {t as translateUI,useUiTranslation} from './i18n';
import {useState} from 'react';
import {RecentReadingList,type RecentReading} from './recent-reading';
import {useRemote,Data,Empty} from './library-shared';

function RecoveryDesk({project,onBook}:{project:string|null;onBook:(id:string,path?:string)=>void}){
 useUiTranslation(["dashboard","navigation"]);

 const recovery=useRemote<Data[]>('/api/studio/recovery-index'+(project?'?project='+encodeURIComponent(project):''),[]);
 return <section className="recovery-desk"><h2>{translateUI("dashboard:unsavedWork")}</h2>{recovery.error&&<p role="alert">{translateUI("dashboard:recoveryUnavailable")}</p>}{recovery.value.filter(r=>r.project===project).map(r=><button className="desk-entry" key={r.project+r.path} onClick={()=>onBook(r.project,r.path)}><strong>{r.title} · {r.path.startsWith('chapters/story/')?translateUI("dashboard:singleTextBody"):'第 '+(r.path.match(/chapter-(\d+)/)?.[1]||'未知')+' 章'}</strong><small>{new Date(r.saved_at).toLocaleString(i18n.language)}{r.conflict?translateUI("dashboard:updatedOriginalRecoveryNotice"):''}</small><span>{translateUI("dashboard:reviewRecovery")}</span></button>)}{!recovery.value.length&&!recovery.error&&<p className="muted">{project?translateUI("dashboard:noPendingServerRecoveryCopies"):translateUI("dashboard:selectWorkForRecoveryCopies")}</p>}</section>;
}
export function HomeDesk({books,lastProject,lastFiles,onBook,onStatistics,onRecent,onAllRecent}:{books:Data[];lastProject:string|null;lastFiles:Record<string,string>;onBook:(id:string,path?:string)=>void;onStatistics:(id:string)=>void;onRecent:(entry:RecentReading)=>void;onAllRecent:(project:string|null)=>void}){
 useUiTranslation(["dashboard","navigation"]);

 const [selected,setSelected]=useState(books.some(b=>b.id===lastProject)?lastProject:null);
 const scope=books.some(b=>b.id===selected)?selected:null;
 const latest=books.find(b=>b.id===scope)||books[0];
 const recent=[...books].sort((a,b)=>(b.updated_at||'').localeCompare(a.updated_at||'')).slice(0,3);
 return <><section className="home-recent"><section><div className="home-section-mark"><Clock3 size={18} aria-hidden="true"/><span className="overline">PICK UP THE THREAD</span></div><h2>{translateUI("dashboard:recentWork")}</h2>{recent.map(b=><button className="desk-entry" key={b.id} onClick={()=>onBook(b.id,lastFiles[b.id])}><strong>{b.title}</strong><small>{b.continue_chapter?.title||'尚未开始正文'} · {Number(b.han||0).toLocaleString()} {translateUI("dashboard:characterCountUnit")}</small><span>{translateUI("dashboard:continueForward")}</span></button>)}</section><section><div className="home-section-mark"><Target size={18} aria-hidden="true"/><span className="overline">ONE PAGE AT A TIME</span></div><h2>{translateUI("dashboard:currentWritingGoal")}</h2>{latest?<><h3>{latest.title}</h3><p>{latest.goals?.daily?`每日 ${latest.goals.daily.toLocaleString()} 汉字`:translateUI("dashboard:dailyGoalNotSet")}</p>{latest.goals?.book>0&&<><progress aria-label={translateUI("dashboard:wholeBookWritingGoal")} max={latest.goals.book} value={Math.min(latest.han||0,latest.goals.book)}/><small>{translateUI("dashboard:wholeBookScope")}{(latest.han||0).toLocaleString()} / {latest.goals.book.toLocaleString()} {translateUI("dashboard:chineseCharacterCountUnit")}</small></>}<button onClick={()=>onStatistics(latest.id)}>{translateUI("dashboard:viewAndAdjustGoals")}</button></>:<Empty text="有了第一部作品，就可以设置自己的写作目标。"/>}</section><section><div className="home-section-mark"><BookOpen size={18} aria-hidden="true"/><span className="overline">READ, THEN WRITE</span></div><div className="section-heading"><h2>{translateUI("navigation:recentReading")}</h2><button onClick={()=>onAllRecent(scope)}>{translateUI("dashboard:allReading")}</button></div><select aria-label={translateUI("dashboard:recentReadingWorkScope")} value={scope||''} onChange={e=>setSelected(e.target.value||null)}><option value="">{translateUI("dashboard:publicLiterature")}</option>{books.map(b=><option key={b.id} value={b.id}>{b.title}</option>)}</select><RecentReadingList key={scope||'public'} project={scope} onOpen={onRecent} limit={3}/></section></section><RecoveryDesk key={scope||'public'} project={scope} onBook={onBook}/></>;
}
