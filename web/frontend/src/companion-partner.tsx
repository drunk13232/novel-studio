import {useEffect,useRef,useState} from 'react';
import {CompanionPet} from './companion-pet';
import type {PetController} from './companion-pet';
type D=Record<string,any>;
export function CompanionPartner({character,model,profile,cfg,controller,onMove,onChat,onClose}:{character:string;model:D|null;profile:D;cfg:D;controller:React.MutableRefObject<((type:string,data?:D)=>void)|null>;onMove:(x:number,y:number)=>void;onChat:()=>void;onClose:()=>void}){
 const frame=useRef<HTMLIFrameElement>(null),pet=useRef<PetController|null>(null),[status,S]=useState(''),[pass,P]=useState(false);
 const latest=useRef({model,profile,cfg});latest.current={model,profile,cfg};
 useEffect(()=>{const token=crypto.randomUUID();const post=(type:string,data:D={})=>frame.current?.contentWindow?.postMessage({channel:'novel-live2d',token,type,...data},location.origin);controller.current=post;
 const receive=(e:MessageEvent)=>{if(e.origin!==location.origin||e.source!==frame.current?.contentWindow||e.data?.channel!=='novel-live2d')return;const m=e.data;
 if(m.type==='frame-ready'){const {model,profile,cfg}=latest.current;if(model)post('load',{spec:{character,url:'/api/studio/live2d/models/'+model.id+'/'+model.model.split('/').map(encodeURIComponent).join('/'),mouth_ids:model.mouth_ids,position:[cfg.offset_x,cfg.offset_y],scale:cfg.scale,display_aspect:model.display_aspect,canvas_aspect:model.canvas_aspect,behaviors:{...model.behaviors,...profile.motions},expressions:profile.expressions,quiet:cfg.quiet,autonomous:cfg.autonomous}});return;}
 if(m.token!==token)return;
 if(m.type==='pet-pointer')pet.current?.pointer(m);else if(m.type==='pet-activate')pet.current?.activate();else if(m.type==='status')S(m.text);else if(m.type==='error')S(m.text);else if(m.type==='motion')S(m.group);else if(m.type==='behavior')S(m.state);
 };window.addEventListener('message',receive);return()=>{controller.current=null;window.removeEventListener('message',receive);};},[character,model?.id,!!cfg.animation]);
 useEffect(()=>{controller.current?.('policy',{quiet:cfg.quiet,autonomous:cfg.autonomous});},[cfg.quiet,cfg.autonomous]);
 return <CompanionPet controller={pet} name={character==='rem'?'蕾姆':'朝武芳乃'} size={cfg.size} x={cfg.partner_x} y={cfg.partner_y} passthrough={pass} panelOpen={false} onPanel={onChat} onMove={onMove} onPassthrough={()=>P(!pass)} onClose={onClose} status={status} panel={null}><div className="lc-stage">{model&&cfg.animation?<iframe key={model.id} ref={frame} src="/live2d/frame.html" title={'Live2D '+character} sandbox="allow-scripts allow-same-origin"/>:<button onClick={onChat}>此角色尚未配置动态模型</button>}</div></CompanionPet>;
}
