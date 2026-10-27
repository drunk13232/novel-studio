import React from 'react';
import CodeMirror from '@uiw/react-codemirror';
import {markdown} from '@codemirror/lang-markdown';
import {yaml} from '@codemirror/lang-yaml';
import {json} from '@codemirror/lang-json';
import {EditorState} from '@codemirror/state';
export default function TextEditor({value,path,editable,onChange}:{value:string;path:string;editable:boolean;onChange:(value:string)=>void}){
 const extensions=[path.endsWith('.json')?json():/\.ya?ml$/.test(path)?yaml():markdown(),EditorState.lineSeparator.of('\n')];
 return <CodeMirror value={value} height="calc(100vh - 225px)" extensions={extensions} editable={editable} onChange={onChange} basicSetup={{lineNumbers:true,foldGutter:true}} theme="light"/>;
}
