import {useEffect,useRef,useState} from 'react';
import {api} from './api';
import {t,useUiTranslation} from './i18n';
const errorMessage=(e:unknown)=>t('creativeTools:errors.'+((e as {code?:string})?.code||'unknown'),{defaultValue:String(e)});
export function LocationMapLinks({project,entityId,onMap}:{project:string;entityId:string;onMap?:(id:string)=>void}){
 useUiTranslation('creativeTools');const epoch=useRef(0);const[rows,setRows]=useState<{id:string;name:string}[]|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{epoch.current++;setRows(null);setError('');setBusy(false);return()=>{epoch.current++}},[project,entityId]);
 return <section><button disabled={busy} onClick={()=>{const ticket=epoch.current;setBusy(true);setError('');void api<{maps:{id:string;name:string;pins:{entity_id:string}[]}[]}>('/api/projects/'+project+'/world-maps').then(v=>{if(ticket===epoch.current)setRows(v.maps.filter(m=>m.pins.some(p=>p.entity_id===entityId)))}).catch(e=>{if(ticket===epoch.current)setError(errorMessage(e))}).finally(()=>{if(ticket===epoch.current)setBusy(false)})}}>{t('creativeTools:map.findMaps')}</button>{error&&<p role="alert">{error}</p>}{rows&&<div>{!rows.length&&<p>{t('creativeTools:map.noLinkedMaps')}</p>}{rows.map(m=><button key={m.id} disabled={!onMap} onClick={()=>onMap?.(m.id)}>{m.name}</button>)}</div>}</section>
}
