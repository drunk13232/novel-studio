import {t as translateUI,useUiTranslation} from './i18n';
import {useState} from 'react';
import {StudioDialog} from './studio-dialog';
import {imageUrl,Data} from './library-shared';
export function ImagePreview({project,items,initialId,onClose}:{project:string;items:Data[];initialId:string;onClose:()=>void}){
 useUiTranslation(["images"]);

 const [id,setId]=useState(initialId),index=items.findIndex(x=>x.id===id),asset=items[index];
 if(!asset)return null;
 return <StudioDialog title={asset.name||'图片预览'} className="image-preview-dialog" onClose={onClose}><figure><img src={imageUrl(project,asset.id)} alt={asset.name}/><figcaption>{asset.width} × {asset.height} · {index+1} / {items.length}</figcaption></figure><div className="dialog-actions"><button disabled={index<=0} onClick={()=>setId(items[index-1].id)}>{translateUI("images:previousImage")}</button><a className="v12-link-button" href={imageUrl(project,asset.id)+'?download=true'} download>导出原图</a><button disabled={index>=items.length-1} onClick={()=>setId(items[index+1].id)}>{translateUI("images:nextImage")}</button></div></StudioDialog>;
}
