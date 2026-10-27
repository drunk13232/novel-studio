import {useEffect,useImperativeHandle,useRef,useState} from 'react';
import type {ReactNode,RefObject} from 'react';
import {GripVertical,MessageCircle,Minus,MousePointer2,X} from 'lucide-react';
import {t} from './i18n';
const tr=(key:string)=>t('settings:l2d_'+key);
const clamp=(n:number,min:number,max:number)=>Math.max(min,Math.min(max,n));
type Point={x:number;y:number};
type PointerMessage={phase:'start'|'move'|'end'|'cancel';x:number;y:number;pointer_id:number};
export type PetController={pointer:(message:PointerMessage)=>void;activate:()=>void};
type Props={dock?:{left:number;top:number;width:number;height:number}|null;name:string;size:number;x:number;y:number;passthrough:boolean;panelOpen:boolean;
 controller:RefObject<PetController|null>;onMove:(x:number,y:number)=>void;
 onPanel:(open:boolean)=>void;onPassthrough:()=>void;onClose:()=>void;
 children:ReactNode;panel:ReactNode;status:string};
/** Presentation only: existing Live2D/AI ownership stays in LiveCompanion. */
export function CompanionPet(p:Props){
 const host=useRef<HTMLDivElement>(null),panel=useRef<HTMLDivElement>(null);
 const [bounds,setBounds]=useState({width:0,height:0}),[panelHeight,setPanelHeight]=useState(420);
 const [preview,setPreview]=useState<Point|null>(null);
 const dragging=useRef<{id:number;start:Point;origin:Point;last:Point;scale:number;moved:boolean}|null>(null);
 const hostRect=host.current?.getBoundingClientRect();const unit=hostRect&&bounds.width?hostRect.width/bounds.width:1;
 const stageHeight=p.dock?Math.min(176,p.dock.height/unit-8):Math.min(p.size,Math.max(120,bounds.height-64));
 const width=p.dock?Math.max(200,p.dock.width/unit-24):Math.min(stageHeight*.66,Math.max(100,bounds.width-24));
 const maxX=Math.max(0,bounds.width-width-24),maxY=Math.max(0,bounds.height-stageHeight-56);
 const position=p.dock?{x:(p.dock.left-(hostRect?.left||0))/unit+12,y:(p.dock.top-(hostRect?.top||0))/unit+4}:preview||{x:12+clamp(p.x,0,1)*maxX,y:12+clamp(p.y,0,1)*maxY};
 useEffect(()=>{const node=host.current;if(!node)return;const ro=new ResizeObserver(()=>setBounds({width:node.clientWidth,height:node.clientHeight}));ro.observe(node);return()=>ro.disconnect();},[]);
 useEffect(()=>{const node=panel.current;if(!node||!p.panelOpen)return;const ro=new ResizeObserver(()=>setPanelHeight(node.offsetHeight));ro.observe(node);return()=>ro.disconnect();},[p.panelOpen]);
 function pointer(m:PointerMessage){
  if(p.dock)return;
  if(!Number.isFinite(m.x)||!Number.isFinite(m.y)||!Number.isInteger(m.pointer_id))return;
  if(m.phase==='start'){
   const node=host.current;if(!node||dragging.current)return;
   dragging.current={id:m.pointer_id,start:{x:m.x,y:m.y},origin:position,last:position,scale:node.getBoundingClientRect().width/node.clientWidth||1,moved:false};return;
  }
  const drag=dragging.current;if(!drag||drag.id!==m.pointer_id)return;
  if(m.phase==='move'){
   const dx=(m.x-drag.start.x)/drag.scale,dy=(m.y-drag.start.y)/drag.scale;
   if(!drag.moved&&Math.hypot(dx,dy)<5)return;
   drag.moved=true;drag.last={x:clamp(drag.origin.x+dx,12,12+maxX),y:clamp(drag.origin.y+dy,12,12+maxY)};setPreview(drag.last);return;
  }
  if(m.phase==='end'&&drag.moved)p.onMove(maxX?(drag.last.x-12)/maxX:1,maxY?(drag.last.y-12)/maxY:1);
  dragging.current=null;setPreview(null);
 }
 useImperativeHandle(p.controller,()=>({pointer,activate:()=>p.onPanel(true)}));
 useEffect(()=>{if(!p.panelOpen)return;
  const outside=(e:PointerEvent)=>{if(!host.current?.contains(e.target as Node))p.onPanel(false);};
  const escape=(e:KeyboardEvent)=>{if(e.key==='Escape'){p.onPanel(false);}};
  document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape);
  return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape);};
 },[p.panelOpen,p.onPanel]);
 const panelWidth=Math.min(350,Math.max(180,bounds.width-24));
 const preferLeft=position.x>=panelWidth+20;
 const panelX=clamp(preferLeft?position.x-panelWidth-10:position.x+width+10,12,Math.max(12,bounds.width-panelWidth-12));
 const panelY=clamp(position.y+stageHeight+32-panelHeight,12,Math.max(12,bounds.height-panelHeight-12));
 return <div ref={host} className="lc-pet-host">
  <div className={'lc-pet '+(p.dock?'is-docked ':'')+(preview?'is-dragging ':'')+(p.passthrough?'is-passthrough':'')} style={{left:position.x,top:position.y,width,visibility:bounds.width?'visible':'hidden'}}>
   <div onContextMenu={e=>{e.preventDefault();p.onPanel(true);}} className="lc-pet-body" style={{height:stageHeight}}>{p.children}</div>
   <div className="lc-pet-toolbar">
    <button className="lc-pet-grip" aria-label={tr('petDrag')} title={tr('petDragHint')}
     onPointerDown={e=>{if(e.button!==0)return;e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);pointer({phase:'start',x:e.screenX,y:e.screenY,pointer_id:e.pointerId});}}
     onPointerMove={e=>pointer({phase:'move',x:e.screenX,y:e.screenY,pointer_id:e.pointerId})}
     onPointerUp={e=>{pointer({phase:'end',x:e.screenX,y:e.screenY,pointer_id:e.pointerId});if(e.currentTarget.hasPointerCapture(e.pointerId))e.currentTarget.releasePointerCapture(e.pointerId);}}
     onPointerCancel={e=>pointer({phase:'cancel',x:e.screenX,y:e.screenY,pointer_id:e.pointerId})}
     onLostPointerCapture={e=>pointer({phase:'cancel',x:e.screenX,y:e.screenY,pointer_id:e.pointerId})}
     onKeyDown={e=>{const moves:Record<string,Point>={ArrowLeft:{x:-.05,y:0},ArrowRight:{x:.05,y:0},ArrowUp:{x:0,y:-.05},ArrowDown:{x:0,y:.05}};const delta=moves[e.key];if(delta){e.preventDefault();p.onMove(clamp(p.x+delta.x,0,1),clamp(p.y+delta.y,0,1));}}}>
     <GripVertical size={13}/><span>{p.name}</span>
    </button>
    <button className="lc-pet-tool" aria-label={tr('petChat')} aria-expanded={p.panelOpen} title={tr('petChat')} onClick={()=>p.onPanel(!p.panelOpen)}><MessageCircle size={15}/></button>
    <button className="lc-pet-tool" aria-label={tr('petPassthrough')} aria-pressed={p.passthrough} title={tr('petPassthroughHint')} onClick={p.onPassthrough}><MousePointer2 size={14}/></button>
    <button className="lc-pet-tool" aria-label={tr('hide')} title={tr('hide')} onClick={p.onClose}><Minus size={15}/></button>
   </div>
   <span className="lc-pet-status" role="status">{p.status}</span>
  </div>
  {p.panelOpen&&<div ref={panel} className="lc-pet-popover" role="region" aria-label={tr('petChat')} style={{left:panelX,top:panelY,width:panelWidth,maxHeight:Math.max(120,bounds.height-24)}}>
   <button className="lc-pet-close" aria-label={tr('petClosePanel')} onClick={()=>p.onPanel(false)}><X size={17}/></button>
   {p.panel}
  </div>}
 </div>;
}
