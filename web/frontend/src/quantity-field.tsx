import {useEffect,useState} from 'react';
import {OptionalNumberInput} from './number-input';
export function QuantityField({label,value,defaultUnit='',minimum,maximum,unitLabel,onChange}:{label:string;value:any;defaultUnit?:string;minimum?:number;maximum?:number;unitLabel:string;onChange:(v:any)=>void}){
 const [unit,setUnit]=useState(value?.unit??defaultUnit);
 useEffect(()=>{setUnit(value?.unit??defaultUnit);},[value?.unit,defaultUnit]);
 return <div className="ws-quantity"><OptionalNumberInput aria-label={label} value={value?.value??undefined} min={minimum??-Number.MAX_SAFE_INTEGER} max={maximum??Number.MAX_SAFE_INTEGER} precision={6} onValueChange={number=>onChange(number===undefined?null:{value:number,unit})}/><input aria-label={label+' · '+unitLabel} placeholder={defaultUnit||unitLabel} value={unit} onChange={e=>{setUnit(e.target.value);if(typeof value?.value==='number')onChange({...value,unit:e.target.value});}}/></div>;
}
