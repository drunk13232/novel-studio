/** Headless checks read the complete CodeMirror document, never its virtualized viewport.
 * A test-only same-origin module uses EditorView.findFromDOM. No production bridge,
 * editor mutation, new dependency or runtime-network download is introduced.
 */
import path from 'node:path';
import {pathToFileURL} from 'node:url';

export async function editorStateReader(page, root) {
 const {default: esbuild}=await import(pathToFileURL(path.join(root,'web/frontend/node_modules/esbuild/lib/main.js')).href);
 const result=await esbuild.build({stdin:{contents:"export {EditorView} from '@codemirror/view';",resolveDir:path.join(root,'web/frontend')},bundle:true,format:'esm',platform:'browser',target:'es2022',write:false,logLevel:'silent'});
 const script=result.outputFiles[0].text;
 await page.route('**/__novel-test__/editor-view.mjs',route=>route.fulfill({status:200,contentType:'text/javascript',body:script}));
 return ()=>page.evaluate(async()=>{
  const {EditorView}=await import('/__novel-test__/editor-view.mjs');
  const dom=document.querySelector('.manuscript-editor .cm-editor');
  if(!dom)throw new Error('Manuscript editor is not mounted');
  const view=EditorView.findFromDOM(dom);
  if(!view)throw new Error('CodeMirror view is unavailable; never fall back to visible text');
  return view.state.doc.toString();
 });
}
