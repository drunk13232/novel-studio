import {t as translateUI,useUiTranslation} from './i18n';
import {Document,Page,pdfjs} from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc=new URL('pdfjs-dist/build/pdf.worker.min.mjs',import.meta.url).toString();
const options={cMapUrl:'/pdf/cmaps/',cMapPacked:true,standardFontDataUrl:'/pdf/standard_fonts/',wasmUrl:'/pdf/wasm/'};

export default function ReferencePDF({url,page,count,width,onLoad,onError,onRender}:{url:string;page:number;count:number;width:number;onLoad:(count:number)=>void;onError:(error:Error)=>void;onRender:()=>void}){
 useUiTranslation(["references"]);

 return <Document file={url} options={options} onLoadSuccess={({numPages})=>onLoad(numPages)} onLoadError={onError} loading={<p role="status">{translateUI("references:readingPdfPages")}</p>}><Page pageNumber={Math.max(1,Math.min(page,count||1))} width={width} renderTextLayer renderAnnotationLayer={false} onRenderSuccess={onRender} onRenderError={onError}/></Document>;
}
