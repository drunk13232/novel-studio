import {lazy,Suspense,useEffect,useRef,useState} from 'react';
import {api} from './api';
import {t,useUiTranslation} from './i18n';
import {WRITING_METRICS_CHANGED} from './writing-metrics-events';
import './print-edition.css';
const ReferencePDF=lazy(()=>import('./reference-pdf'));
const tr=(key:string,values?:Record<string,unknown>)=>t('print:'+key,values);
type Layout={paper_size:'A5'|'POCKET32';gutter_mm:number;running_header:boolean;page_numbers:boolean};
type Artifact={id:string;sha256:string;pages:number;chapter_pages?:{id:string;title:string;page:number|null;status:string}[];front_pages?:number|null;size:number;paper_size:string;width_mm:number;height_mm:number;file_url:string;created_at:string;
 layout_warnings:{kind:string;chapter_number:number;line:number;characters:number;snippet:string;path?:string;document_revision?:string;exact?:string;start?:number;end?:number;prefix?:string;suffix?:string;evidence?:boolean}[];source_warnings:string[];limits:string[]};
type SourceStatus={status:'CURRENT'|'CHANGED'|'UNKNOWN';checked_at:string;verified_chapters:number;source_chapters:number;changed:{chapter_id:string;path:string;reason:string}[]};
type PrintOperation={id:string;project:string;key:string;cancelled:boolean;submitted:boolean;controller:AbortController;cancelPending:boolean};
const bookBase=(project:string)=>'/api/projects/'+encodeURIComponent(project)+'/book';
const messageOf=(reason:unknown)=>(reason as {code?:string})?.code==='PRINT_REQUEST_CONFLICT'?tr('requestConflict'):String(reason).replace(/^Error: /,'');

/** Uses a single immutable PDF. Cancellation targets its own request only; late
 * receipts cannot replace another request or turn a cancelled preview into success. */
export default function PrintEdition({project,selection,onOpen}:{project:string;selection:Record<string,any>;onOpen?:(path:string,location?:Record<string,any>)=>void}){
 useUiTranslation('print');
 const [layout,setLayout]=useState<Layout>({paper_size:'A5',gutter_mm:3,running_header:true,page_numbers:true});
 const [artifact,setArtifact]=useState<Artifact|null>(null),[sourceWarnings,setSourceWarnings]=useState<string[]>([]),[confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false),[cancelling,setCancelling]=useState(false),[exporting,setExporting]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[result,setResult]=useState<{path:string;sha256:string}|null>(null);
 const [sourceStatus,setSourceStatus]=useState<SourceStatus|null>(null),[checkingSource,setCheckingSource]=useState(false),[allowSnapshot,setAllowSnapshot]=useState(false),[sourceRefresh,setSourceRefresh]=useState(0);
 const [page,setPage]=useState(1),[count,setCount]=useState(1),[rendered,setRendered]=useState(false),[viewerError,setViewerError]=useState(''),[width,setWidth]=useState(620);
 const mounted=useRef(true),operation=useRef<PrintOperation|null>(null),pane=useRef<HTMLDivElement|null>(null),generation=useRef(0),exportPending=useRef(false);
 const key=JSON.stringify({...selection,directory:undefined,confirm_warnings:undefined,format:'pdf',...layout});
 const base=bookBase(project),latest=useRef({project,key});latest.current={project,key};
 const liveOperation=(op:PrintOperation)=>mounted.current&&operation.current===op&&latest.current.project===op.project&&latest.current.key===op.key;
 async function stop(op:PrintOperation|null,show=true){
  if(!op||op.cancelPending)return;op.cancelled=true;op.cancelPending=true;
  if(show&&liveOperation(op)){setCancelling(true);setNotice(tr('cancelling'));setError('');}
  try{
   const receipt=op.submitted?await api<{status:string}>(bookBase(op.project)+'/print-preview/'+op.id+'/cancel',undefined,'POST'):{status:'CANCELLED'};
   op.controller.abort();
   if(show&&liveOperation(op)){setNotice(tr(receipt.status==='SUCCEEDED'?'cancelTooLate':'cancelled'));setBusy(false);setCancelling(false);operation.current=null;}
  }catch(reason){if(show&&liveOperation(op)){setError(tr('cancelFailed')+' '+messageOf(reason));setCancelling(false);}}
  finally{op.cancelPending=false;}
 }
 useEffect(()=>{generation.current++;const prior=operation.current;operation.current=null;if(prior)void stop(prior,false);setBusy(false);setCancelling(false);setArtifact(null);setSourceStatus(null);setAllowSnapshot(false);setSourceWarnings([]);setConfirmed(false);setError('');setNotice('');setResult(null);setRendered(false);setViewerError('');},[project,key]);
 useEffect(()=>{const element=pane.current;if(!element)return;const measure=()=>setWidth(Math.max(200,Math.min(900,element.clientWidth-18)));measure();if(typeof ResizeObserver==='undefined')return;const observer=new ResizeObserver(measure);observer.observe(element);return()=>observer.disconnect();},[]);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;generation.current++;const prior=operation.current;operation.current=null;if(prior)void stop(prior,false);};},[]);
 useEffect(()=>{
  if(!artifact)return;let active=true,pending=false,again=false;const controller=new AbortController();
  async function check(){if(!active)return;if(pending){again=true;return;}pending=true;
   do{again=false;setCheckingSource(true);try{const value=await api<SourceStatus>(base+'/print/'+artifact!.id+'/source-status',undefined,'GET',{signal:controller.signal});if(active)setSourceStatus(value);}
    catch{if(active)setSourceStatus({status:'UNKNOWN',checked_at:'',verified_chapters:0,source_chapters:0,changed:[]});}
   }while(active&&again);
   pending=false;if(active)setCheckingSource(false);
  }
  const onSaved=(event:Event)=>{const detail=(event as CustomEvent).detail;if(detail?.project===project&&['save','restore'].includes(detail.kind)){setAllowSnapshot(false);setSourceStatus(null);void check();}};
  const onFocus=()=>void check();window.addEventListener(WRITING_METRICS_CHANGED,onSaved);window.addEventListener('focus',onFocus);void check();
  return()=>{active=false;controller.abort();window.removeEventListener(WRITING_METRICS_CHANGED,onSaved);window.removeEventListener('focus',onFocus);};
 },[artifact?.id,project,sourceRefresh]);
 function change(values:Partial<Layout>){if(operation.current)return;setLayout(current=>({...current,...values}));}
 async function generate(){
  if(operation.current||exportPending.current)return;
  const op:PrintOperation={id:crypto.randomUUID().replaceAll('-',''),project,key,cancelled:false,submitted:false,controller:new AbortController(),cancelPending:false};operation.current=op;
  setBusy(true);setCancelling(false);setError('');setNotice('');setResult(null);
  try{
   const source=await api<{warnings:string[]}>(base+'/preview',{...selection,format:'docx',confirm_warnings:false},'POST');if(!liveOperation(op)||op.cancelled)return;
   const sameWarnings=JSON.stringify(source.warnings)===JSON.stringify(sourceWarnings);setSourceWarnings(source.warnings);if(source.warnings.length&&(!confirmed||!sameWarnings)){setConfirmed(false);return;}
   op.submitted=true;
   const row=await api<Artifact&{status?:string}>(base+'/print-preview',{...selection,format:'pdf',page_break:true,...layout,request_id:op.id,confirm_warnings:!source.warnings.length||confirmed},'POST',{signal:op.controller.signal});
   if(!liveOperation(op))return;
   if(op.cancelled||row.status==='CANCELLED'){setNotice(tr(row.status==='SUCCEEDED'?'cancelTooLate':'cancelled'));return;}
   setArtifact(row);setSourceStatus(null);setAllowSnapshot(false);setPage(1);setCount(row.pages);setRendered(false);setViewerError('');
  }catch(reason){if(liveOperation(op)&&!op.cancelled)setError((reason as {code?:string})?.code==='PRINT_ALREADY_RUNNING'?tr('alreadyRunning'):messageOf(reason));}
  finally{if(operation.current===op){operation.current=null;if(mounted.current){setBusy(false);setCancelling(false);}}}
 }
 async function exportPdf(){
  if(!artifact||exportPending.current||operation.current)return;exportPending.current=true;setExporting(true);setError('');const id=generation.current;
  try{
   const current=await api<SourceStatus>(base+'/print/'+artifact.id+'/source-status');if(id!==generation.current)return;setSourceStatus(current);
   if(current.status!=='CURRENT'&&!allowSnapshot){setNotice(tr('snapshotConsentRequired'));return;}
   const value=await api<{path:string;sha256:string}>(base+'/print/'+artifact.id+'/export',{directory:selection.directory||'',allow_snapshot:current.status!=='CURRENT'&&allowSnapshot},'POST');if(id===generation.current)setResult(value);
  }catch(reason){if(id===generation.current){if((reason as {code?:string})?.code==='PRINT_SNAPSHOT_STALE'){setAllowSnapshot(false);setSourceRefresh(value=>value+1);setError(tr('snapshotConsentRequired'));}else setError(messageOf(reason));}}
  finally{exportPending.current=false;if(mounted.current)setExporting(false);}
 }
 const canDownload=(sourceStatus?.status==='CURRENT'&&!checkingSource)||allowSnapshot;
 return <section className="night-panel print-edition"><h2>{tr('title')}</h2><p>{tr('intro')}</p><div className="print-layout-controls"><label>{tr('paper')}<select value={layout.paper_size} disabled={busy} onChange={event=>change({paper_size:event.target.value as Layout['paper_size']})}><option value="A5">A5 · 148 × 210 mm</option><option value="POCKET32">{tr('pocket')}</option></select></label><label>{tr('gutter')}<input type="number" min={0} max={12} step={1} value={layout.gutter_mm} disabled={busy} onChange={event=>change({gutter_mm:Math.max(0,Math.min(12,Number(event.target.value)||0))})}/></label><label className="check"><input type="checkbox" checked={layout.running_header} disabled={busy} onChange={event=>change({running_header:event.target.checked})}/>{tr('runningHeader')}</label><label className="check"><input type="checkbox" checked={layout.page_numbers} disabled={busy} onChange={event=>change({page_numbers:event.target.checked})}/>{tr('pageNumbers')}</label></div>
  <p className="print-hint">{tr('layoutHelp')}</p>{sourceWarnings.length>0&&<div className="print-warnings"><h3>{tr('sourceWarnings')}</h3><ul>{sourceWarnings.map((value,index)=><li key={index}>{value}</li>)}</ul><label className="check"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event=>setConfirmed(event.target.checked)}/>{tr('confirmWarnings')}</label></div>}
  <div className="print-actions"><button disabled={busy||exporting} onClick={()=>void generate()}>{busy?tr('generating'):artifact?tr('regenerate'):tr('generate')}</button>{busy&&<button disabled={cancelling} onClick={()=>void stop(operation.current)}>{cancelling?tr('cancelling'):tr('cancel')}</button>}{artifact&&<><button disabled={exporting||busy} onClick={()=>void exportPdf()}>{exporting?tr('exporting'):tr('export')}</button>{canDownload&&<a href={artifact.file_url} download={'NovelStudio-Print-'+artifact.id.slice(0,8)+'.pdf'}>{tr('download')}</a>}</>}</div>{busy&&<p role="status">{tr('progress')}</p>}{notice&&<p className="print-hint" role="status">{notice}</p>}{error&&<p role="alert" className="print-error">{error}</p>}
  {artifact&&<section className={'print-source-status '+(sourceStatus?.status==='CURRENT'?'current':'outdated')} aria-live="polite"><strong>{tr(checkingSource?'checkingSource':sourceStatus?.status==='CURRENT'?'sourceCurrent':sourceStatus?.status==='CHANGED'?'sourceChanged':'sourceUnknown')}</strong><p>{tr('snapshot')}</p><button disabled={checkingSource} onClick={()=>setSourceRefresh(value=>value+1)}>{tr('checkSource')}</button>{sourceStatus?.status!=='CURRENT'&&<label className="check"><input type="checkbox" checked={allowSnapshot} onChange={event=>setAllowSnapshot(event.target.checked)}/>{tr('allowSnapshot')}</label>}</section>}
  {result&&<p role="status" className="print-saved">{tr('exported')}<br/>{result.path}<br/>SHA-256: {result.sha256}</p>}
  <div ref={pane} className="print-viewer">{!artifact?<div className="print-empty"><h3>{tr('emptyTitle')}</h3><p>{tr('emptyHelp')}</p></div>:<><div className="print-page-controls">{artifact.chapter_pages&&artifact.chapter_pages.length>0&&<label>{tr('chapter')}<select aria-label={tr('chapter')} value="" onChange={event=>{if(event.target.value){setPage(Number(event.target.value));setRendered(false);}}}><option value="">{tr('jumpChapter')}</option>{artifact.chapter_pages.map(chapter=><option key={chapter.id} value={chapter.page??''} disabled={chapter.page===null}>{chapter.title} · {chapter.page!==null?tr('chapterPage',{page:chapter.page}):tr('chapterUnresolved')}</option>)}</select></label>}<button disabled={page<=1} onClick={()=>{setPage(value=>value-1);setRendered(false);}}>{tr('previous')}</button><label>{tr('page')}<input aria-label={tr('page')} type="number" min={1} max={count} value={page} onChange={event=>{setPage(Math.max(1,Math.min(count,Number(event.target.value)||1)));setRendered(false);}}/></label><span>/ {count}</span><button disabled={page>=count} onClick={()=>{setPage(value=>value+1);setRendered(false);}}>{tr('next')}</button></div>
    <p className="print-hint">{tr('artifactInfo',{paper:artifact.paper_size,pages:artifact.pages,width:artifact.width_mm,height:artifact.height_mm})}</p>{viewerError&&<p role="alert">{tr('viewerError')} {viewerError}</p>}<Suspense fallback={<p role="status">{tr('loadingPdf')}</p>}><ReferencePDF key={artifact.id} url={artifact.file_url} page={page} count={count} width={width} onLoad={setCount} onError={reason=>setViewerError(String(reason))} onRender={()=>setRendered(true)}/></Suspense><p className="print-hint" role="status">{rendered?tr('pageRendered',{page}):tr('renderingPage')}</p>
    <details><summary>{tr('verification')}</summary><p>SHA-256: {artifact.sha256}</p><p>{tr('snapshot')}</p></details>
   </>}</div>
  {artifact&&artifact.layout_warnings.length>0&&<section className="print-warnings"><h3>{tr('layoutWarnings')}</h3>{artifact.layout_warnings.map((warning,index)=><article key={index}><b>{tr('longParagraph',{chapter:warning.chapter_number,line:warning.line,count:warning.characters})}</b><blockquote>{warning.snippet}…</blockquote>{onOpen&&warning.path&&warning.document_revision&&warning.evidence&&<button onClick={()=>onOpen(warning.path!,{exact:warning.exact,start:warning.start,end:warning.end,prefix:warning.prefix,suffix:warning.suffix,document_revision:warning.document_revision,evidence:true})}>{tr('openSource')}</button>}</article>)}</section>}
  <details className="print-limits"><summary>{tr('limitsTitle')}</summary><p>{tr('limits')}</p><p>{tr('fontFallback')}</p><p>{tr('offline')}</p></details>
 </section>;
}
