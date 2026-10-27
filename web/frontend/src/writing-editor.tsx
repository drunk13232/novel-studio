import React,{memo,useEffect,useMemo,useRef} from 'react';
import {t,useUiTranslation} from './i18n';
import CodeMirror from '@uiw/react-codemirror';
import {EditorView,keymap,ViewPlugin,type ViewUpdate} from '@codemirror/view';
import {EditorState,Compartment} from '@codemirror/state';
import {openSearchPanel} from '@codemirror/search';
import {indentWithTab,undo,redo,historyField} from '@codemirror/commands';
import {TypingAudio,notifyEditorActivity,type ActivityScope} from './focus-runtime';
// CodeMirror owns Undo/Redo. Keep at most eight small document states in this process.
const editorStates=new Map<string,{json:any;top:number;size:number}>();
function retainEditor(key:string,view:EditorView){if(view.state.doc.length>120000)return;const json=view.state.toJSON({history:historyField}),size=JSON.stringify(json).length;if(size>500000)return;editorStates.delete(key);editorStates.set(key,{json,top:view.scrollDOM.scrollTop,size});while(editorStates.size>8||Array.from(editorStates.values()).reduce((n,v)=>n+v.size,0)>1500000)editorStates.delete(editorStates.keys().next().value!);}
export type EditorPosition={anchor:number;head:number;top:number;revision?:string};
/** A stable compartment changes presentation without replacing the editor/history. */
const typewriterTheme=EditorView.theme({'.cm-content':{paddingTop:'var(--novel-typewriter-pad,4px)',paddingBottom:'var(--novel-typewriter-pad,4px)'}});
const typewriterPadding=ViewPlugin.fromClass(class {
 constructor(readonly view:EditorView){this.measure();}
 measure(){this.view.requestMeasure({read:view=>Math.max(4,view.scrollDOM.clientHeight/2-view.defaultLineHeight/2),write:(height,view)=>{const value=Math.round(height)+'px';if(view.dom.style.getPropertyValue('--novel-typewriter-pad')!==value)view.dom.style.setProperty('--novel-typewriter-pad',value);}});}
 update(update:ViewUpdate){if(update.geometryChanged)this.measure();}
 destroy(){this.view.dom.style.removeProperty('--novel-typewriter-pad');}
});
export function userTyped(update:Pick<ViewUpdate,'docChanged'|'transactions'>){return update.docChanged&&update.transactions.some(transaction=>transaction.isUserEvent('input')||transaction.isUserEvent('delete'));}
function WritingEditor({documentKey='',value,editable,theme,onChange,onSave,onSelection,onComposition,onReady,onLocate,initialPosition,onPosition,onRestore,typewriter=false,typingSound=false,typingVolume=0.25,onActivity,activityScope}:{documentKey?:string;value:string;editable:boolean;theme:'light'|'dark';onChange:(s:string)=>void;onSave:()=>void;onSelection:(s:{text:string;from:number;to:number;userInitiated?:boolean})=>void;onComposition:(v:boolean)=>void;onReady:(search:()=>void)=>void;onLocate?:(locate:(from:number,to:number)=>void)=>void;initialPosition?:EditorPosition;onPosition?:(position:EditorPosition)=>void;onRestore?:(restore:()=>void)=>void;typewriter?:boolean;typingSound?:boolean;typingVolume?:number;onActivity?:(scope?:ActivityScope)=>void;activityScope?:ActivityScope;}){
 const {i18n,ready}=useUiTranslation('editor');
 const editorRef=useRef<EditorView|null>(null);
 const attributes=useMemo(()=>new Compartment(),[]),typewriterCompartment=useMemo(()=>new Compartment(),[]);
 const typingFrame=useRef<number|null>(null),compositionEdited=useRef(false);
 const audio=useRef<TypingAudio|null>(null);
 const restoring=useRef(false);
 const callbacks=useRef({onSave,onSelection,onComposition,onReady,onPosition,onActivity,activityScope,typewriter,typingSound,typingVolume,editable});callbacks.current={onSave,onSelection,onComposition,onReady,onPosition,onActivity,activityScope,typewriter,typingSound,typingVolume,editable};
 useEffect(()=>{editorRef.current?.dispatch({effects:attributes.reconfigure(EditorView.contentAttributes.of({'aria-label':t('editor:manuscript'),spellcheck:'false',dir:'auto'}))});},[i18n.language,ready,attributes]);
 useEffect(()=>{editorRef.current?.dispatch({effects:typewriterCompartment.reconfigure(typewriter?[typewriterTheme,typewriterPadding]:[])});},[typewriter,typewriterCompartment]);
 useEffect(()=>{audio.current?.configure(typingSound,typingVolume);},[typingSound,typingVolume]);
 const cached=useMemo(()=>{const entry=editorStates.get(documentKey);return entry?.json.doc===value?entry:undefined;},[documentKey]);
 useEffect(()=>()=>{if(documentKey&&editorRef.current)retainEditor(documentKey,editorRef.current);if(typingFrame.current!==null)cancelAnimationFrame(typingFrame.current);audio.current?.dispose();audio.current=null;},[documentKey]);
 const presentTyping=(view:EditorView)=>{
  if(typingFrame.current!==null)return;
  typingFrame.current=requestAnimationFrame(()=>{
   typingFrame.current=null;
   if(editorRef.current!==view||!view.dom.isConnected||view.composing||restoring.current)return;
   const options=callbacks.current;
   if(options.typewriter)view.dispatch({effects:EditorView.scrollIntoView(view.state.selection.main.head,{y:'center'})});
   if(options.typingSound){if(!audio.current)audio.current=new TypingAudio(import.meta.env.BASE_URL+'sounds/typewriter-soft.wav');audio.current.configure(options.typingSound,options.typingVolume);audio.current.play();}
  });
 };
 const extensions=useMemo(()=>[EditorView.lineWrapping,EditorState.lineSeparator.of('\n'),keymap.of([
  {key:'Mod-s',run:view=>{if(!view.composing)callbacks.current.onSave();return true;}},{key:'Mod-z',run:undo},{key:'Mod-y',run:redo},{key:'Mod-Shift-z',run:redo},{key:'Mod-f',run:openSearchPanel},{key:'Mod-h',run:openSearchPanel},indentWithTab]),
  attributes.of(EditorView.contentAttributes.of({'aria-label':t('editor:manuscript'),spellcheck:'false',dir:'auto'})),
  typewriterCompartment.of(typewriter?[typewriterTheme,typewriterPadding]:[]),
  EditorView.domEventHandlers({compositionstart:()=>{compositionEdited.current=false;callbacks.current.onComposition(true);},compositionend:(_event,view)=>{callbacks.current.onComposition(false);if(compositionEdited.current){compositionEdited.current=false;presentTyping(view);}},scroll:(_event,view)=>{if(restoring.current)return;const selection=view.state.selection.main;callbacks.current.onPosition?.({anchor:selection.anchor,head:selection.head,top:view.scrollDOM.scrollTop});}}),
  EditorView.updateListener.of(update=>{
   if(update.selectionSet&&!restoring.current){const selection=update.state.selection.main;callbacks.current.onSelection({text:update.state.sliceDoc(selection.from,selection.to),from:selection.from,to:selection.to,userInitiated:update.transactions.some(transaction=>transaction.isUserEvent('select')||transaction.isUserEvent('input'))});callbacks.current.onPosition?.({anchor:selection.anchor,head:selection.head,top:update.view.scrollDOM.scrollTop});}
   if(callbacks.current.editable&&!restoring.current&&userTyped(update)){
    notifyEditorActivity(callbacks.current.activityScope);callbacks.current.onActivity?.(callbacks.current.activityScope);
    if(update.view.composing)compositionEdited.current=true;
    else if(callbacks.current.typewriter||callbacks.current.typingSound)presentTyping(update.view);
   }
  })],[]);
 return <CodeMirror initialState={cached?{json:cached.json,fields:{history:historyField}}:undefined} value={value} height="100%" editable={editable} theme={theme} extensions={extensions} onChange={onChange} onCreateEditor={view=>{editorRef.current=view;callbacks.current.onReady(()=>openSearchPanel(view));const restore=()=>{const position=cached?{anchor:view.state.selection.main.anchor,head:view.state.selection.main.head,top:initialPosition?.top??cached.top}:initialPosition;if(!position)return;restoring.current=true;const clamp=(number:number)=>Math.min(view.state.doc.length,Math.max(0,number));view.dispatch({selection:{anchor:clamp(position.anchor),head:clamp(position.head)}});requestAnimationFrame(()=>{if(editorRef.current===view&&view.dom.isConnected)view.scrollDOM.scrollTop=position.top;restoring.current=false;});};onRestore?.(restore);restore();onLocate?.((from,to)=>{const clamp=(number:number)=>Math.min(view.state.doc.length,Math.max(0,number));view.dispatch({selection:{anchor:clamp(from),head:clamp(to)},effects:EditorView.scrollIntoView(clamp(from),{y:'center'})});view.focus();});}} basicSetup={{lineNumbers:false,foldGutter:false,highlightActiveLine:false,highlightActiveLineGutter:false,autocompletion:false,closeBrackets:false,bracketMatching:false,highlightSelectionMatches:false}}/>;
}
export default memo(WritingEditor);
