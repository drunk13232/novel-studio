import {lazy,Suspense,useState} from 'react';
import {api} from './api';
import {type Data} from './library-shared';
import {StudioDialog} from './studio-dialog';
import {t,useUiTranslation} from './i18n';
import './creative-spaces.css';
const Roleplay=lazy(()=>import('./roleplay-workbench').then(m=>({default:m.RoleplayWorkbench})));
const WorldLab=lazy(()=>import('./world-logic').then(m=>({default:m.WorldLogicLab})));
export type StudioOrigin={path:string;revision:string;chapter?:number;quote:string;question?:string;initialTab?:'roleplay'|'logic'};
export default function CreativeLabDialog({project,origin,characters,onClose,onMaterial,onOpen,onSource}:{project:string;origin:StudioOrigin;characters:string[];onClose:()=>void;onMaterial:(id:string)=>Promise<void>;onOpen:(path:string)=>void;onSource:(type:string,id:string)=>void}){
 useUiTranslation(['spaces','common']);const [tab,setTab]=useState(origin.initialTab||'roleplay'),[visited,setVisited]=useState([origin.initialTab||'roleplay']),[seed,setSeed]=useState<Data>({text:origin.question||origin.quote,nonce:crypto.randomUUID()}),[error,setError]=useState('');const [dirty,setDirty]=useState(false);
 const [roleSeed]=useState({text:origin.quote,characters,chapter:origin.chapter,nonce:crypto.randomUUID()});
 async function take(value:Data){setError('');try{const r=await api<Data>('/api/projects/'+project+'/writing-assist/materials',{...value,origin:{path:origin.path,revision:origin.revision,chapter:origin.chapter,quote:origin.quote},confirm:true},'POST');await onMaterial(r.note_id);}catch(e){setError(String((e as any).technicalDetail||e));}}
 function close(){if(!dirty||window.confirm(t('spaces:discardLab')))onClose();}
 function choose(v:'roleplay'|'logic'){setTab(v);setVisited(a=>a.includes(v)?a:[...a,v]);}
 return <StudioDialog title={t('spaces:labTitle')} className="creative-lab-dialog" onClose={close}><p className="muted">{t('spaces:labIntro')}</p><div className="creative-space-tabs"><button className={tab==='roleplay'?'selected':''} onClick={()=>choose('roleplay')}>{t('spaces:people')}</button><button className={tab==='logic'?'selected':''} onClick={()=>choose('logic')}>{t('spaces:rules')}</button><button onClick={close}>{t('spaces:returnWriting')}</button></div>{error&&<p role="alert" className="studio-alert">{error}</p>}<div className="creative-lab-body"><Suspense fallback={<p>{t('common:loading')}</p>}>{visited.includes('roleplay')&&<div hidden={tab!=='roleplay'}><Roleplay project={project} seed={roleSeed} onOpen={onOpen} onSource={onSource} onMaterial={take} onExperiment={text=>{setSeed({text,nonce:crypto.randomUUID()});choose('logic');}}/></div>}{visited.includes('logic')&&<div hidden={tab!=='logic'}><WorldLab project={project} seed={seed as any} onDirty={setDirty} onSource={onSource} onMaterial={take}/></div>}</Suspense></div></StudioDialog>;
}
