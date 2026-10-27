import type {ReactElement} from 'react';
import * as Menu from '@radix-ui/react-context-menu';
import i18n from './i18n';

export type ObjectAction={id:string;label:string;run:()=>void;disabled?:boolean};
/** Object actions reuse the same callbacks as visible buttons; no new authority. */
export function ObjectActions({label,actions,children}:{label:string;actions:ObjectAction[];children:ReactElement}){
 return <Menu.Root dir={i18n.dir()}><Menu.Trigger asChild>{children}</Menu.Trigger><Menu.Portal container={document.querySelector('.studio') as HTMLElement||undefined}><Menu.Content className="object-actions" aria-label={label} collisionPadding={10}><Menu.Label className="object-actions-label">{label}</Menu.Label>{actions.map(action=><Menu.Item key={action.id} disabled={action.disabled} onSelect={action.run}>{action.label}</Menu.Item>)}</Menu.Content></Menu.Portal></Menu.Root>;
}
