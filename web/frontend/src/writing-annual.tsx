import {useEffect,useRef,useState} from 'react';
import i18n,{t,useUiTranslation} from './i18n';
import {api} from './api';
import './writing-annual.css';

type Source={net_han:number;added_han:number;deleted_han:number;save_count:number};
type Totals={net_han:number;manual_han:number;ai_han:number;restore_han:number;unknown_han:number;save_count:number};
export type AnnualReport={project_id:string;year:number;available_years:number[];timezone:string;start:string;end:string;is_partial_year:boolean;has_saved_events:boolean;
 totals:Totals;sources:Record<'manual'|'ai'|'restore'|'unknown',Source>;streaks:{longest:number;writing_days:number;best_day:{date:string;han:number}|null};
 calendar:{date:string;han:number}[];months:(Totals&{month:number})[];hourly:{hour:number;han:number;save_count:number}[];peak_hour:number|null;
 edited_chapters:number;most_edited:(Totals&{id:string;title:string;number:number|null;volume_id:string})[];
 volumes:(Totals&{id:string;title:string;edited_chapters:number})[];unassigned:{net_han:number;save_count:number};
 quality:{legacy_methodless_saves:number;historical_exclusions:{excluded_estimates:number;excluded_invalid_events:number;excluded_future_events:number}};missing_sections?:string[]};
export function annualSourceShare(report:Pick<AnnualReport,'sources'>){const manual=Math.max(0,report.sources.manual.added_han),ai=Math.max(0,report.sources.ai.added_han);return manual+ai>0?{manual,ai,manualPercent:manual/(manual+ai)*100,aiPercent:ai/(manual+ai)*100}:null;}
export type AnnualShareIdentity={penName:string;bookTitle:string};
const tr=(key:string,values?:Record<string,unknown>)=>t('annual:'+key,values);
const num=(value:number)=>value.toLocaleString(i18n.language);
const signed=(value:number)=>(value>0?'+':'')+num(value);
const thisYear=()=>new Date(Date.now()+8*3600000).getUTCFullYear();

/** Missing optional charts are omitted, never replaced with invented zeroes. */
export function readAnnualReport(value:unknown,project?:string,year?:number):AnnualReport{
 const row=value as AnnualReport,integer=(v:unknown)=>typeof v==='number'&&Number.isSafeInteger(v);
 const sourceKeys=['manual','ai','restore','unknown'] as const;
 if(!row||typeof row!=='object'||(project&&row.project_id!==project)||(year!==undefined&&row.year!==year)||!integer(row.year)||!row.totals||!row.sources||!row.streaks||
  !['net_han','manual_han','ai_han','restore_han','unknown_han','save_count'].every(key=>integer((row.totals as unknown as Record<string,unknown>)[key]))||
  !sourceKeys.every(key=>row.sources[key]&&['net_han','added_han','deleted_han','save_count'].every(field=>integer((row.sources[key] as unknown as Record<string,unknown>)[field])))||
  !integer(row.streaks.longest)||!integer(row.streaks.writing_days))throw Error(tr('incompleteCore'));
 const missing:string[]=[];
 function list<T>(key:string,input:unknown,valid:(item:T)=>boolean){if(!Array.isArray(input)){missing.push(key);return [] as T[];}const result=input.filter(valid);if(result.length!==input.length)missing.push(key);return result as T[];}
 function unique<T>(key:string,rows:T[],identifier:(item:T)=>string|number){const counts=new Map<string|number,number>();for(const row of rows)counts.set(identifier(row),(counts.get(identifier(row))||0)+1);if([...counts.values()].some(count=>count>1))missing.push(key);return rows.filter(row=>counts.get(identifier(row))===1);}
 const validDate=(date:string)=>{try{return date.startsWith(row.year+'-')&&new Date(date+'T00:00:00Z').toISOString().slice(0,10)===date;}catch{return false;}};
 let months=list<AnnualReport['months'][number]>('monthly',row.months,item=>!!item&&integer(item.month)&&item.month>=1&&item.month<=12&&integer(item.net_han));
 let hourly=list<AnnualReport['hourly'][number]>('hourly',row.hourly,item=>!!item&&integer(item.hour)&&item.hour>=0&&item.hour<=23&&integer(item.han));
 let calendar=list<AnnualReport['calendar'][number]>('calendar',row.calendar,item=>!!item&&typeof item.date==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(item.date)&&validDate(item.date)&&integer(item.han));
 months=unique('monthly',months,item=>item.month);hourly=unique('hourly',hourly,item=>item.hour);calendar=unique('calendar',calendar,item=>item.date);
 if(new Set(months.map(item=>item.month)).size!==months.length||months.length!==12)missing.push('monthly');
 if(new Set(hourly.map(item=>item.hour)).size!==hourly.length||hourly.length!==24)missing.push('hourly');
 const edited=list<AnnualReport['most_edited'][number]>('mostEdited',row.most_edited,item=>!!item&&typeof item.id==='string'&&integer(item.save_count)&&integer(item.manual_han)&&integer(item.ai_han));
 const volumes=list<AnnualReport['volumes'][number]>('volumes',row.volumes,item=>!!item&&typeof item.id==='string'&&integer(item.edited_chapters)&&integer(item.manual_han)&&integer(item.ai_han)&&integer(item.restore_han));
 const quality=row.quality||{legacy_methodless_saves:0,historical_exclusions:{excluded_estimates:0,excluded_invalid_events:0,excluded_future_events:0}};
 if(!row.quality)missing.push('methodTitle');
 const best=row.streaks.best_day&&integer(row.streaks.best_day.han)&&typeof row.streaks.best_day.date==='string'?row.streaks.best_day:null;
 return {...row,months,hourly,calendar,most_edited:edited,volumes,quality,streaks:{...row.streaks,best_day:best},
  unassigned:row.unassigned&&integer(row.unassigned.save_count)?row.unassigned:{save_count:0,net_han:0},
  peak_hour:integer(row.peak_hour)&&row.peak_hour!>=0&&row.peak_hour!<24?row.peak_hour:null,
  available_years:Array.isArray(row.available_years)?row.available_years.filter(year=>integer(year)&&year>=1900&&year<=thisYear()):[row.year],missing_sections:[...new Set(missing)]};
}

/** Canvas is composed from an explicit allowlist of aggregates and manually entered names.
 * It never reads the DOM, project title, paths, notes, manuscript or API configuration. */
export function paintAnnualShare(canvas:HTMLCanvasElement,report:AnnualReport,identity:AnnualShareIdentity,label:(key:string,values?:Record<string,unknown>)=>string=tr){
 canvas.width=1080;canvas.height=1280;
 const ctx=canvas.getContext('2d');if(!ctx)throw Error(label('canvasUnavailable'));
 const font=(size:number)=>`${size>=50?'600':'400'} ${size}px system-ui, sans-serif`;
 const draw=(text:string,x:number,y:number,size=30,color='#24454b',maxWidth=936)=>{
  let actual=size;ctx.font=font(actual);while(actual>14&&ctx.measureText(text).width>maxWidth){actual-=1;ctx.font=font(actual);}
  let value=text;const symbols=Array.from(value);if(ctx.measureText(value).width>maxWidth){while(symbols.length&&ctx.measureText(symbols.join('')+'…').width>maxWidth)symbols.pop();value=symbols.join('')+'…';}
  ctx.fillStyle=color;ctx.fillText(value,x,y);
 };
 const fit=(raw:string,maxWidth:number,size:number)=>{const symbols=Array.from(raw.replace(/[\r\n\t]/g,' ').trim()).slice(0,80);const value=symbols.join('');ctx.font=font(size);if(ctx.measureText(value).width<=maxWidth)return value;while(symbols.length&&ctx.measureText(symbols.join('')+'…').width>maxWidth)symbols.pop();return symbols.join('')+'…';};
 ctx.fillStyle='#faf8f1';ctx.fillRect(0,0,1080,1280);ctx.fillStyle='#26706b';ctx.fillRect(64,70,8,110);
 draw(label('shareHeading',{year:report.year}),102,116,46);
 draw(fit(identity.bookTitle||label('unnamedBook'),870,36),102,176,36);
 if(identity.penName.trim())draw(fit(identity.penName,870,26),102,218,26,'#627370');
 draw(label('sharePeriod',{start:report.start,end:report.end}),72,276,23,'#627370');
 const fields:[string,string][]=[['manual',signed(report.totals.manual_han)],['ai',signed(report.totals.ai_han)],['writingDays',num(report.streaks.writing_days)],['longest',num(report.streaks.longest)]];
 fields.forEach(([key,value],index)=>{const x=72+(index%2)*480,y=350+Math.floor(index/2)*150;draw(label(key),x,y,27,'#627370',426);draw(value,x,y+68,62,'#24454b',426);});
 let y=675;
 for(const key of ['restore','unknown'] as const)if(report.sources[key].save_count){draw(label(key)+': '+signed(report.sources[key].net_han),72,y,25);y+=38;}
 if(report.streaks.best_day){draw(label('bestDay')+': '+report.streaks.best_day.date+'  '+signed(report.streaks.best_day.han),72,y+15,25);y+=58;}
 draw(label('monthly'),72,Math.max(804,y+20),26);
 const chartY=1010,max=Math.max(1,...report.months.map(row=>Math.abs(row.net_han)));
 ctx.strokeStyle='#d2d9d2';ctx.beginPath();ctx.moveTo(72,chartY);ctx.lineTo(1000,chartY);ctx.stroke();
 for(let month=1;month<=12;month++){const row=report.months.find(item=>item.month===month),x=83+(month-1)*76;if(row){const height=Math.abs(row.net_han)/max*130;ctx.fillStyle=row.net_han<0?'#b28152':'#26706b';ctx.fillRect(x,row.net_han<0?chartY:chartY-height,42,Math.max(row.net_han?2:0,height));}else draw('—',x+6,chartY-12,18,'#627370',48);draw(String(month),x+6,1172,22,'#627370',48);}
 draw(label('shareBasis'),72,1220,20,'#627370');if(report.missing_sections?.length)draw(label('sharePartial'),72,1253,18,'#946a41');
 return canvas;
}

export function WritingAnnualReport({project,onClose}:{project:string;onClose?:()=>void}){
 useUiTranslation('annual');
 const [year,setYear]=useState(thisYear),[report,setReport]=useState<AnnualReport|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[reload,setReload]=useState(0);
 const [penName,setPenName]=useState(''),[bookTitle,setBookTitle]=useState(''),[sharing,setSharing]=useState(false),[shareError,setShareError]=useState(''),[preview,setPreview]=useState(false);
 const canvas=useRef<HTMLCanvasElement|null>(null),mounted=useRef(true),request=useRef(0);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{setYear(thisYear());setReport(null);setPenName('');setBookTitle('');setPreview(false);},[project]);
 useEffect(()=>{const id=++request.current,controller=new AbortController();setLoading(true);setError('');setReport(null);setPreview(false);
  void api<AnnualReport>('/api/projects/'+encodeURIComponent(project)+'/experience/annual?year='+year,undefined,'GET',{signal:controller.signal}).then(value=>{if(id===request.current&&!controller.signal.aborted)setReport(readAnnualReport(value,project,year));}).catch(reason=>{if(id===request.current&&!controller.signal.aborted)setError(String(reason).replace(/^Error: /,''));}).finally(()=>{if(id===request.current&&!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[project,year,reload]);
 async function share(download:boolean){
  if(!report||!canvas.current||sharing)return;setSharing(true);setShareError('');
  try{paintAnnualShare(canvas.current,report,{penName,bookTitle});setPreview(true);
   if(download){const blob=await new Promise<Blob>((resolve,reject)=>canvas.current!.toBlob(value=>value?resolve(value):reject(Error(tr('canvasUnavailable'))),'image/png'));
    if(!mounted.current)return;const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='NovelStudio-Writing-'+report.year+'.png';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  }catch(reason){if(mounted.current)setShareError(String(reason).replace(/^Error: /,''));}finally{if(mounted.current)setSharing(false);}
 }
 const years=Array.from(new Set([thisYear(),year,...(report?.available_years||[])])).sort((a,b)=>b-a);
 const maxMonth=Math.max(1,...(report?.months||[]).map(row=>Math.abs(row.net_han)));
 const maxHour=Math.max(1,...(report?.hourly||[]).map(row=>Math.abs(row.han)));
 return <section className="writing-annual" aria-labelledby="writing-annual-title"><header className="annual-heading"><div><small>{tr('eyebrow')}</small><h2 id="writing-annual-title">{tr('title')}</h2><p>{tr('scope')}</p></div>{onClose&&<button onClick={onClose}>{tr('close')}</button>}</header>
  <div className="annual-controls"><label>{tr('year')}<select value={year} disabled={loading} onChange={event=>setYear(Number(event.target.value))}>{years.map(value=><option key={value} value={value}>{value}</option>)}</select></label><button disabled={loading} onClick={()=>setReload(value=>value+1)}>{tr('refresh')}</button></div>
  {loading&&<p role="status">{tr('loading')}</p>}{error&&<p role="alert" className="annual-note">{error}</p>}
  {report&&<>{!!report.missing_sections?.length&&<p className="annual-note" role="status">{tr('partialData',{sections:report.missing_sections.map(key=>tr(key)).join(' / ')})}</p>}<p className="annual-note">{tr('period',{start:report.start,end:report.end})} · {report.is_partial_year?tr('partialYear'):tr('completeYear')}</p>
   {!report.has_saved_events&&<div className="annual-empty"><h3>{tr('emptyTitle')}</h3><p>{tr('emptyHelp')}</p></div>}
   <div className="annual-metrics">{(['manual','ai','restore','unknown'] as const).filter(key=>key==='manual'||key==='ai'||report.sources[key].save_count>0).map(key=><article key={key} data-source={key}><small>{tr(key)}</small><strong>{signed(report.sources[key].net_han)}</strong><span>{tr('sourceDetail',{added:num(report.sources[key].added_han),deleted:num(report.sources[key].deleted_han),saves:num(report.sources[key].save_count)})}</span></article>)}</div>
   <section className="annual-card"><h3>{tr('sourceShare')}</h3><p>{tr('sourceShareBasis')}</p>{annualSourceShare(report)?<><div className="annual-controls"><span>{tr('manualAdditions')}: {num(annualSourceShare(report)!.manual)} · {annualSourceShare(report)!.manualPercent.toFixed(1)}%</span><span>{tr('aiAdditions')}: {num(annualSourceShare(report)!.ai)} · {annualSourceShare(report)!.aiPercent.toFixed(1)}%</span></div><progress aria-label={tr('sourceShare')} value={annualSourceShare(report)!.aiPercent} max={100}/></>:<p>{tr('sourceShareEmpty')}</p>}</section>

   <div className="annual-metrics annual-records"><article><small>{tr('writingDays')}</small><strong>{num(report.streaks.writing_days)}</strong><span>{tr('writingDayRule')}</span></article><article><small>{tr('longest')}</small><strong>{num(report.streaks.longest)}</strong><span>{tr('withinYear')}</span></article><article><small>{tr('bestDay')}</small><strong>{report.streaks.best_day?signed(report.streaks.best_day.han):'—'}</strong><span>{report.streaks.best_day?.date||tr('noRecord')}</span></article>{report.peak_hour!==null&&<article><small>{tr('peakHour')}</small><strong>{String(report.peak_hour).padStart(2,'0')}:00</strong><span>{tr('hourRule')}</span></article>}</div>
   <section className="annual-card"><h3>{tr('calendar')}</h3><p>{tr('calendarHelp')}</p>{!report.calendar.length&&<p>{tr('chartUnavailable')}</p>}<div className="annual-calendar" dir="ltr">{report.calendar.map(day=><span key={day.date} title={day.date+' · '+signed(day.han)} aria-label={day.date+' · '+signed(day.han)} className={day.han<0?'negative':day.han===0?'zero':day.han<500?'level-1':day.han<1500?'level-2':'level-3'}/>)}</div></section>
   <div className="annual-chart-grid"><section className="annual-card"><h3>{tr('monthly')}</h3>{!report.months.length&&<p>{tr('chartUnavailable')}</p>}<div className="annual-months">{report.months.map(row=><div key={row.month}><b>{tr('monthLabel',{month:row.month})}</b><div><i className={row.net_han<0?'negative':''} style={{width:Math.abs(row.net_han)/maxMonth*100+'%'}}/></div><span>{signed(row.net_han)}</span></div>)}</div><p>{tr('monthlyRule')}</p></section><section className="annual-card"><h3>{tr('hourly')}</h3><p>{tr('hourRule')}</p>{report.hourly.length!==24&&<p>{tr('chartUnavailable')}</p>}<div className="annual-hours" dir="ltr">{(report.hourly.length===24?report.hourly:[]).map(row=><div key={row.hour} title={row.hour+':00 · '+signed(row.han)}><div><i className={row.han<0?'negative':''} style={{height:Math.abs(row.han)/maxHour*100+'%'}}/></div><small>{row.hour%3===0?row.hour:''}</small></div>)}</div><p>{tr('negativeLegend')}</p></section></div>
   {report.most_edited.length>0&&<section className="annual-card"><h3>{tr('mostEdited')}</h3><p>{tr('catalogRule')}</p><ol className="annual-edited">{report.most_edited.map(chapter=><li key={chapter.id}><span>{chapter.title||tr('untitledChapter')}</span><b>{tr('savedTimes',{count:chapter.save_count})}</b><small>{tr('manual')}: {signed(chapter.manual_han)} · {tr('ai')}: {signed(chapter.ai_han)}</small></li>)}</ol>{report.unassigned.save_count>0&&<p>{tr('unassigned',{count:report.unassigned.save_count})}</p>}</section>}
   {report.volumes.length>0&&<section className="annual-card"><h3>{tr('volumes')}</h3><div className="annual-table-scroll"><table><thead><tr><th>{tr('volume')}</th><th>{tr('editedChapters')}</th><th>{tr('manual')}</th><th>{tr('ai')}</th><th>{tr('restore')}</th></tr></thead><tbody>{report.volumes.map(volume=><tr key={volume.id}><th>{volume.title}</th><td>{num(volume.edited_chapters)}</td><td>{signed(volume.manual_han)}</td><td>{signed(volume.ai_han)}</td><td>{signed(volume.restore_han)}</td></tr>)}</tbody></table></div><p>{tr('catalogRule')}</p></section>}
   <section className="annual-card annual-sharing"><h3>{tr('shareTitle')}</h3><p>{tr('sharePrivacy')}</p><div className="annual-identities"><label>{tr('penName')}<input maxLength={60} value={penName} onChange={event=>{setPenName(event.target.value);setPreview(false);}}/></label><label>{tr('bookTitle')}<input maxLength={60} value={bookTitle} onChange={event=>{setBookTitle(event.target.value);setPreview(false);}}/></label></div><div className="annual-controls"><button disabled={sharing} onClick={()=>void share(false)}>{tr('preview')}</button><button disabled={sharing} onClick={()=>void share(true)}>{sharing?tr('preparing'):tr('download')}</button></div>{shareError&&<p role="alert">{shareError}</p>}<canvas ref={canvas} hidden={!preview} aria-label={tr('sharePreview')} role="img"/></section>
   <details className="annual-method"><summary>{tr('methodTitle')}</summary><p>{tr('method')}</p><p>{tr('monthlyRule')}</p><p>{tr('catalogRule')}</p>{report.quality.legacy_methodless_saves>0&&<p>{tr('legacy',{count:report.quality.legacy_methodless_saves})}</p>}<p>{tr('omittedUnknown')}</p></details>
  </>}
 </section>;
}
