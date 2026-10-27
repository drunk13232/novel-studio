import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {EntityReferences} from './knowledge-center';
import {base,ErrorNote,Empty,useUnsavedChanges,upload,saveJSON} from './library-shared';
import {StudioDialog} from './studio-dialog';
import {NumberInput} from './number-input';
import {t,useUiTranslation} from './i18n';
import './creative-tools.css';
type D=Record<string,any>;
const tr=(key:string,values?:Record<string,unknown>)=>t('creativeTools:map.'+key,values);
const id=(prefix:string)=>prefix+'_'+crypto.randomUUID().replaceAll('-','');
const errorMessage=(e:unknown)=>t('creativeTools:errors.'+((e as {code?:string})?.code||'unknown'),{defaultValue:String(e)});
export function WorldMap({project,onEntity,onOpen,initialMap}:{project:string;initialMap?:string;onEntity?:(type:string,id:string)=>void;onOpen?:(node:D)=>void}){
 useUiTranslation('creativeTools');
 const [data,setData]=useState<D|null>(null),[maps,setMaps]=useState<D[]>([]),[selected,setSelected]=useState(''),[pinId,setPinId]=useState(''),[mode,setMode]=useState('inspect'),[entity,setEntity]=useState(''),[shapeName,setShapeName]=useState(''),[points,setPoints]=useState<D[]>([]),[zoom,setZoom]=useState(1),[dirty,setDirty]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[search,setSearch]=useState(''),[confirm,setConfirm]=useState<'reload'|'remove'|'switch'|null>(null),[fullImage,setFullImage]=useState(false),[imageError,setImageError]=useState(false),[conflict,setConflict]=useState(false);
 const generation=useRef(0),live=useRef({project,maps,selected}),saving=useRef<symbol|null>(null),past=useRef<D[][]>([]),future=useRef<D[][]>([]),group=useRef(''),saved=useRef('[]'),nextMap=useRef<string|null>(null);
 live.current={project,maps,selected};
 const svg=useRef<SVGSVGElement>(null),drag=useRef<string>('');const url=base(project)+'/world-maps';
 useUnsavedChanges(dirty||points.length>0,tr('title'));
 function apply(rows:D[],newHistory=true,key=''){
  if(JSON.stringify(rows)===JSON.stringify(live.current.maps))return;
  if(newHistory){if(!key||key!==group.current)past.current=[...past.current,structuredClone(live.current.maps)].slice(-40);future.current=[];group.current=key;}
  live.current={...live.current,maps:rows};setMaps(rows);setDirty(JSON.stringify(rows)!==saved.current);
 }
 function update(delta:D,key=''){apply(live.current.maps.map(m=>m.id===live.current.selected?{...m,...delta}:m),true,key)}
 function undo(redo=false){
  if(points.length){if(!redo)setPoints(rows=>rows.slice(0,-1));return;}
  const source=redo?future:past,target=redo?past:future;if(!source.current.length||busy)return;
  const rows=source.current.at(-1)!;source.current=source.current.slice(0,-1);target.current=[...target.current,structuredClone(live.current.maps)].slice(-40);group.current='';apply(rows,false);setPoints([]);
  if(!rows.some(m=>m.id===selected))setSelected(rows[0]?.id||'');
 }
 async function refresh(accept=false){
  if((dirty||points.length)&&!accept){setConfirm('reload');return;}
  const ticket=generation.current;setBusy(true);setError('');
  try{const v=await api<D>(url);if(ticket!==generation.current)return;setData(v);live.current={...live.current,maps:v.maps};setMaps(v.maps);saved.current=JSON.stringify(v.maps);setDirty(false);setPoints([]);setConflict(false);past.current=[];future.current=[];group.current='';setSelected(s=>v.maps.some((m:D)=>m.id===s)?s:v.maps[0]?.id||'');setPinId('');setConfirm(null)}
  catch(e){if(ticket===generation.current)setError(errorMessage(e))}
  finally{if(ticket===generation.current)setBusy(false)}
 }
 useEffect(()=>{
  const ticket=++generation.current;saving.current=null;setData(null);setMaps([]);setBusy(false);setDirty(false);setError('');setSearch('');setConfirm(null);setConflict(false);setPoints([]);setMode('inspect');past.current=[];future.current=[];group.current='';
  void api<D>(url).then(v=>{if(ticket===generation.current){setData(v);setMaps(v.maps);saved.current=JSON.stringify(v.maps);setSelected(v.maps.find((m:D)=>m.id===initialMap)?.id||v.maps[0]?.id||'');setPinId('')}}).catch(e=>{if(ticket===generation.current)setError(errorMessage(e))});
  return()=>{generation.current++};
 },[url]);
 useEffect(()=>{setFullImage(false);setImageError(false);drag.current='';},[selected,maps.find(m=>m.id===selected)?.background]);
 function position(e:React.PointerEvent<SVGSVGElement>){const rect=svg.current!.getBoundingClientRect();return {x:Math.max(0,Math.min(1000,(e.clientX-rect.left)*1000/rect.width)),y:Math.max(0,Math.min(1000,(e.clientY-rect.top)*1000/rect.height))}}
 function chooseMap(identifier:string,discard=false){if(points.length&&!discard){nextMap.current=identifier;setConfirm('switch');return;}setSelected(identifier);setPinId('');setPoints([]);setMode('inspect');group.current=''}
 function addMap(){const row={id:id('map'),name:tr('untitled'),parent_id:selected,background:'',scale_label:'',coordinate_label:'',pins:[],shapes:[]};apply([...live.current.maps,row]);chooseMap(row.id)}
 async function save(){
  if(!data||saving.current)return;
  if(points.length){setError(tr('drawingUnfinished'));return;}
  if(live.current.maps.some(m=>!m.name.trim()||m.shapes.some((shape:D)=>!shape.name.trim()))){setError(tr('nameRequired'));return;}
  const submitted=structuredClone(live.current.maps),ticket=generation.current,operation=Symbol();saving.current=operation;setBusy(true);setError('');
  try{const v=await api<D>(url,{etag:data.etag,maps:submitted},'PUT');if(ticket!==generation.current)return;setData(v);saved.current=JSON.stringify(v.maps);setConflict(false);if(JSON.stringify(live.current.maps)===JSON.stringify(submitted)){live.current={...live.current,maps:v.maps};setMaps(v.maps);setDirty(false)}else setDirty(true)}
  catch(e){if(ticket===generation.current){setError(errorMessage(e));if((e as {code?:string}).code==='MAP_STALE')setConflict(true)}}
  finally{if(saving.current===operation)saving.current=null;if(ticket===generation.current)setBusy(false)}
 }
 async function image(file:File){const ticket=generation.current,mapId=selected;setBusy(true);setError('');try{const asset=await upload<D>(base(project)+'/assets/import?name='+encodeURIComponent(file.name),file);if(ticket!==generation.current)return;apply(live.current.maps.map(m=>m.id===mapId?{...m,background:asset.id}:m));setData(d=>d?{...d,images:[...d.images,asset]}:d)}catch(e){if(ticket===generation.current)setError(errorMessage(e))}finally{if(ticket===generation.current)setBusy(false)}}
 async function createLocation(){if(!shapeName.trim())return;const ticket=generation.current,mapId=selected,name=shapeName.trim();setBusy(true);setError('');try{const e=await api<D>(base(project)+'/bible/entities',{entity:{name,category:'location',status:'DRAFT',source:'USER',canon_level:'REFERENCE'}},'POST');if(ticket!==generation.current)return;setData(d=>d?{...d,locations:[...d.locations,e]}:d);if(live.current.selected===mapId){setEntity(e.id);setMode('pin');setShapeName(value=>value.trim()===name?'':value)}}catch(e){if(ticket===generation.current)setError(errorMessage(e))}finally{if(ticket===generation.current)setBusy(false)}}
 const current=maps.find(m=>m.id===selected),pin=current?.pins.find((p:D)=>p.id===pinId),location=data?.locations.find((e:D)=>e.id===pin?.entity_id);
 function updatePin(delta:D,key=''){if(pin&&current)update({pins:current.pins.map((p:D)=>p.id===pin.id?{...p,...delta}:p)},key)}
 function coordinate(axis:string,raw:string){const value=Number(raw);if(raw.trim()&&Number.isFinite(value)&&value>=0&&value<=1000)updatePin({[axis]:value},'coordinate:'+pinId+':'+axis)}
 function download(){saveJSON('world-map-unsaved-draft.json',{schema_version:1,kind:'AUTHOR_UNSAVED_MAP_DRAFT',maps:live.current.maps,pending_drawing:points.length?{map_id:selected,kind:mode,name:shapeName,points}:undefined})}
 if(!data)return <div className="creative-tool-page"><p role="status">{error||tr('loading')}</p>{error&&<button onClick={()=>void refresh(true)}>{tr('reload')}</button>}</div>;
 return <div className="creative-tool-page" onKeyDown={e=>{
  if((e.ctrlKey||e.metaKey)&&!e.altKey&&e.key.toLowerCase()==='s'){e.preventDefault();e.stopPropagation();void save();return;}
  if((e.ctrlKey||e.metaKey)&&!e.altKey&&e.key.toLowerCase()==='z'&&!(e.target as Element).closest('input,textarea,select,[contenteditable="true"]')){e.preventDefault();undo(e.shiftKey)}
 }}>
  <header><h1>{tr('title')}</h1><p>{tr('boundary')}</p></header><ErrorNote text={error}/>
  {conflict&&<p role="status" className="studio-notice">{tr('conflictHelp')}</p>}
  <div className="creative-tool-actions"><button onClick={addMap} disabled={busy||maps.length>=30||points.length>0}>{tr('new')}</button><button disabled={!dirty||busy} onClick={()=>void save()}>{busy?tr('saving'):tr('save')}</button><button disabled={busy||!past.current.length} onClick={()=>undo()}>{tr('undo')}</button><button disabled={busy||points.length>0||!future.current.length} onClick={()=>undo(true)}>{tr('redo')}</button><button disabled={busy} onClick={()=>void refresh()}>{tr('reload')}</button><button disabled={!maps.length} onClick={download}>{tr('downloadDraft')}</button><span role="status">{dirty||points.length?tr('unsaved'):tr('saved')}</span></div>
  <div className="map-layout">
   <aside className="night-panel"><h2>{tr('maps')}</h2><input aria-label={tr('search')} placeholder={tr('search')} value={search} onChange={e=>setSearch(e.target.value)}/>{maps.filter(m=>m.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())).map(m=><button key={m.id} aria-current={m.id===selected?'page':undefined} className={m.id===selected?'selected':''} onClick={()=>chooseMap(m.id)}>{m.parent_id?'↳ ':''}{m.name}</button>)}{!maps.length&&<Empty text={tr('empty')}/>}<p>{tr('backup')}</p></aside>
   {current&&<><section className="night-panel map-editor">
    <div className="creative-tool-actions"><label>{tr('name')}<input maxLength={100} value={current.name} onBlur={()=>{group.current=''}} onChange={e=>update({name:e.target.value},'name:'+selected)}/></label><label>{tr('parent')}<select value={current.parent_id} onChange={e=>update({parent_id:e.target.value})}><option value="">—</option>{maps.filter(m=>m.id!==current.id).map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label><label>{tr('zoom')}<input type="range" min={.5} max={2} step={.1} value={zoom} onChange={e=>setZoom(+e.target.value)}/></label></div>
    <div className="creative-tool-actions"><label>{tr('background')}<input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file)void image(file);e.target.value=''}}/></label><button onClick={()=>update({background:''})}>{tr('blank')}</button>{current.background&&<button onClick={()=>{setFullImage(v=>!v);setImageError(false)}}>{fullImage?tr('usePreview'):tr('loadOriginal')}</button>}<label>{tr('coordinates')}<input maxLength={150} value={current.coordinate_label} onBlur={()=>{group.current=''}} onChange={e=>update({coordinate_label:e.target.value},'coordinate-label:'+selected)}/></label><label>{tr('scale')}<input maxLength={150} value={current.scale_label} onBlur={()=>{group.current=''}} onChange={e=>update({scale_label:e.target.value},'scale:'+selected)}/></label></div>
    <div className="creative-tool-actions"><select aria-label={tr('mode')} value={mode} onChange={e=>{if(points.length){setError(tr('drawingUnfinished'));return;}setMode(e.target.value)}}>{['inspect','pin','route','region'].map(v=><option key={v} value={v}>{tr(v)}</option>)}</select><select aria-label={tr('location')} value={entity} onChange={e=>setEntity(e.target.value)}><option value="">{tr('choose')}</option>{data.locations.map((l:D)=><option key={l.id} value={l.id}>{l.name}</option>)}</select><input aria-label={tr('shapeName')} placeholder={tr('shapeName')} value={shapeName} maxLength={100} onChange={e=>setShapeName(e.target.value)}/><button disabled={busy||!shapeName.trim()} onClick={()=>void createLocation()}>{tr('newLocation')}</button>{['route','region'].includes(mode)&&<><button disabled={!shapeName.trim()||points.length<(mode==='region'?3:2)} onClick={()=>{update({shapes:[...current.shapes,{id:id('shape'),name:shapeName.trim(),kind:mode,points}]});setPoints([]);setShapeName('')}}>{tr('finish')}</button><button disabled={!points.length} onClick={()=>setPoints(p=>p.slice(0,-1))}>{tr('undoPoint')}</button><button disabled={!points.length} onClick={()=>setPoints([])}>{tr('cancelDrawing')}</button></>}</div>
    <p className="muted">{tr('instructions')}</p>{imageError&&<p role="status" className="studio-notice">{tr('imageMissing')}</p>}
    <div className="map-scroll"><svg ref={svg} viewBox="0 0 1000 1000" role="img" aria-label={current.name} style={{width:zoom*100+'%'}} onPointerDown={e=>{
     if((e.target as Element).closest('[data-pin]'))return;const p=position(e);
     if(mode==='pin'&&entity&&current.pins.length<500){const next={id:id('pin'),entity_id:entity,label:'',child_map:'',...p};update({pins:[...current.pins,next]});setPinId(next.id);setMode('inspect')}
     else if(['route','region'].includes(mode)&&points.length<200)setPoints([...points,p]);
    }} onPointerMove={e=>{if(!drag.current)return;const p=position(e);update({pins:current.pins.map((x:D)=>x.id===drag.current?{...x,...p}:x)},'drag:'+drag.current)}} onPointerUp={()=>{drag.current='';group.current=''}} onPointerCancel={()=>{drag.current='';group.current=''}}>
     {current.background&&!imageError&&<image href={base(project)+'/assets/'+current.background+'/file'+(fullImage?'':'?thumbnail=true')} width="1000" height="1000" preserveAspectRatio="xMidYMid meet" pointerEvents="none" onError={()=>setImageError(true)}/>}
     {current.shapes.map((s:D)=><g key={s.id}><polyline points={[...s.points,...(s.kind==='region'?[s.points[0]]:[])].map((p:D)=>p.x+','+p.y).join(' ')} fill={s.kind==='region'?'var(--wash,#e0efea)':'none'} fillOpacity={.4} stroke="var(--accent,#27645c)" strokeWidth={3}/><text x={s.points[0].x} y={s.points[0].y-10}>{s.name}</text></g>)}
     {points.length>0&&<polyline points={points.map(p=>p.x+','+p.y).join(' ')} fill="none" stroke="var(--accent,#27645c)" strokeWidth={3} strokeDasharray="6 4"/>}
     {current.pins.map((p:D)=><g data-pin={p.id} key={p.id} tabIndex={0} role="button" aria-label={data.locations.find((e:D)=>e.id===p.entity_id)?.name||p.entity_id} transform={'translate('+p.x+' '+p.y+')'} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setPinId(p.id)}}} onPointerDown={e=>{e.stopPropagation();setPinId(p.id);if(mode==='inspect'){group.current='';drag.current=p.id;svg.current?.setPointerCapture?.(e.pointerId)}}}><circle r={pinId===p.id?13:10} fill="var(--accent,#27645c)" stroke="white" strokeWidth={3}/><text y={-20} textAnchor="middle">{p.label||data.locations.find((l:D)=>l.id===p.entity_id)?.name||tr('missing')}</text></g>)}
     <text x={20} y={970}>{current.coordinate_label} · {current.scale_label}</text>
    </svg></div>
    {current.shapes.map((s:D)=><div className="creative-tool-actions" key={s.id}><input aria-label={tr('renameShape')} maxLength={100} value={s.name} onBlur={()=>{group.current=''}} onChange={e=>update({shapes:current.shapes.map((v:D)=>v.id===s.id?{...v,name:e.target.value}:v)},'shape:'+s.id)}/><span>{tr(s.kind)}</span><button onClick={()=>update({shapes:current.shapes.filter((v:D)=>v.id!==s.id)})}>{tr('remove')}</button></div>)}
    <button disabled={busy||!!maps.find(m=>m.parent_id===current.id)} onClick={()=>setConfirm('remove')}>{tr('removeMap')}</button>
   </section><aside className="night-panel">{pin?<>
    <h2>{location?.name||tr('missing')}</h2><p>{location?.summary||tr('noSummary')}</p><p>{location?.status} · ({pin.x.toFixed(1)}, {pin.y.toFixed(1)})</p>
    {!location&&<p className="studio-notice">{tr('repairLocation')}</p>}
    <label>{tr('location')}<select value={pin.entity_id} onChange={e=>updatePin({entity_id:e.target.value})}>{!location&&<option value={pin.entity_id}>{tr('missing')}</option>}{data.locations.map((l:D)=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
    <label>{tr('pinLabel')}<input maxLength={100} value={pin.label} onBlur={()=>{group.current=''}} onChange={e=>updatePin({label:e.target.value},'pin-label:'+pin.id)}/></label>
    <div className="map-coordinate-fields">{['x','y'].map(axis=><label key={axis}>{axis.toUpperCase()}<NumberInput key={pin.id+axis} aria-label={tr('coordinateValue',{axis:axis.toUpperCase()})} min={0} max={1000} step={.01} precision={2} value={pin[axis]} onBlur={()=>{group.current=''}} onValueChange={value=>coordinate(axis,String(value))}/></label>)}</div>
    <button disabled={!location} onClick={()=>onEntity?.('entity',pin.entity_id)}>{tr('openEntry')}</button>
    <label>{tr('child')}<select value={pin.child_map} onChange={e=>updatePin({child_map:e.target.value})}><option value="">—</option>{maps.filter(m=>m.id!==selected).map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
    {pin.child_map&&<button onClick={()=>chooseMap(pin.child_map)}>{tr('openChild')}</button>}
    <button onClick={()=>{update({pins:current.pins.filter((p:D)=>p.id!==pin.id)});setPinId('')}}>{tr('removePin')}</button>
    <EntityReferences project={project} target={{type:'entity',id:pin.entity_id}} onSelect={target=>onEntity?.(target.type,target.id)} onOpen={onOpen}/>
   </>:<p>{tr('selectPin')}</p>}</aside></>}
  </div>
  {confirm&&<StudioDialog title={confirm==='remove'?tr('removeMap'):confirm==='switch'?tr('switchMap'):tr('reload')} onClose={()=>setConfirm(null)}><p>{confirm==='remove'?tr('removeConfirm'):confirm==='switch'?tr('switchConfirm'):tr('reloadConfirm')}</p><div className="creative-tool-actions"><button onClick={download}>{tr('downloadDraft')}</button><button disabled={busy} onClick={()=>{
   if(confirm==='reload')void refresh(true);
   else if(confirm==='switch'){chooseMap(nextMap.current||'',true);nextMap.current=null;setConfirm(null)}
   else{const identifier=selected;apply(live.current.maps.filter(m=>m.id!==identifier).map(m=>({...m,pins:m.pins.map((p:D)=>p.child_map===identifier?{...p,child_map:''}:p)})));chooseMap(live.current.maps[0]?.id||'');setConfirm(null)}
  }}>{tr('confirm')}</button></div></StudioDialog>}
 </div>;
}
