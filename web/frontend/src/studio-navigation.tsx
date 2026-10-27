import {useEffect,useState} from 'react';
import {BookOpen,Layers,Users,Globe,Library,PanelsTopLeft,Network,Search,Feather,Images,Palette,NotebookPen,Clock,Database,ChartNoAxesCombined,Bookmark,ChevronDown,ArrowUpRight,Command,Settings} from 'lucide-react';
import {t,useUiTranslation} from './i18n';
import {StudioDialog} from './studio-dialog';

type Tool={id:string;label:string;group:string;icon:typeof BookOpen};
const aliases:Record<string,string>={plans:'计划 日历 日期 待办 进度 安排 planning calendar schedule todo',clues:'伏笔 线索 回收 逾期 clues foreshadow payoff',focusTools:'专注 番茄钟 打字机 音效 久坐 护眼 focus pomodoro typewriter sound wellbeing',plugins:'插件 扩展 接入 plugin extension integration',python:'Python 脚本 自动化 操作 API SDK control automation',literary:'评分 总编辑 校对 文风 思想 伏笔 质量 score review editor critique',worldlogic:'实验 推演 反事实 约束 simulation experiment',world:'百科 设定 规则 世界观 bible rules',characters:'角色 档案 character profile',data:'备份 恢复 backup restore',references:'文献 阅读 reference reading',styles:'文风 档案 style',images:'图片 生成 ComfyUI',graph:'人物关系 graph',board:'剧情矩阵 matrix',book:'出版 导出 export',revision:'修改 历史 diff revision',todos:'待办 todo',inspiration:'灵感 note',snapshots:'快照 snapshot',import:'旧稿 导入 txt markdown docx import'};
const definitions:[string,string,string,typeof BookOpen][]=[
 ['plans','planningCenter','writing',Clock],['write','manuscript','writing',BookOpen],['concept','concept','writing',Feather],['outline','outline','writing',Layers],['board','plotBoard','writing',PanelsTopLeft],['collection','collection','writing',Layers],['mode','writingMode','writing',BookOpen],
 ['characters','characters','world',Users],['world','worldSettings','world',Globe],['knowledge','knowledgeLinks','world',Network],['graph','relationships','world',Network],['timeline','timeline','world',Clock],['worldlogic','worldLogicLab','world',Globe],
 ['emotionCurve','emotionCurve','analysis',ChartNoAxesCombined],['readerPersonas','readerPersonas','analysis',Users],
 ['chapterVersions','chapterVersions','writing',BookOpen],
 ['worldmap','worldMap','world',Globe],['annual','annualReport','analysis',ChartNoAxesCombined],['ritual','writingRitual','writing',Clock],['finishWriting','finishWriting','writing',BookOpen],['audioExport','audioExport','manage',BookOpen],
 ['clues','clueBoard','analysis',Bookmark],['focusTools','focusTools','writing',Clock],['literary','literaryReview','analysis',Feather],['roleplay','roleplay','analysis',Users],['statistics','statistics','analysis',ChartNoAxesCombined],
 ['references','referenceLibrary','reference',Library],['styles','styleLibrary','reference',Feather],['research','research','reference',NotebookPen],['gallery','gallery','reference',Images],['images','aiImages','reference',Palette],
 ['plugins','pluginHub','manage',Command],['python','pythonControl','manage',Command],['search','fullTextSearch','manage',Search],['recent','recentReading','manage',Clock],['notes','bookmarksNotes','manage',Bookmark],['book','publication','manage',BookOpen],['data','dataBackup','manage',Database],
 ['overview','commandOverview','writing',PanelsTopLeft],['todos','commandTodos','writing',Bookmark],['inspiration','commandInspiration','writing',NotebookPen],['revision','commandRevision','analysis',Feather],['replace','commandReplace','manage',Search],['snapshots','commandSnapshots','manage',Database],['import','commandImport','manage',BookOpen],
];
export function studioToolsFor(form:string):Tool[]{
 return definitions.filter(([id])=>id!=='collection'||form==='anthology').filter(([id])=>id!=='concept'||['short','undecided','novella'].includes(form)).map(([id,key,group,icon])=>({id,group,icon,label:t((id==='literary'||id==='roleplay'?'creative:':'navigation:')+key)}));
}

/** Application navigation only. Every destination uses Studio's existing guarded router. */
export function StudioNavigation({page,form,simple,onSimple,onNavigate,onSettings}:{page:string;form:string;simple:boolean;onSimple:(value:boolean)=>void;onNavigate:(page:string)=>void;onSettings:()=>void}){
 useUiTranslation(['navigation','creative','common']);
 const [drawer,setDrawer]=useState(false),[query,setQuery]=useState(''),[expanded,setExpanded]=useState<string|null>(null);
 const tools=studioToolsFor(form),active=tools.find(tool=>tool.id===page);
 useEffect(()=>{setExpanded(active?.group||null);},[page]);
 const primaryIds=['write',['short','undecided'].includes(form)?'concept':form==='anthology'?'collection':'outline','characters','world','references'];
 const primary=primaryIds.map(id=>tools.find(tool=>tool.id===id)).filter((tool):tool is Tool=>!!tool);
 const groups=['writing','world','analysis','reference','manage'];
 const matches=tools.filter(tool=>(tool.label+' '+tool.id+' '+(aliases[tool.id]||'')+' '+t('navigation:toolGroup_'+tool.group)).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
 const renderTool=(tool:Tool,close=false)=><button key={tool.id} data-studio-page={tool.id} className={page===tool.id?'selected':''} aria-current={page===tool.id?'page':undefined} onClick={()=>{if(close)setDrawer(false);onNavigate(tool.id);}}><tool.icon size={17}/><span>{!close&&tool.id==='references'?t('navigation:referenceShort'):tool.label}</span>{close&&<ArrowUpRight size={13}/>}</button>;
 return <>
  <div className="navigation-mode" role="group" aria-label={t('navigation:navigationDensity')}><button aria-pressed={simple} onClick={()=>onSimple(true)}>{t('navigation:writingNavigation')}</button><button aria-pressed={!simple} onClick={()=>onSimple(false)}>{t('navigation:fullNavigation')}</button></div>
  <nav className="project-navigation" aria-label={t('navigation:projectTools')}>
   <div className="navigation-primary">{primary.map(tool=>renderTool(tool))}</div>
   {simple&&active&&!primaryIds.includes(active.id)&&<div className="navigation-current"><small>{t('navigation:currentTool')}</small>{renderTool(active)}</div>}
   {!simple&&<div className="navigation-groups">{groups.map(group=>{const items=tools.filter(tool=>tool.group===group&&!primaryIds.includes(tool.id));return items.length?<div key={group} className="navigation-group"><button className="navigation-group-title" aria-expanded={expanded===group} onClick={()=>setExpanded(value=>value===group?null:group)}><span>{t('navigation:toolGroup_'+group)}</span><small>{items.length}</small><ChevronDown size={12}/></button>{expanded===group&&<div>{items.map(tool=>renderTool(tool))}</div>}</div>:null;})}</div>}
   <button className="navigation-index" aria-haspopup="dialog" onClick={()=>{setQuery('');setDrawer(true);}}><Command size={16}/><span>{t('navigation:allTools')}</span><small>{tools.length}</small></button>
  </nav>
  {drawer&&<StudioDialog title={t('navigation:allTools')} className="tool-index-dialog" onClose={()=>setDrawer(false)}><p className="muted">{t('navigation:toolIndexHelp')}</p><label className="tool-index-search"><Search size={17}/><input autoFocus aria-label={t('navigation:searchTools')} placeholder={t('navigation:searchTools')} value={query} onChange={event=>setQuery(event.target.value)}/></label><div className="tool-index-grid">{groups.map(group=>{const rows=matches.filter(tool=>tool.group===group);return rows.length?<section key={group}><h3>{t('navigation:toolGroup_'+group)}<small>{rows.length}</small></h3>{rows.map(tool=>renderTool(tool,true))}</section>:null;})}</div>{!matches.length&&<p className="tool-index-empty" role="status">{t('navigation:noMatchingTools')}</p>}<div className="tool-index-footnote"><kbd>Ctrl K</kbd><span>{t('navigation:commandShortcutHelp')}</span><button onClick={()=>{setDrawer(false);onSettings();}}><Settings size={14}/>{t('navigation:settings')}</button></div></StudioDialog>}
 </>;
}
