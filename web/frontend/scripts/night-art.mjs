// Static editorial compositions of licensed Lucide icons. No runtime drawing engine.
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {BookOpen,Feather,Moon,Flower2,LibraryBig,Users,Sprout,Mountain,Bookmark} from 'lucide-react';
import {mkdirSync,writeFileSync,copyFileSync} from 'node:fs';
const root=new URL('../src/assets/night/',import.meta.url);mkdirSync(root,{recursive:true});
const scenes={welcome:[BookOpen,Feather,Moon],shelf:[LibraryBig,Sprout,Moon],books:[BookOpen,Flower2,Feather],characters:[Users,Flower2,Moon],library:[LibraryBig,Bookmark,Sprout],world:[Mountain,Sprout,Moon],reading:[BookOpen,Feather,Bookmark]};
for(const [name,icons] of Object.entries(scenes)){
 const ink=['#687e77','#ad9568','#91a69f'];
 const drawings=icons.map((Icon,i)=>`<g transform="translate(${[107,40,240][i]} ${[55,110,24][i]})">${renderToStaticMarkup(React.createElement(Icon,{width:[130,62,42][i],height:[130,62,42][i],strokeWidth:1,color:ink[i]}))}</g>`).join('');
 writeFileSync(new URL(name+'.svg',root),`<svg xmlns="http://www.w3.org/2000/svg" width="340" height="220" viewBox="0 0 340 220"><ellipse cx="170" cy="117" rx="105" ry="83" fill="#a8bab4" opacity=".13"/><ellipse cx="179" cy="193" rx="108" ry="4" fill="#91a69f" opacity=".13"/>${drawings}</svg>`);
}
copyFileSync(new URL('../node_modules/lucide-react/LICENSE',import.meta.url),new URL('Lucide-LICENSE.txt',root));
writeFileSync(new URL('ATTRIBUTION.txt',root),'Local editorial compositions use Lucide icons (https://lucide.dev), ISC license. No external image CDN or fonts. Composition: Novel Studio.');
