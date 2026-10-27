import {t as translateUI,useUiTranslation} from './i18n';
import {useEffect} from 'react';
import {Data,Empty,ErrorNote,useRemote,date} from './library-shared';

export type RecentReading={kind:'reference'|'chapter';scope:string;source:string;id?:string;path?:string;title:string;at:string;position:string|number;source_label:string;version_changed:boolean};
export function RecentReadingList({project,onOpen,limit=120}:{project?:string|null;onOpen:(entry:RecentReading)=>void;limit?:number}){
 useUiTranslation(["dashboard","navigation"]);

 const url='/api/studio/recent-reading'+(project?'?project='+encodeURIComponent(project):'');
 const r=useRemote<Data>(url,{scope:project||'public',items:[],loading:true});
 useEffect(()=>{const refresh=()=>void r.run(r.refresh);window.addEventListener('reference-reading-changed',refresh);return()=>window.removeEventListener('reference-reading-changed',refresh);},[url]);
 return <div className="recent-reading-list" aria-busy={r.busy}><ErrorNote text={r.error}/>{(r.value.scope===(project||'public')?r.value.items:[]).slice(0,limit).map((entry:RecentReading)=><button className="desk-entry" key={[entry.kind,entry.scope,entry.source,entry.id||entry.path].join(':')} onClick={()=>onOpen(entry)}><span className="recent-kind" aria-hidden="true">{entry.kind==='chapter'?translateUI("dashboard:chapterUnit"):translateUI("dashboard:textUnit")}</span><span><strong>{entry.title}</strong><small>{entry.source_label} · {entry.kind==='chapter'?`已读 ${Math.round(Number(entry.position)*100)}%`:`位置 ${entry.position}`} · {date(entry.at)}</small>{entry.version_changed&&<small className="position-changed">{translateUI("dashboard:sourceChangedReconfirmPosition")}</small>}</span><span aria-hidden="true">→</span></button>)}{!r.value.items.length&&!r.error&&<Empty text={r.busy||r.value.loading?'正在读取阅读记录…':'打开文献或阅读章节后，可以从这里接着读。'}/>}</div>;
}
export default function RecentReadingPage(props:{project?:string|null;onOpen:(entry:RecentReading)=>void}){
 useUiTranslation(["dashboard","navigation"]);

 return <section className="recent-reading-page"><p className="overline">WHERE YOU LEFT OFF</p><h1>{translateUI("navigation:recentReading")}</h1><p className="muted">{props.project?translateUI("dashboard:projectPublicRecentReadingScope"):translateUI("dashboard:publicRecentReadingScope")}</p><RecentReadingList {...props}/></section>;
}
