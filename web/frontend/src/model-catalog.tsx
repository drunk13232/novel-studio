import {useState} from 'react';
import {api} from './api';
import {t,useUiTranslation} from './i18n';
type D=Record<string,any>;
let pending:Promise<D>|null=null;
// One in-flight discovery per frontend; never starts a model Turn or edits Codex config.
export function refreshCodexCatalog():Promise<D>{
 if(!pending)pending=api<D>('/api/ai/codex/models',{},'POST').then(result=>{window.dispatchEvent(new CustomEvent('ai-catalog-changed',{detail:result}));return result;}).finally(()=>{pending=null;});
 return pending;
}
export function CodexModelOptions({settings,defaultValue='codex'}:{settings:D;defaultValue?:string}){
 useUiTranslation('ai-controls');
 return <><option value={defaultValue}>{t('ai-controls:codexDefault')}</option>{!!settings.codex_models?.length&&<optgroup label={t('ai-controls:codexModels')}>{settings.codex_models.map((m:D)=><option key={m.id} value={'codex::'+m.id}>{m.display_name||m.id} · {m.id}</option>)}</optgroup>}</>;
}
export function CodexCatalogButton({onCatalog,disabled=false}:{onCatalog?:(value:D)=>void;disabled?:boolean}){
 useUiTranslation('ai-controls');const [busy,B]=useState(false),[error,E]=useState(''),[notice,N]=useState('');
 return <span className="codex-catalog-control"><button type="button" disabled={disabled||busy} onClick={()=>{B(true);E('');N('');void refreshCodexCatalog().then(v=>{onCatalog?.(v);N(t('ai-controls:catalogLoaded'));}).catch(e=>E(String(e))).finally(()=>B(false));}}>{t('ai-controls:'+(busy?'working':'refreshCatalog'))}</button>{notice&&<small role="status">{notice}</small>}{error&&<small role="alert">{error}</small>}</span>;
}
