// Lifecycle and behavior decisions only. Cubism/l2d owns deformation, interpolation, blending and rendering.
const label=document.getElementById('receipt');let runtime=null,token='',spec=null,ready=false,epoch=0;
let extrema={},samples=0,petPointer=null,hitPending='',hoverArea='',hoverSince=0,lastHover=0;
let mode='idle',quiet=false,autonomous=true,busyUntil=0,nextIdle=0,lastIntent='',lastInteraction=0,lastClick=0,clicks=0,expressionUntil=0;
const history=[];
const emit=(type,data={})=>parent.postMessage({channel:'novel-live2d',token,type,...data},location.origin);
function status(text){label.textContent=text;emit('status',{text});}
function record(event,detail=''){history.push({event,detail,at:Math.round(performance.now())});if(history.length>80)history.shift();emit('behavior',{state:quiet?'quiet':mode,event,detail});}
function fittedScale(){const c=document.getElementById('model'),r=Number(spec?.canvas_aspect);return (Number(spec?.scale)||1)*(Number.isFinite(r)&&r>=.1&&r<=10&&c.clientWidth?Math.min(1,c.clientHeight/c.clientWidth*r)*.94:1);}
const resize=new ResizeObserver(()=>{if(ready&&runtime)runtime.setScale(fittedScale());});resize.observe(document.getElementById('model'));
function later(){nextIdle=performance.now()+(spec?.character==='yoshino'?18000:24000)+Math.random()*16000;}
function expression(id,seconds=7){if(!ready||!runtime.getExpressions().includes(id))return false;runtime.setExpression(id);expressionUntil=performance.now()+seconds*1000;return true;}
function emotion(id,seconds){return expression(spec?.expressions?.[id],seconds);}
function motion(intent,priority=2){
 const m=spec?.behaviors?.[intent];if(!m||!ready)return false;
 const groups=runtime.getMotions();if(!groups[m.group]?.[m.index])return false;
 if(priority<3&&(busyUntil>performance.now()||['thinking','speaking','listening'].includes(mode)))return false;
 busyUntil=performance.now()+8000;lastIntent=intent;runtime.playMotion(m.group,m.index,priority);record('requested',intent);return true;
}
function setMode(value){
 const mapping={idle:['neutral',''],observing:['neutral','look'],listening:['neutral',''],thinking:['thinking','think'],searching:['thinking','search'],reading:['thinking','read'],analyzing:['thinking','read'],executing:['neutral','execute'],confirm:['confused','confirm'],result:['neutral','present'],success:['happy','nod'],error:['confused','error'],risk:['displeased',''],cancelled:['neutral','rest'],rejected:['neutral',''],speaking:['neutral',''],waiting:['neutral',''],resting:['neutral','rest']};
 if(!mapping[value]||mode===value)return;mode=value;record('state');later();
 if(!quiet){const [face,intent]=mapping[value];emotion(face,120);if(intent)motion(intent,3);else if(spec?.assistant&&runtime?.getMotions()?.Neutral?.[0])runtime.playMotion('Neutral',0,3);}
}
function interaction(kind,area=''){
 if(!ready)return;const now=performance.now();record(kind,area);if(spec?.assistant)return;
 if(['thinking','speaking'].includes(mode)||quiet||now-lastInteraction<1500)return;
 lastInteraction=now;later();
 if(kind==='tap'){
  clicks=now-lastClick<4500?clicks+1:1;lastClick=now;
  if(clicks>=3){emotion(spec.character==='yoshino'?'displeased':'confused');motion('shake',3);record('cooldown','repeated-touch');lastInteraction=now+3500;clicks=0;}
  else {emotion(area==='Head'?'shy':'happy');motion(area==='Head'?'nod':'tap',3);}
 }else if(kind==='hold'){emotion('confused');motion('think',3);}
 else if(kind==='hover-dwell'){setMode('observing');emotion('neutral');}
 else if(kind==='drag-end'){emotion('surprised',3);motion('agree',3);}
}
async function load(value){
 const mine=++epoch;spec=value;quiet=!!value.quiet;autonomous=value.autonomous!==false;ready=false;extrema={};samples=0;
 if(runtime){runtime.destroy();runtime=null;}busyUntil=0;mode='idle';
 const aspect=Number(value.display_aspect)||1;if(aspect<.5||aspect>2.2)throw new Error('模型显示比例无效');
 const canvas=document.getElementById('model');canvas.style.transformOrigin='center';canvas.style.transform=aspect===1?'':'scaleY('+aspect+')';
 if(!window.AMotion)await new Promise((resolve,reject)=>{const core=document.createElement('script');core.src='/api/studio/live2d/runtime/cubism2.js';core.onload=resolve;core.onerror=()=>reject(new Error('官方兼容 Core 加载失败'));document.head.append(core);});
 if(mine!==epoch||document.hidden)return;
 const api=await import('/api/studio/live2d/runtime/l2d.js');if(mine!==epoch)return;
 const instance=api.init(canvas);runtime=instance;
 instance.on('motionstart',(group,index,duration)=>{if(instance!==runtime)return;busyUntil=group==='Idle'?0:performance.now()+Math.min(15000,Math.max(500,(Number(duration)||4)*1000));emit('motion',{group,index,duration});record('motion-start',group);});
 instance.on('motionend',(group,index)=>{if(instance!==runtime)return;busyUntil=0;emit('motion-end',{group,index});record('motion-end',group);});
 instance.on('expressionchange',id=>{if(instance===runtime)emit('expression',{id});});
 // SDK tap arrives at pointerdown. Commit only at pointerup; dragging never taps.
 instance.on('tap',area=>{if(petPointer)hitPending=area;});
 status('加载真实模型数据…');await instance.load({path:value.url,scale:fittedScale(),position:value.position||[0,0],volume:0,logLevel:'error'});
 if(mine!==epoch){instance.destroy();return;}ready=true;later();
 emit('ready',{motions:runtime.getMotions(),expressions:runtime.getExpressions(),parameters:runtime.getParams().map(x=>({id:x.id,min:x.min,max:x.max})),hit_areas:runtime.getHitAreaBounds().map(x=>x.name),core_version:window.Live2DCubismCore?.Version?.csmGetVersion?.()||null});status('真实模型已加载');record('loaded');
}
window.addEventListener('message',async event=>{
 if(event.origin!==location.origin||event.source!==parent||event.data?.channel!=='novel-live2d')return;
 const m=event.data;if(!token&&m.type==='load')token=m.token;if(m.token!==token)return;
 try{
 if(m.type==='load'){await load(m.spec);return;}
 if(m.type==='policy'){quiet=!!m.quiet;autonomous=m.autonomous!==false;if(spec){spec.quiet=quiet;spec.autonomous=autonomous;}later();record('policy');return;}
 if(!runtime||!ready)return;
 if(m.type==='state')setMode(m.state);
 else if(m.type==='cue'){if(m.emotion)emotion(m.emotion);if(m.intent&&m.intent!=='none'&&!motion(m.intent,3))emit('unsupported',{intent:m.intent});}
 else if(m.type==='interaction')interaction(m.kind,m.area);
 else if(m.type==='motion'){
  if(!runtime.getMotions()[m.group]?.[m.index]||!Number.isInteger(m.index))throw new Error('模型没有该动作');
  if(mode==='speaking')throw new Error('请先停止朗读再手动切换动作');runtime.playMotion(m.group,m.index,3);later();
 }else if(m.type==='expression'){if(!expression(m.id,10))throw new Error('模型没有该表情');}
 else if(m.type==='mouth'){const known=new Set(runtime.getParams().map(x=>x.id));runtime.setParams(Object.fromEntries((spec.mouth_ids||[]).filter(x=>known.has(x)).map(id=>[id,Math.max(0,Math.min(1,Number(m.value)||0))])));}
 else if(m.type==='transform'){spec.scale=Math.max(.5,Math.min(1.5,Number(m.scale)||1));spec.position=[Math.max(-.8,Math.min(.8,Number(m.x)||0)),Math.max(-.8,Math.min(.8,Number(m.y)||0))];runtime.setScale(fittedScale());runtime.setPosition(...spec.position);}
 else if(m.type==='reset')await load(spec);
 }catch(e){status(String(e));emit('error',{text:String(e)});}
});
const timer=setInterval(()=>{
 if(!ready||!runtime||document.hidden)return;samples++;const now=performance.now();
 for(const p of runtime.getParams()){const v=extrema[p.id]||(extrema[p.id]={min:p.value,max:p.value});v.min=Math.min(v.min,p.value);v.max=Math.max(v.max,p.value);}
 if(expressionUntil&&now>=expressionUntil&&!['speaking','thinking','listening'].includes(mode)){emotion('neutral',0);expressionUntil=0;}
 if(hoverArea&&now-hoverSince>1800&&now-lastHover>12000){lastHover=now;interaction('hover-dwell',hoverArea);}
 if(autonomous&&!quiet&&now>=nextIdle&&!['thinking','speaking','listening'].includes(mode)){
  const choices=(spec.character==='yoshino'?['look','think','rest']:['look','rest','nod']).filter(x=>spec.behaviors?.[x]&&x!==lastIntent);
  const choice=choices[Math.floor(Math.random()*choices.length)];
  if(choice&&motion(choice)){setMode(choice==='rest'?'resting':'idle');}later();
 }
 const keys=['ParamEyeLOpen','ParamEyeROpen','ParamBreath','ParamAngleX','ParamAngleY','ParamMouthOpenY'];
 emit('measure',{samples,measured:Object.fromEntries(keys.filter(k=>extrema[k]).map(k=>[k,extrema[k]])),state:quiet?'quiet':mode,history});
},1000);
const petCanvas=document.getElementById('model');petCanvas.addEventListener('contextmenu',event=>{event.preventDefault();emit('pet-activate');});petCanvas.style.touchAction='none';
function actualArea(event){
 if(!ready)return '';const r=petCanvas.getBoundingClientRect(),x=(event.clientX-r.left)/r.width,y=(event.clientY-r.top)/r.height;
 return runtime.getHitAreaBounds().find(h=>x>=h.x&&x<=h.x+h.w&&y>=h.y&&y<=h.y+h.h)?.name||'';
}
petCanvas.addEventListener('pointerdown',event=>{
 if(event.button!==0||petPointer)return;
 hitPending=actualArea(event);petPointer={id:event.pointerId,x:event.screenX,y:event.screenY,moved:false,at:performance.now()};petCanvas.setPointerCapture(event.pointerId);
 emit('pet-pointer',{phase:'start',x:event.screenX,y:event.screenY,pointer_id:event.pointerId});
});
petCanvas.addEventListener('pointermove',event=>{
 if(!petPointer){const area=actualArea(event);if(area!==hoverArea){hoverArea=area;hoverSince=performance.now();}return;}
 if(petPointer.id!==event.pointerId)return;
 if(Math.hypot(event.screenX-petPointer.x,event.screenY-petPointer.y)>5)petPointer.moved=true;
 emit('pet-pointer',{phase:'move',x:event.screenX,y:event.screenY,pointer_id:event.pointerId});
});
petCanvas.addEventListener('pointerleave',()=>{hoverArea='';});
function finishPetPointer(event){
 if(petPointer?.id!==event.pointerId)return;
 const {moved,at}=petPointer,clicked=!moved&&event.type==='pointerup',area=hitPending;
 emit('pet-pointer',{phase:event.type==='pointerup'?'end':'cancel',x:event.screenX,y:event.screenY,pointer_id:event.pointerId});
 petPointer=null;hitPending='';if(petCanvas.hasPointerCapture(event.pointerId))petCanvas.releasePointerCapture(event.pointerId);
 if(clicked){if(area){interaction(performance.now()-at>700?'hold':'tap',area);emit('tap',{area});}emit('pet-activate');}
 else if(moved&&event.type==='pointerup')interaction('drag-end');
}
for(const name of ['pointerup','pointercancel','lostpointercapture'])petCanvas.addEventListener(name,finishPetPointer);
document.addEventListener('visibilitychange',()=>{
 if(document.hidden){epoch++;ready=false;runtime?.destroy();runtime=null;emit('suspended');}
 else if(spec)void load(spec).catch(e=>emit('error',{text:String(e)}));
});
window.addEventListener('pagehide',()=>{epoch++;clearInterval(timer);resize.disconnect();runtime?.destroy();});
parent.postMessage({channel:'novel-live2d',type:'frame-ready'},location.origin);
