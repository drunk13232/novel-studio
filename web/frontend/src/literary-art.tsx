import welcome from './assets/study/study-banner.webp';
import empty from './assets/study/empty-library.webp';
import shelf from './assets/night/shelf.svg';
import books from './assets/night/books.svg';
import characters from './assets/night/characters.svg';
import library from './assets/night/library.svg';
import world from './assets/night/world.svg';
import reading from './assets/night/reading.svg';
import {useAppearance} from './companion-theme';
import {getTheme} from './themes';
const images={welcome,shelf,books:empty,characters,library:empty,world:empty,reading,empty};
export function LiteraryArt({kind,className=''}:{kind:keyof typeof images;className?:string}){const theme=getTheme(useAppearance());const themed=!!theme.art;const source=themed?(kind==='welcome'?theme.art!:theme.ornament):theme.family==='minimal'?theme.ornament:images[kind];return <img className={'literary-art '+(themed?'theme-'+(kind==='welcome'?'welcome':'empty')+'-art ':'')+className} src={source} alt="" aria-hidden="true" loading="lazy" decoding="async"/>;}
