import {t as translateUI,useUiTranslation} from './i18n';
import type {ReactNode} from 'react';
import * as Dialog from '@radix-ui/react-dialog';
export function StudioDialog({title,children,onClose,className=''}:{title:string;children:ReactNode;onClose:()=>void;className?:string}){
 useUiTranslation(["common"]);

 return <Dialog.Root open onOpenChange={open=>{if(!open)onClose();}}><Dialog.Portal container={document.querySelector('.studio') as HTMLElement||undefined}><Dialog.Overlay className="studio-overlay"/><Dialog.Content className={'studio-dialog night-dialog '+className} aria-describedby={undefined}><div className="dialog-heading"><Dialog.Title>{title}</Dialog.Title><button aria-label={translateUI("common:closeDialog")} onClick={onClose}>×</button></div>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
