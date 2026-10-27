import {useEffect,useRef,useState,type InputHTMLAttributes} from 'react';

type Props=Omit<InputHTMLAttributes<HTMLInputElement>,'type'|'value'|'defaultValue'|'onChange'|'min'|'max'> & {
 value:number;min:number;max:number;precision?:number;onValueChange:(value:number)=>void;
};
/** Keep an incomplete number editable; enforce bounds when the user finishes. */
export function NumberInput({value,min,max,precision=0,onValueChange,onBlur,onKeyDown,...rest}:Props){
 const [text,setText]=useState(String(value)),editing=useRef(false);
 useEffect(()=>{if(!editing.current)setText(String(value));},[value]);
 const digits=Math.max(0,Math.min(6,Math.trunc(precision)));
 const rounded=(number:number)=>Math.round(number*10**digits)/10**digits;
 const valid=(raw:string)=>raw.trim()!==''&&Number.isFinite(Number(raw))&&(digits>0||Number.isInteger(Number(raw)))&&Number(raw)>=min&&Number(raw)<=max;
 function finish(){
  const number=text.trim()===''||!Number.isFinite(Number(text))?value:Number(text);
  const next=Math.max(min,Math.min(max,rounded(number)));
  setText(String(next));if(next!==value)onValueChange(next);
 }
 return <input {...rest} type="number" min={min} max={max} step={rest.step??1} value={text}
  onFocus={e=>{editing.current=true;rest.onFocus?.(e);}}
  onChange={e=>{const raw=e.target.value;setText(raw);if(valid(raw)&&Number(raw)!==value)onValueChange(Number(raw));}}
  onBlur={e=>{editing.current=false;finish();onBlur?.(e);}}
  onKeyDown={e=>{onKeyDown?.(e);if(e.key==='Enter'&&!e.defaultPrevented){e.preventDefault();e.currentTarget.blur();}}}/>;
}

/** Optional model parameters keep decimal/incomplete input local; blank means default. */
type OptionalProps=Omit<Props,'value'|'onValueChange'> & {value:number|undefined;onValueChange:(value:number|undefined)=>void};
export function OptionalNumberInput({value,min,max,precision=2,onValueChange,onBlur,onKeyDown,...rest}:OptionalProps){
 const [text,setText]=useState(value===undefined?'':String(value)),editing=useRef(false);
 useEffect(()=>{if(!editing.current)setText(value===undefined?'':String(value));},[value]);
 const digits=Math.max(0,Math.min(6,precision));
 function finish(){
  if(!text.trim()){setText('');onValueChange(undefined);return;}
  const number=Number(text);if(!Number.isFinite(number)){setText(value===undefined?'':String(value));return;}
  const next=Math.round(Math.max(min,Math.min(max,number))*10**digits)/10**digits;setText(String(next));if(next!==value)onValueChange(next);
 }
 return <input {...rest} type="text" inputMode={digits?'decimal':'numeric'} value={text} onFocus={e=>{editing.current=true;rest.onFocus?.(e);}} onChange={e=>{const raw=e.target.value;setText(raw);if(!raw.trim()){onValueChange(undefined);return;}if(/^-?\d+(?:\.\d+)?$/.test(raw)){const number=Number(raw);if(number>=min&&number<=max&&(digits>0||Number.isInteger(number))&&number!==value)onValueChange(number);}}} onBlur={e=>{editing.current=false;finish();onBlur?.(e);}} onKeyDown={e=>{onKeyDown?.(e);if(e.key==='Enter'&&!e.defaultPrevented){e.preventDefault();e.currentTarget.blur();}}}/>;
}
