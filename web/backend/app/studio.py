"""Thin desktop/manual-writing endpoints over the existing project registry.

No story generation or state commit lives here. Manuscripts stay in the real
workspace; preferences and crash recovery are independent application data.
"""
import hashlib
from functools import lru_cache
import json
import os
import re
import threading
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from app.version import release_info
from app.errors import ConsoleError
from app.tasks.storage import atomic_json
from app.workspace.service import sha, modified
from app.appearance import ThemeId,ThemeCustomization,THEME_IDS,DARK_THEMES


def body_counts(text,strip_header=True):
    if strip_header:text=re.sub(r'^\ufeff?\s*(?:#{1,6}\s+|第[一二三四五六七八九十百千零〇\d]+章[^\r\n]*)(?:[^\r\n]*)(?:\r?\n|$)', '', text, count=1)
    return {'han':len(re.findall(r'[\u3400-\u9fff]', text)),
            'characters':len(re.sub(r'\s', '', text))}


@lru_cache(maxsize=1024)
def manuscript_summary(root,relative,mtime,ctime,size):
    from app.projects.service import NovelWorkspace
    content=NovelWorkspace(Path(root)).content(relative)
    lines=content['content'].splitlines();heading=lines[0] if lines else ''
    title=re.sub(r'^(?:#+\s*)?第[一二三四五六七八九十百千零〇\d]+章\s*','',heading).strip()
    return {**body_counts(content['content']),'modified_at':content['modified_at'],
            'heading_title':title if title and title!=heading else None}

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class DraftRequest(Strict):
    number:int=Field(ge=0,le=99999)
    title:str=Field(default='',max_length=200)
    volume_id:str|None=None
    source:str|None=None
    etag:str|None=None

class Recovery(Strict):
    path:str=Field(max_length=300)
    etag:str=Field(min_length=64,max_length=64)
    content:str=Field(max_length=2*1024*1024)

class EditorPosition(Strict):
    anchor:int=Field(default=0,ge=0,le=2*1024*1024)
    head:int=Field(default=0,ge=0,le=2*1024*1024)
    top:float=Field(default=0,ge=0,le=100000000)
    revision:str=Field(default='',max_length=64)

class ReferencePosition(Strict):
    scope:str=Field(pattern=r'^[A-Za-z0-9_-]{1,120}$')
    source:str=Field(pattern=r'^[A-Za-z0-9_-]{1,120}$')
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,120}$')
    hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    unit:str=Field(min_length=1,max_length=120)
    top:float=Field(default=0,ge=0,le=100000000)

from typing import Literal
UiLocale = Literal['zh-CN','zh-TW','en','ja','ko','es','fr','de','ru','pt-BR','pt-PT','it','nl','pl','uk','tr','id','vi','th','ms','hi','bn','ur','ar','fa','he']

class WorkspaceView(Strict):
    nav_open:bool=True
    ai_open:bool=False
    focus_mode:bool=False
    nav_width:int=Field(default=248,ge=190,le=340)
    ai_width:int=Field(default=330,ge=280,le=460)
    reference_width:int=Field(default=420,ge=320,le=640)
    referenceOpen:bool=False
    layout:dict[Literal['manuscript','reference'],float]=Field(default_factory=lambda:{'manuscript':62,'reference':38},min_length=2,max_length=2)

    @field_validator('layout')
    @classmethod
    def valid_layout(cls,value):
        if not 25<=value.get('reference',0)<=60 or not 40<=value.get('manuscript',0)<=75 or abs(sum(value.values())-100)>.1:raise ValueError('参考分栏比例必须合计 100%')
        return value

class Preferences(Strict):
    ui_language:UiLocale|None=None
    ai_response_language:Literal['project','zh-CN','zh-TW','en','ja','ko','es','fr','de','ru','pt-BR','pt-PT','it','nl','pl','uk','tr','id','vi','th','ms','hi','bn','ur','ar','fa','he']='project'

    settings_section:str=Field(default='general',pattern='^(general|appearance|writing|api|models|assistant|plugins|images|storage|backup|keys|help)$')
    theme:str='light'
    appearance:ThemeId='moon'
    previous_appearance:ThemeId|None=None
    theme_favorites:list[ThemeId]=Field(default_factory=list,max_length=16)
    theme_customizations:dict[ThemeId,ThemeCustomization]=Field(default_factory=dict,max_length=16)
    decorations:bool=True
    animations:bool=True
    font_size:int=Field(default=19,ge=14,le=32)
    line_height:float=Field(default=1.95,ge=1.3,le=2.8)
    editor_width:int=Field(default=760,ge=480,le=1100)
    indentation:bool=False
    recovery:bool=True
    autosave:bool=True
    autosave_delay:int=Field(default=1800,ge=800,le=15000)
    font_family:str='Microsoft YaHei'
    ui_font_family:str=Field(default='Microsoft YaHei UI',min_length=1,max_length=120)
    ui_font_size:int=Field(default=14,ge=13,le=18)
    scale:int=Field(default=100,ge=80,le=150)
    count_mode:str='both'
    opening:str='last'
    last_project:str|None=None
    last_files:dict[str,str]=Field(default_factory=dict)
    last_edited_files:dict[str,str]=Field(default_factory=dict,max_length=500)
    nav_width:int=Field(default=248,ge=190,le=340)
    ai_width:int=Field(default=330,ge=280,le=460)
    nav_open:bool=True
    ai_open:bool=False
    companion_visible:bool|None=None  # None: show an already configured local model on first use.
    focus_mode:bool=False
    reading_mode:bool=False
    simple_navigation:bool=Field(default=False,exclude=True)
    closed_volumes:dict[str,list[str]]=Field(default_factory=dict,max_length=500)
    editor_positions:dict[str,EditorPosition]=Field(default_factory=dict,max_length=500)
    reference_width:int=Field(default=420,ge=320,le=640)
    recent_characters:dict[str,list[str]]=Field(default_factory=dict,max_length=500)
    workspaces:dict[str,dict]=Field(default_factory=dict,max_length=500)

    @field_validator('workspaces')
    @classmethod
    def safe_workspace_themes(cls,workspaces):
        # Preferences is also used by backup import and restore. Keep the
        # whitelist here, rather than only at the HTTP save entry point.
        for workspace in workspaces.values():
            for field in ('view','personal_layout'):
                if field in workspace:workspace[field]=WorkspaceView.model_validate(workspace[field]).model_dump()
            if 'appearance' in workspace and (not isinstance(workspace['appearance'],str) or workspace['appearance'] not in THEME_IDS):raise ValueError('作品主题设置无效')
            if 'appearance_customizations' not in workspace:continue
            custom=workspace['appearance_customizations']
            if not isinstance(custom,dict) or len(custom)>16 or any(key not in THEME_IDS for key in custom):raise ValueError('作品主题个性化设置无效')
            try:workspace['appearance_customizations']={key:ThemeCustomization.model_validate(item).model_dump(exclude_unset=True) for key,item in custom.items()}
            except (ValidationError,TypeError,ValueError) as error:raise ValueError('作品主题个性化设置无效') from error
        return workspaces


def continuation(chapters,preferences,project):
    written=[c for c in chapters if c.get('path')]
    for field in ('last_edited_files','last_files'):
        paths=preferences.get(field,{})
        path=paths.get(project) if isinstance(paths,dict) else None
        if not isinstance(path,str):continue
        for row in written:
            if any(v.get('path')==path for v in row.get('versions',[])) or row['path']==path:
                return {**row,'path':path}
    return max(written,key=lambda c:c.get('modified_at') or '',default=None)


APP_STATE_FILES={'application/preferences.json','application/reference-reading.json','application/writing-templates.json','application/ai-settings.json','application/assistant-settings.json','application/project-assistant.json'}
APP_STATE_LOCK=threading.RLock()
PROJECT_PREFS={'last_files','last_edited_files','closed_volumes','recent_characters','workspaces'}

def scoped_preferences(value,scope):
    value=Preferences.model_validate(value).model_dump()
    for key in PROJECT_PREFS:value[key]={scope:value[key][scope]} if scope in value[key] else {}
    value['editor_positions']={k:v for k,v in value['editor_positions'].items() if k.startswith(scope+':') and scope!='public'}
    value['last_project']=scope if scope!='public' and value['last_project']==scope else None
    return value

def validate_application(name,blob,scope):
    """Allow only typed UI state belonging to the backed-up scope, never credentials."""
    if name not in APP_STATE_FILES or len(blob)>(24 if name=='application/project-assistant.json' else 4)*1024*1024:raise ConsoleError('备份应用状态不受支持',422)
    value=json.loads(blob)
    if name=='application/project-assistant.json':
        from app.assistant.models import AssistantSettings
        from app.assistant.conversations import checked_scopes,PERSONAS
        if not isinstance(value,dict) or set(value)!={'schema_version','project_id','personas','conversations'} or value['schema_version']!=1 or value['project_id']!=scope:raise ConsoleError('助手备份项目作用域无效',403)
        if not isinstance(value['personas'],dict) or not set(value['personas'])<=set(PERSONAS):raise ConsoleError('助手配置身份无效',422)
        personas={k:AssistantSettings.model_validate(v).model_dump() for k,v in value['personas'].items()}
        return {**value,'personas':personas,'conversations':checked_scopes(value['conversations'])}
    if name=='application/assistant-settings.json':
        from app.assistant.models import AssistantSettings
        return AssistantSettings.model_validate(value).model_dump()
    if name=='application/ai-settings.json':
        from app.ai.center import backup_settings
        checked=backup_settings(value,scope)
        if checked!=value:raise ConsoleError('AI 备份包含凭据引用或其他项目配置',403)
        return checked
    if name=='application/writing-templates.json':
        from app.projects.writing import validate_template
        if not isinstance(value,list) or len(value)>500:raise ConsoleError('个人模板格式无效',422)
        for item in value:validate_template(item)
        return value
    if name.endswith('/preferences.json'):
        checked=scoped_preferences(value,scope)
        if checked!=Preferences.model_validate(value).model_dump():raise ConsoleError('备份偏好包含其他小说的记录',403)
        return checked
    if not isinstance(value,list) or len(value)>120:raise ConsoleError('备份阅读位置格式无效',422)
    for entry in value:
        data={k:v for k,v in entry.items() if k!='at'};position=ReferencePosition.model_validate(data)
        if position.scope not in {scope,'public'} or position.source not in {position.scope,'public'}:raise ConsoleError('备份阅读位置跨越小说权限',403)
        datetime.fromisoformat(entry['at'])
    return value

def application_backup(root,scope,private_history=True):
    from app.library.storage import read
    with APP_STATE_LOCK:
        values={'application/preferences.json':scoped_preferences(read(root/'preferences.json',{}),scope),
                'application/reference-reading.json':[r for r in read(root/'reference-reading.json',[]) if r.get('scope') in {scope,'public'} and r.get('source') in {r.get('scope'),'public'}][:120],
                'application/writing-templates.json':read(root/'writing-templates.json',[])}
        from app.ai.center import backup_settings
        values['application/ai-settings.json']=backup_settings(read(root/'ai-settings.json',{}),scope)
        from app.assistant.models import AssistantSettings
        values['application/assistant-settings.json']=AssistantSettings.model_validate(read(root/'assistant-settings.json',{})).model_dump()
        if scope!='public':
            from app.assistant.conversations import Conversations,PERSONAS
            from app.ai.models import Preferences as AIPreferences
            global_cfg=read(root/'assistant-settings.json',{});personas=read(root/'assistant-personas.json',{});overrides=read(root/'assistant-projects.json',{}).get(scope,{})
            configs={k:AssistantSettings.model_validate({**global_cfg,**(personas.get(k,{}) if k!='assistant' else {}),**overrides.get(k,{})}).model_dump() for k in PERSONAS}
            ai=AIPreferences.model_validate(read(root/'ai-settings.json',{}))
            refs={'codex','codex-software',*[p.provider_id+'::'+m.id for p in ai.providers for m in p.available_models],*[v['model'] for v in configs.values()]}
            refs.update(str(v['provider'])+'::'+str(v['model']) for v in read(root/'ai-usage.json',[]) if v.get('project')==scope and v.get('provider') and v.get('model'))
            values['application/project-assistant.json']={'schema_version':1,'project_id':scope,'personas':configs,'conversations':Conversations(root).export_project(scope,refs) if private_history else []}
        result={name:json.dumps(value,ensure_ascii=False,indent=2).encode('utf8') for name,value in values.items()}
        for name,blob in result.items():validate_application(name,blob,scope)
        return result

def restore_application(root,entries,old_scope,scope,personal=False):
    # All entries are validated before a write; only UI records are re-scoped.
    checked={name:validate_application(name,blob,old_scope) for name,blob in entries.items()}
    from app.library.storage import read,write,write_bytes,checkpoint
    with APP_STATE_LOCK:
        pending={}
        if 'application/ai-settings.json' in checked:
            from app.ai.models import Preferences as AIPreferences
            incoming=checked['application/ai-settings.json'];current=AIPreferences.model_validate(read(root/'ai-settings.json',{})).model_dump()
            if personal:
                # Preserve current credentials and merge only missing, non-sensitive providers.
                known={p['provider_id'] for p in current['providers']}
                current['providers'] += [p for p in incoming['providers'] if p['provider_id'] not in known]
            routes=incoming['projects'].get(old_scope)
            available={'codex',*['codex::'+m['id'] for m in current['codex_models']],*[p['provider_id']+'::'+m['id'] for p in current['providers'] for m in p['available_models']]}
            if routes:current['projects'][scope]={k:v for k,v in routes.items() if v in available}
            from app.ai.controls import RequestControls
            for key,value in incoming.get('controls',{}).items():
                try:kind,owner,feature,session=json.loads(key)
                except (ValueError,TypeError):continue
                if owner==old_scope:
                    current['controls'][json.dumps([kind,scope,feature,session],separators=(',',':'))]=RequestControls.model_validate(value).model_dump(exclude_unset=True)
                elif personal and owner=='':current['controls'].setdefault(key,RequestControls.model_validate(value).model_dump(exclude_unset=True))
            if personal:
                for name,value in incoming.get('control_presets',{}).items():current['control_presets'].setdefault(name,RequestControls.model_validate(value).model_dump(exclude_unset=True))
            pending['ai-settings.json']=AIPreferences.model_validate(current).model_dump()
        if personal and 'application/writing-templates.json' in checked:
            merged={r['id']:r for r in read(root/'writing-templates.json',[])}
            for r in checked['application/writing-templates.json']:merged.setdefault(r['id'],r)
            pending['writing-templates.json']=list(merged.values())
        if personal and 'application/assistant-settings.json' in checked:pending['assistant-settings.json']=checked['application/assistant-settings.json']
        prefs=checked.get('application/preferences.json')
        if prefs is not None:
            current=Preferences.model_validate(read(root/'preferences.json',{})).model_dump()
            if personal:
                current.update({k:v for k,v in prefs.items() if k not in PROJECT_PREFS|{'editor_positions','last_project'}})
            for key in PROJECT_PREFS:
                if old_scope in prefs[key]:current[key][scope]=prefs[key][old_scope]
            current['editor_positions'].update({scope+k[len(old_scope):]:v for k,v in prefs['editor_positions'].items()})
            current['editor_positions']=dict(list(current['editor_positions'].items())[-500:])
            pending['preferences.json']=Preferences.model_validate(current).model_dump()
        rows=checked.get('application/reference-reading.json')
        if rows is not None:
            imported=[{**r,'scope':scope if r['scope']==old_scope else r['scope'],'source':scope if r['source']==old_scope else r['source']} for r in rows]
            merged={}
            for r in sorted([*read(root/'reference-reading.json',[]),*imported],key=lambda r:r.get('at',''),reverse=True):
                merged.setdefault((r['scope'],r['source'],r['id']),r)
            pending['reference-reading.json']=list(merged.values())[:120]
        assistant=checked.get('application/project-assistant.json')
        if assistant:
            from app.assistant.conversations import Conversations
            from app.ai.models import Preferences as AIPreferences
            ai=AIPreferences.model_validate(pending.get('ai-settings.json',read(root/'ai-settings.json',{})))
            available={'codex','codex-software',*[p.provider_id+'::'+m.id for p in ai.providers for m in p.available_models]}
            projects=read(root/'assistant-projects.json',{})
            projects[scope]=assistant['personas']
            pending['assistant-projects.json']=projects
            pending.update(Conversations(root).restored_files(scope,assistant['conversations']))
        before={name:(root/name).read_bytes() if (root/name).exists() else None for name in pending}
        for name in pending:
            if before[name] is not None:checkpoint(root,name,'PRE_RESTORE','恢复阅读与界面偏好前保留')
        try:
            for name,value in pending.items():write(root/name,value)
        except Exception:
            for name,blob in before.items():
                if blob is None:(root/name).unlink(missing_ok=True)
                else:write_bytes(root/name,blob)
            raise
    return {'reading_and_layout':bool(checked),'personal_settings':personal and prefs is not None,'project_assistant':bool(assistant),'conversation_scopes':len(assistant['conversations']) if assistant else 0}


def studio_routes(registry,planning,settings):
    router=APIRouter()
    data=Path(os.environ.get('NOVEL_STUDIO_DATA',settings.workspace/'web/runtime/studio'))
    # One prefs/recovery namespace per actual workspace, even when a user switches.
    namespace=hashlib.sha256(str(settings.workspace.resolve()).casefold().encode()).hexdigest()[:20]
    root=data/namespace
    lock=APP_STATE_LOCK

    def read_json(path,default):
        try:return json.loads(path.read_text(encoding='utf8'))
        except (OSError,ValueError):return default

    def chapter_rows(project):
        ws=registry.workspace(project)
        volumes=planning.rows(project,'volume')
        cards=planning.rows(project,'chapter')
        manual=read_json(ws.root/'metadata/manual-chapters.json',{})
        index={}
        for c in cards:
            # Existing production files use full-book numbers. Do not guess a
            # file's volume if a legacy plan repeats a number across volumes.
            n=c['number']
            if n in index: index[n]['ambiguous']=True;continue
            index[n]={'number':n,'title':c.get('title') or '未命名章节','volume_id':c['volume'],
                      'card_id':c['id'],'plan_status':c['status'],'order':c['order']}
        chapter_dir=ws.root/'chapters'
        if chapter_dir.is_dir():
            for folder in chapter_dir.iterdir():
                match=re.fullmatch(r'chapter-(\d+)',folder.name)
                if match and folder.is_dir() and not folder.is_symlink() and not folder.is_junction():
                    n=int(match[1]);index.setdefault(n,{'number':n,'title':'未命名章节','order':n,**manual.get(str(n),{})})
        for n,row in index.items():
            candidates=[]
            folder=ws.root/f'chapters/chapter-{n}'
            if folder.is_dir():
                for p in folder.iterdir():
                    if p.is_file() and p.suffix in {'.txt','.md'} and p.stem in {'draft','final'} or (p.is_file() and p.name.startswith('manual-') and p.suffix=='.txt'):
                        try:
                            rel=p.relative_to(ws.root).as_posix();ws.resolve(rel)
                            candidates.append((rel,p.stat().st_mtime,p.stem))
                        except (OSError,ConsoleError):continue
            finals=[r for r in candidates if r[2]=='final']
            revisions=sorted([r for r in candidates if r[2].startswith('manual-')],key=lambda r:r[1],reverse=True)
            drafts=[r for r in candidates if r[2]=='draft']
            preferred=(revisions or finals or drafts)
            row.update(path=preferred[0][0] if preferred else None, final_path=finals[0][0] if finals else None,
                       status='修订中' if revisions else '正式稿' if finals else '草稿' if drafts else '待写',
                       versions=[{'path':r[0],'label':'正式稿' if r[2]=='final' else '原草稿' if r[2]=='draft' else '修订稿 · '+datetime.fromtimestamp(r[1]).strftime('%m-%d %H:%M')} for r in revisions+finals+drafts])
            row['han']=row['characters']=0;row['modified_at']=None
            if preferred:
                relative=preferred[0][0];stat=ws.resolve(relative).stat()
                summary=manuscript_summary(str(ws.root),relative,stat.st_mtime_ns,stat.st_ctime_ns,stat.st_size)
                row.update({k:v for k,v in summary.items() if k!='heading_title'})
                if summary['heading_title']:row['title']=summary['heading_title']
            row['volume_id']=row.get('volume_id') or (volumes[0]['id'] if volumes else None)
        from app.projects.writing_config import story_row
        single=story_row(ws,registry.get(project))
        ordered=sorted(index.values(),key=lambda r:(next((v['number'] for v in volumes if v['id']==r['volume_id']),999),r['order']))
        return volumes,([single] if single else [])+ordered

    @router.get('/api/studio/fonts')
    def fonts(refresh:bool=False):
        from app.system_fonts import installed_fonts
        if refresh:installed_fonts.cache_clear()
        return installed_fonts()

    @router.get('/api/studio/preferences')
    def preferences():
        saved=read_json(root/'preferences.json',{})
        if 'appearance' not in saved:saved['appearance']='night' if saved.get('theme')=='dark' else 'moon'
        # A missing/unknown old skin must not prevent manual writing. Reading
        # fallback never rewrites the saved preferences or a novel.
        if saved.get('appearance') not in THEME_IDS:saved['appearance']='night' if saved.get('theme')=='dark' else 'moon'
        # A newer/removed project skin falls back for display only, retaining
        # the original file until the author explicitly saves preferences.
        for workspace in saved.get('workspaces',{}).values():
            if not isinstance(workspace,dict):continue
            if 'appearance' in workspace and (not isinstance(workspace['appearance'],str) or workspace['appearance'] not in THEME_IDS):workspace.pop('appearance')
            if isinstance(workspace.get('appearance_customizations'),dict):workspace['appearance_customizations']={key:value for key,value in workspace['appearance_customizations'].items() if key in THEME_IDS}
        prefs=Preferences.model_validate(saved)
        prefs.theme='dark' if prefs.appearance in DARK_THEMES else 'light'
        return {'preferences':prefs.model_dump(),
                'workspace':'独立演示工作区' if os.environ.get('NOVEL_DEMO') else str(settings.workspace),
                'app_data':'独立演示应用数据' if os.environ.get('NOVEL_DEMO') else str(root),
                'release':release_info(),'demo_mode':bool(os.environ.get('NOVEL_DEMO')),'desktop':bool(os.environ.get('NOVEL_DESKTOP'))}

    @router.put('/api/studio/preferences')
    def save_preferences(body:Preferences):
        body.theme='dark' if body.appearance in DARK_THEMES else 'light'
        if body.theme not in {'light','dark'} or body.opening not in {'home','last'} or body.count_mode not in {'han','characters','both'}:
            raise ConsoleError('无效写作设置',422)
        for project,value in body.workspaces.items():
            registry.get(project)
            if set(value)-{'tabs','closed','active','layout','reference','referenceOpen','simple_navigation','appearance','appearance_customizations','view','personal_layout'}:raise ConsoleError('工作区恢复字段不受支持',422)
            if 'simple_navigation' in value and not isinstance(value['simple_navigation'],bool):raise ConsoleError('个人写作布局设置无效',422)
            tabs=value.get('tabs',[]);closed=value.get('closed',[])
            if not isinstance(tabs,list) or not isinstance(closed,list) or len(tabs)>40 or len(closed)>12:raise ConsoleError('工作区标签过多',422)
            for tab in [*tabs,*closed,*([value['reference']] if value.get('reference') else [])]:
                if not isinstance(tab,dict) or set(tab)-{'key','page','title','path','target','pinned','entityType'} or len(str(tab))>1600:raise ConsoleError('恢复标签格式无效',422)
                if tab.get('entityType') not in {None,'chapter','character','entity','world','location','faction','event','asset','item','term','clue'}:raise ConsoleError('参考实体类型无效',422)
                if tab.get('path'):registry.workspace(project).resolve(tab['path'])
            layout=value.get('layout',{})
            if not isinstance(layout,dict) or any(k not in {'manuscript','reference'} or not isinstance(v,(int,float)) or not 0<=v<=100 for k,v in layout.items()):raise ConsoleError('工作区布局无效',422)
        with lock:atomic_json(root/'preferences.json',body.model_dump())
        return body.model_dump()

    @router.get('/api/studio/reference-reading')
    def reference_reading(scope:str='public'):
        if scope!='public':registry.get(scope)
        with lock:return [r for r in read_json(root/'reference-reading.json',[]) if r.get('scope')==scope and r.get('source') in {scope,'public'}]

    @router.put('/api/studio/reference-reading')
    def save_reference_reading(body:ReferencePosition):
        # UI reading progress only, stored beside preferences, outside novels.
        if body.scope!='public':registry.get(body.scope)
        if body.source not in {body.scope,'public'}:raise ConsoleError('阅读位置不能跨小说复用',409)
        doc=registry.references.source_document(body.scope,body.source,body.id)
        if doc.get('trashed') or doc['sha256']!=body.hash:raise ConsoleError('资料已删除或版本已变化',409)
        entry={**body.model_dump(),'at':datetime.now(timezone.utc).isoformat()}
        with lock:
            existing=read_json(root/'reference-reading.json',[])
            rows=[entry,*[v for v in existing if (v.get('scope'),v.get('source'),v.get('id'))!=(body.scope,body.source,body.id)]]
            atomic_json(root/'reference-reading.json',rows[:120])
        return entry

    @router.get('/api/studio/recent-reading')
    def recent_reading(project:str|None=None):
        # No project means public reading only. An explicit active project is
        # resolved through the same registry/source authorization as its reader.
        if project:registry.get(project)
        owners={'public',project} if project else {'public'}
        result=[]
        with lock:positions=read_json(root/'reference-reading.json',[])
        for entry in positions:
            owner=entry.get('scope');source=entry.get('source')
            if owner not in owners or source not in {owner,'public'}:continue
            try:
                doc=registry.references.source_document(owner,source,entry['id'])
                if doc.get('trashed'):continue
                result.append({'kind':'reference','scope':owner,'source':source,'id':entry['id'],'title':doc['metadata']['title'],
                               'at':entry['at'],'position':entry['unit'],'source_label':'公共文献' if owner=='public' else '当前小说文献',
                               'version_changed':doc['sha256']!=entry['hash']})
            except (ConsoleError,KeyError):continue
        if project:
            ws=registry.workspace(project)
            from app.library.storage import read,safe
            shelf=read(safe(ws.root,'metadata/studio/reading.json'),{})
            _,chapters=chapter_rows(project)
            names={v['path']:c for c in chapters for v in c['versions']}
            for entry in shelf.get('progress',{}).values():
                path=entry.get('path');chapter=names.get(path)
                if not chapter:continue
                try:current=ws.content(path)
                except ConsoleError:continue
                result.append({'kind':'chapter','scope':project,'source':project,'path':path,'title':chapter['title'] if chapter.get('kind')=='story' else f'第 {chapter["number"]} 章 · {chapter["title"]}',
                               'at':entry['at'],'position':entry.get('ratio',0),'source_label':'当前小说章节','version_changed':current['etag']!=entry['revision']})
        result.sort(key=lambda r:r['at'],reverse=True)
        return {'scope':project or 'public','items':result[:120]}

    @router.get('/api/studio/library')
    def library():
        registry.scan();rows=[];resume_prefs=read_json(root/'preferences.json',{})
        for id,m in registry.rows.items():
            if m['status']['phase']=='ARCHIVED':continue
            try:
                volumes,chapters=chapter_rows(id)
                written=[c for c in chapters if c['path']]
                continuing=continuation(chapters,resume_prefs,id)
                anthology=None
                if (m.get('writing') or {}).get('form')=='anthology' and getattr(registry,'book_center',None):anthology=registry.book_center.catalog(id)
                from app.library.storage import read,safe
                cover=read(safe(registry.workspace(id).root,'covers/official.json')) or {}
                writing=read(safe(registry.workspace(id).root,'metadata/studio/writing.json'),{})
                from app.writing_metrics import compact_progress
                from app.projects.writing_config import writing as writing_config
                rows.append({'writing':writing_config(m),'phase':m['status']['phase'],'goals':writing.get('goals',{}),'writing_progress':compact_progress(writing,id),'id':id,'title':m['title'],'genre':m['genre']['primary'],'author':read(safe(registry.workspace(id).root,'metadata/studio/export.json'),{}).get('author',''),'cover_url':f'/api/projects/{id}/covers/assets/{cover["asset_id"]}' if cover.get('asset_id') else None,
                             'volumes':volumes,'chapter_count':len(written),'collection_count':len(anthology['chapters']) if anthology else None,'han':sum(c['han'] for c in anthology['chapters']) if anthology else sum(c['han'] for c in written),
                             'continue_chapter':continuing,'updated_at':max([c['modified_at'] for c in written if c['modified_at']]+[m['status']['updated_at']])})
            except ConsoleError as error:rows.append({'id':id,'title':m['title'],'error':str(error)})
        return {'projects':rows,'errors':registry.errors}

    @router.get('/api/projects/{project}/studio')
    def workspace(project:str):
        volumes,chapters=chapter_rows(project)
        from app.projects.writing_config import writing
        m=registry.get(project)
        return {'title':m['title'],'writing':writing(m),'volumes':volumes,'chapters':chapters,'continue_chapter':continuation(chapters,read_json(root/'preferences.json',{}),project)}

    @router.post('/api/projects/{project}/studio/drafts',status_code=201)
    def new_draft(project:str,body:DraftRequest):
        if registry.get(project)['status']['phase']=='ARCHIVED':raise ConsoleError('归档小说只读',409)
        ws=registry.workspace(project)
        with lock,ws._save_lock:
            volumes,chapters=chapter_rows(project)
            row=next((c for c in chapters if c['number']==body.number),None)
            if row and row.get('ambiguous'):raise ConsoleError('多卷存在重复章号，请先在现有规划中明确全书章号',409)
            if body.source:
                if body.number==0 and (not row or row.get('kind')!='story'):raise ConsoleError('当前作品没有单篇正文',422)
                prefix='chapters/story' if body.number==0 and row and row.get('kind')=='story' else f'chapters/chapter-{body.number}'
                if not re.fullmatch(re.escape(prefix)+r'/(?:final|draft|manual-[a-z0-9-]+)\.(?:txt|md)',body.source):raise ConsoleError('修订来源须为所选正文',403)
                original=ws.content(body.source)
                if original['etag']!=body.etag:raise ConsoleError('来源已更新，请重新加载后创建修订稿',409)
                content=original['content'];relative=f'{prefix}/manual-{uuid.uuid4().hex}.txt'
            else:
                from app.projects.writing_config import writing
                if body.number==0:raise ConsoleError('单篇正文在创建作品时初始化；请直接打开正文',422)
                if body.volume_id not in {v['id'] for v in volumes} and not (not body.volume_id and writing(registry.get(project))['form']!='novel'):raise ConsoleError('请选择已有卷',422)
                if row and row['volume_id']!=body.volume_id:raise ConsoleError('该章号属于其他卷；不会移动既有章节',409)
                if row and row['path']:raise ConsoleError('该章已有正文，请打开或创建独立修订稿',409)
                title=body.title.strip() or (row['title'] if row else '未命名章节')
                if any(c in title for c in '\r\n'):raise ConsoleError('章节标题不能换行',422)
                content=f'第{body.number}章　{title}\n\n'
                relative=f'chapters/chapter-{body.number}/draft.txt'
            path=ws.resolve(relative);path.parent.mkdir(parents=True,exist_ok=True)
            ws.resolve(relative)
            with path.open('xb') as f:f.write(content.encode('utf8'));f.flush();os.fsync(f.fileno())
            if not body.source and not row:
                catalog=ws.root/'metadata/manual-chapters.json'
                entries=read_json(catalog,{})
                entries[str(body.number)]={'title':title,'volume_id':body.volume_id,'order':body.number}
                atomic_json(catalog,entries)
            return ws.content(relative)

    def recovery_path(project,path):
        ws=registry.workspace(project);ws.resolve(path)
        return root/'recovery'/project/(hashlib.sha256(path.encode()).hexdigest()+'.json')

    @router.get('/api/studio/recovery-index')
    def recovery_index(project:str|None=None):
        entries=[]
        if not project:return entries
        registry.get(project)
        directory=root/'recovery'
        if not directory.is_dir():return entries
        with lock:
            for item in (directory/project).glob('*.json'):
                if item.is_symlink() or not item.resolve().is_relative_to(directory.resolve()):continue
                project=item.parent.name
                try:
                    ws=registry.workspace(project)
                    value=read_json(item,{})
                    path=value.get('path','')
                    if not re.fullmatch(r'chapters/(chapter-\d+|story)/(draft|manual-[a-z0-9-]+)\.(txt|md)',path):continue
                    original=ws.content(path)
                    normalized=original['content'].replace('\r\n','\n') if original['line_ending']=='CRLF' else original['content']
                    if value.get('content')==normalized:continue
                    entries.append({'project':project,'title':registry.get(project)['title'],'path':path,'saved_at':value.get('saved_at',''),'conflict':value.get('etag')!=original['etag']})
                except (ConsoleError,KeyError,TypeError):continue
        return sorted(entries,key=lambda e:e['saved_at'],reverse=True)[:50]

    def recovery_snapshot(project,path):
        target=recovery_path(project,path)
        try:raw=target.read_bytes()
        except FileNotFoundError:return target,None,'missing'
        try:value=json.loads(raw)
        except (ValueError,UnicodeError):raise ConsoleError('恢复副本无法读取，已保留原文件，请检查后重试。',422,code='RECOVERY_INVALID')
        if not isinstance(value,dict) or value.get('path')!=path or not isinstance(value.get('content'),str):
            raise ConsoleError('恢复副本格式不完整，已保留原文件。',422,code='RECOVERY_INVALID')
        return target,value,hashlib.sha256(raw).hexdigest()

    @router.get('/api/projects/{project}/studio/recovery')
    def get_recovery(project:str,path:str):
        with lock:
            _,value,revision=recovery_snapshot(project,path)
            return {**value,'recovery_revision':revision} if value is not None else None

    @router.put('/api/projects/{project}/studio/recovery')
    def put_recovery(project:str,body:Recovery):
        # The on-disk format is unchanged. The revision is a response-only receipt.
        with lock:
            target=recovery_path(project,body.path)
            atomic_json(target,{**body.model_dump(),'saved_at':datetime.now(timezone.utc).isoformat()})
            revision=hashlib.sha256(target.read_bytes()).hexdigest()
        return {'saved':True,'recovery_revision':revision}

    @router.delete('/api/projects/{project}/studio/recovery')
    def delete_recovery(project:str,path:str,if_match:str|None=Header(default=None,alias='If-Match')):
        # Legacy explicit callers remain compatible; current automatic cleanup always supplies a strong precondition.
        expected=None
        if if_match is not None:
            match=re.fullmatch(r'"([0-9a-f]{64}|missing)"',if_match)
            if not match:raise ConsoleError('恢复副本版本校验无效，未执行清理。',422,code='RECOVERY_INVALID')
            expected=match.group(1)
        with lock:
            target=recovery_path(project,path)
            if expected is not None:
                try:current=hashlib.sha256(target.read_bytes()).hexdigest()
                except FileNotFoundError:current='missing'
                if current!='missing' and current!=expected:
                    raise ConsoleError('恢复副本已变化，较新副本已保留。请重新打开后查看。',412,code='RECOVERY_CHANGED')
            target.unlink(missing_ok=True)
        return {'deleted':True,'recovery_revision':'missing'}
    # Reuse the same business functions for controlled application actions.
    registry.studio_workspace=workspace
    registry.studio_draft=new_draft
    return router
