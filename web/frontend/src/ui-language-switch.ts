import type {i18n} from 'i18next';
import type {UiLocale} from './i18n-locales';

const pending=new WeakMap<i18n,number>();
/** Optional feature namespaces may be untranslated; use i18next's real fallback. */
export async function activateUiLanguage(engine:i18n,code:UiLocale){
 const version=(pending.get(engine)||0)+1;pending.set(engine,version);
 await new Promise<void>(resolve=>{void engine.loadLanguages(code,()=>resolve());});
 if(pending.get(engine)!==version)return false;
 // A network failure of the core UI must retain the current usable language.
 if(!engine.hasResourceBundle(code,'common')||!engine.hasResourceBundle(code,'navigation'))throw new Error('UI_LANGUAGE_RESOURCES_UNAVAILABLE');
 await engine.changeLanguage(code);
 return pending.get(engine)===version;
}
