import {Bookmark,Globe,Palette} from 'lucide-react';
import {t,useUiTranslation} from './i18n';
import {getTheme,type ThemeId} from './themes';

export function ProjectAppearance({title,globalTheme,projectTheme,onChange}:{title:string;globalTheme:ThemeId;projectTheme?:ThemeId;onChange:(theme:ThemeId|null)=>void}){
 useUiTranslation('appearance');
 const current=getTheme(projectTheme||globalTheme);
 return <section className="project-appearance" aria-label={t('appearance:projectThemeTitle')}>
  <div className="project-appearance-icon"><Bookmark size={22}/></div><div><h3>{t('appearance:projectThemeTitle')}</h3><p>{t('appearance:projectThemeHelp',{title})}</p></div>
  <div className="project-appearance-options" role="group" aria-label={t('appearance:themeScope')}><button aria-pressed={!projectTheme} onClick={()=>onChange(null)}><Globe size={15}/>{t('appearance:followGlobal')}</button><button aria-pressed={!!projectTheme} onClick={()=>onChange(projectTheme||globalTheme)}><Palette size={15}/>{t('appearance:independentTheme')}</button></div>
  <p className="project-appearance-receipt" role="status">{t(projectTheme?'appearance:projectThemeActive':'appearance:globalThemeActive',{name:t('appearance:theme_'+current.id)})}</p>
 </section>;
}
