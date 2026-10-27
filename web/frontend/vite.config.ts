import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { output: { manualChunks(id) {
    if(!id.includes('node_modules'))return;
    if(/@codemirror\/lang-|@lezer\/(markdown|yaml|json|html|javascript|css)|@codemirror\/language-data/.test(id))return 'editor-languages';
    if(/@codemirror|@uiw|@lezer|\/codemirror\/|style-mod|w3c-keyname|crelt/.test(id))return 'editor-core';
    if(/\/node_modules\/(?:react|react-dom|scheduler)\//.test(id))return 'react';
  } } } },
  server: { proxy: { '/api': { target: 'http://127.0.0.1:8765', changeOrigin: false } } },
});
