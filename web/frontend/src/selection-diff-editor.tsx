import {DiffEditor,loader,type DiffEditorProps} from '@monaco-editor/react';
import * as monaco from 'monaco-editor/editor/editor.api.js';
import EditorWorker from 'monaco-editor/editor/editor.worker.js?worker';

(self as any).MonacoEnvironment={getWorker:()=>new EditorWorker()};
loader.config({monaco});

export default function SelectionDiffEditor(props:DiffEditorProps){return <DiffEditor {...props} keepCurrentOriginalModel keepCurrentModifiedModel onMount={(editor,instance)=>{
  const models=editor.getModel();
  editor.onDidDispose(()=>queueMicrotask(()=>{
    // Release our ephemeral models only after the widget detaches them.
    if(!props.keepCurrentOriginalModel&&!props.originalModelPath&&!models?.original.isDisposed())models?.original.dispose();
    if(!props.keepCurrentModifiedModel&&!props.modifiedModelPath&&!models?.modified.isDisposed())models?.modified.dispose();
  }));
  props.onMount?.(editor,instance);
}}/>;}
