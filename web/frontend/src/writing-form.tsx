import {t as translateUI,useUiTranslation} from './i18n';
type D=Record<string,any>;
import './writing-modes.css';
export const formNames:Record<string,string>={get short(){return translateUI("projects:short");},get novella(){return translateUI("projects:novella");},get novel(){return translateUI("projects:novel");},get anthology(){return translateUI("projects:anthology");},get undecided(){return translateUI("projects:undecided");}};
export function writingDefaults(form='undecided'){
 const light=['short','undecided','anthology'].includes(form);
 return {form,target_characters:null as number|null,structure_mode:light?'free':'chapters',planning_depth:light?'minimal':'standard',interview_depth:light?'quick':'standard',auto_suggestions:false,template_id:'free',structure_reference:'free',body_id:null};
}
export function FormFields({value,onChange,disabled=false}:{value:D;onChange:(value:D)=>void;disabled?:boolean}){
 useUiTranslation(["projects"]);

 return <div className="wm-form-fields"><label>{translateUI("projects:form")}<select aria-label={translateUI("projects:form")} disabled={disabled} value={value.form} onChange={e=>onChange({...writingDefaults(e.target.value),target_characters:value.target_characters,body_id:value.body_id})}>{Object.entries(formNames).map(([k,n])=><option key={k} value={k}>{n}</option>)}</select></label><label>{translateUI("projects:targetHanCount")}<input disabled={disabled} aria-label={translateUI("projects:targetChineseCharacterCount")} type="number" min={0} value={value.target_characters??''} onChange={e=>onChange({...value,target_characters:e.target.value===''?null:+e.target.value})}/></label><label>{translateUI("projects:interviewDepth")}<select disabled={disabled} value={value.interview_depth} onChange={e=>onChange({...value,interview_depth:e.target.value})}><option value="quick">{translateUI("projects:quick")}</option><option value="standard">{translateUI("projects:standard")}</option><option value="deep">{translateUI("projects:depthLevel")}</option></select></label><small className="wm-hint">{value.form==='short'?translateUI("projects:shortStoryLengthGuidance"):value.form==='novella'?translateUI("projects:novellaLengthGuidance"):value.form==='novel'?translateUI("projects:novelLengthGuidance"):translateUI("projects:decideLengthLater")}{translateUI("projects:characterCountReferenceNotice")}</small></div>;
}
