from app.version import release_info
import asyncio
import sqlite3
import time
import secrets
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from app.config import Settings
from app.errors import ConsoleError
from app.codex.adapter import CodexAdapter, redact
from app.models.requests import TaskRequest, FileWrite
from app.workspace.service import WorkspaceService
from app.tasks.router import TaskRouter, ROUTES
from app.tasks.manager import TaskManager
from app.tasks.storage import TaskStore
from app.projects.service import ProjectRegistry, DraftStore, NovelWorkspace, sha
from app.projects.foundation import Foundation, TYPES
from app.projects.creation import Creation,CreationEdit,InterviewRequest
from app.projects.models import DraftCreate,DraftEdit,DraftDiscard,ProjectCreate,ProjectPatch,FoundationTask,ReviewAccept,ChangeEdit
from app.domain.characters import CharacterService,CharacterCanon,CharacterSave
from app.domain.proposals import Proposals,ProposalEdit
from app.domain.planning import Planning,PlanAction
from app.domain.planning_tasks import PlanningTasks,PLANNING_TASKS
from app.domain.tasks import CharacterTasks,DomainTask,CHARACTER_TASKS
from app.integrations.research import ResearchLibrary,ResearchWrite,ResearchAction,SpecialistRequest
from app.integrations.tasks import WritingSpecialists,SPECIALIST_TASKS
from app.integrations.stack import catalog


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    ws = WorkspaceService(settings.workspace, settings.max_file_bytes)
    router = TaskRouter(ws)
    TaskStore(settings.workspace).recover()
    manager = TaskManager(ws, router)
    registry=ProjectRegistry(settings.workspace)
    drafts=DraftStore(settings.workspace)
    foundation=Foundation(settings.workspace,registry,drafts)
    creation=Creation(drafts,foundation)
    characters=CharacterService(registry);changes=Proposals(registry)
    character_tasks=CharacterTasks(registry,characters,changes,foundation)
    planning=Planning(registry,characters,changes);planning_tasks=PlanningTasks(registry,planning,characters,changes,foundation)
    research=ResearchLibrary(registry)
    specialists=WritingSpecialists(settings.workspace,registry,characters,planning,research)
    foundation.research=research
    character_tasks.research=research
    for id in registry.rows:changes.recover(id)
    managers={}
    draft_managers={}

    def project_manager(id):
        active=registry.workspace(id)
        if id not in managers:managers[id]=TaskManager(active,TaskRouter(active,settings.workspace,research=research),settings.workspace,manager._serial)
        managers[id].ai_center=ai_center
        return managers[id]

    def draft_manager(id):
        drafts.get(id)
        if id not in draft_managers:
            active=NovelWorkspace(drafts.path(id))
            draft_managers[id]=TaskManager(active,TaskRouter(active,settings.workspace),settings.workspace,manager._serial)
        draft_managers[id].ai_center=ai_center
        return draft_managers[id]
    nonce = secrets.token_urlsafe(32)
    health = {'backend': True, 'codex': False, 'checking': False, 'reason': '尚未检查；打开 AI 时检查连接'}

    async def probe():
        started=time.monotonic()
        # Preserve contemporaneous request verification on coarse Windows clock ticks.
        try:
            result=await asyncio.to_thread(CodexAdapter(ws.root).health)
            if health.get('verified_at',0)<started or result.get('codex'):health.update(result)
        except Exception as error:
            reason='Codex 连接检查失败，可重试：'+redact(str(error))[:300]
            if health.get('verified_at',0)<started:health.update(codex=False,reason=reason)
            raise ConsoleError(reason,503) from error
        finally:
            health['checking'] = False

    @asynccontextmanager
    async def lifespan(app):
        images.start();data_center.start()
        if hasattr(app.state,'automation'):app.state.automation.loop=asyncio.get_running_loop()
        yield
        await asyncio.to_thread(images.close)
        await asyncio.to_thread(data_center.close)
        await references.close()
        if hasattr(app.state,'automation'):app.state.automation.close()
        if hasattr(app.state,'assistant'):app.state.assistant.close()
        if hasattr(app.state,"audio_export"):await asyncio.to_thread(app.state.audio_export.close)
        if hasattr(app.state,"book_center"):app.state.book_center.prints.close()
        await asyncio.to_thread(speech.close)
        await manager.close()
        for scoped in [*managers.values(),*draft_managers.values()]:await scoped.close()

    app = FastAPI(title='Novel Studio', version=release_info()['version'], lifespan=lifespan)
    app.state.codex_health=health
    app.state.manager = manager
    app.state.workspace = ws
    app.state.registry=registry
    app.state.drafts=drafts
    def active_tasks():
        scopes=[('/api',manager)]+[(f'/api/projects/{id}',m) for id,m in list(managers.items())]+[(f'/api/drafts/{id}',m) for id,m in list(draft_managers.items())]
        scopes += [(f'/api/references/{scope}',m) for scope,m in list(references.managers.items())]
        rows=[{**t.public(),'cancel_url':prefix+'/tasks/'+t.id+'/cancel'} for prefix,m in scopes
                for t in list(m.tasks.values()) if t.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'} and t.runner]
        if images.worker_lease:
            for id in list(registry.rows):
                rows.extend({'id':j['id'],'type':'image','status':j['status'],'cancel_url':f'/api/projects/{id}/images/jobs/{j["id"]}/cancel'} for j in images.rows(id,'jobs') if j['status'] in {'QUEUED','RUNNING'})
        if hasattr(app.state,'audio_export'):
            rows.extend({'id':r['id'],'type':'audio_export','status':r['status'],'cancel_url':f"/api/projects/{p}/audio-export/{r['id']}/cancel"} for (p,_),r in list(app.state.audio_export.jobs.items()) if r['status'] in {'QUEUED','RUNNING','CANCELLING'})
        return rows
    app.state.active_tasks = active_tasks
    from app.studio import studio_routes
    app.include_router(studio_routes(registry, planning, settings))
    from app.companion import companion_routes
    resource_data=Path(os.environ.get('NOVEL_STUDIO_DATA',settings.workspace/'web/runtime/studio'))
    personal_companion=(resource_data.parent if os.environ.get('NOVEL_STUDIO_DATA') else resource_data)/'companion'
    resource_dist=settings.static_dir or Path(os.environ.get('NOVEL_STATIC_DIR',Path(__file__).resolve().parents[2]/'frontend/dist'))
    app.include_router(companion_routes(personal_companion,resource_dist/'companion'))
    from app.library.api import library_routes
    library,images,data_center=library_routes(registry,settings,drafts)
    from app.library.reference_api import reference_routes
    reference_router,references=reference_routes(registry,data_center.settings_path.parent,data_center)
    app.include_router(reference_router)
    app.state.references=references
    registry.references=references
    creation.references=references
    from app.ai.center import AICenter,ai_routes
    ai_center=AICenter(data_center.settings_path.parent,registry,project_manager)
    ai_center.drafts=drafts
    app.state.ai_center=ai_center;references.ai_center=ai_center;manager.ai_center=ai_center
    app.include_router(ai_routes(ai_center))
    from app.library.covers import Covers,cover_routes
    covers=Covers(images);registry.covers=covers
    app.include_router(cover_routes(covers,drafts))
    app.include_router(library)
    app.state.images=images;app.state.data_center=data_center
    from app.library.bible import Bible
    from app.studio_tools import StudioTools,studio_tool_routes
    tools=StudioTools(registry,planning,characters,Bible(registry),project_manager,data_center.settings_path.parent)
    from app.library.knowledge import Knowledge,knowledge_routes
    knowledge=Knowledge(registry,tools,references)
    registry.knowledge=knowledge;app.state.knowledge=knowledge
    app.include_router(knowledge_routes(knowledge))
    app.state.studio_tools=tools
    app.include_router(studio_tool_routes(tools))
    from app.book_center import BookCenter,book_routes
    from app.library.assets import Assets
    from app.writing_metrics import Metrics,ReadingShelf,experience_routes
    import app.writing_metrics as metrics_module
    from app.local_speech import LocalSpeech,speech_routes
    books=BookCenter(registry,planning,Assets(registry,Bible(registry)),data_center.settings_path.parent)
    from app.world_maps import WorldMaps,routes as map_routes
    app.state.world_maps=WorldMaps(registry,tools.bible,books.assets)
    app.include_router(map_routes(app.state.world_maps))
    registry.book_center=books
    metrics=Metrics(books);speech=LocalSpeech()
    from app.audio_export import AudioExport,routes as audio_export_routes
    app.state.audio_export=AudioExport(books,speech)
    app.include_router(audio_export_routes(app.state.audio_export))
    metrics_module.observer=metrics.saved
    app.state.book_center=books;app.state.metrics=metrics;app.state.speech=speech
    from app.projects.writing import Writing,writing_routes
    writing_service=Writing(registry,planning,characters,changes,foundation,tools,books,data_center,project_manager)
    app.state.writing=writing_service;app.include_router(writing_routes(writing_service))
    shelf=ReadingShelf(tools)
    app.include_router(book_routes(books));app.include_router(experience_routes(metrics,shelf));app.include_router(speech_routes(speech))
    from app.chapter_versions import ChapterVersions,chapter_version_routes
    app.state.chapter_versions=ChapterVersions(tools)
    app.include_router(chapter_version_routes(app.state.chapter_versions))
    from app.author_workbench import AuthorWorkbench,workbench_routes
    workbench=AuthorWorkbench(registry,tools,knowledge,shelf,data_center)
    app.state.workbench=workbench;app.include_router(workbench_routes(workbench))
    from app.creative.writing import WritingAssist,routes as writing_assist_routes
    writing_assist=WritingAssist(registry,tools,workbench,ai_center,project_manager,references)
    app.state.writing_assist=writing_assist;tools.writing_assist=writing_assist
    app.include_router(writing_assist_routes(writing_assist))
    from app.world_logic.service import WorldLogic, routes as world_logic_routes
    world_logic=WorldLogic(registry,knowledge,project_manager,ai_center)
    app.state.world_logic=world_logic;app.include_router(world_logic_routes(world_logic))
    from app.library.world_studio import WorldStudio,routes as world_studio_routes
    world_studio=WorldStudio(registry,ai_center,project_manager,writing_assist,world_logic)
    app.state.world_studio=world_studio;writing_assist.world_studio=world_studio;app.include_router(world_studio_routes(world_studio))
    from app.library.world_model import WorldModel,routes as world_model_routes
    world_model=WorldModel(world_studio,knowledge,references)
    app.state.world_model=world_model;world_studio.world_model=world_model
    app.include_router(world_model_routes(world_model))
    from app.roleplay.service import Roleplay,routes as roleplay_routes
    roleplay=Roleplay(registry,characters,workbench,project_manager,ai_center,world_logic)
    app.state.roleplay=roleplay;app.include_router(roleplay_routes(roleplay))
    from app.creative.materials import Materials,routes as material_routes
    creative_materials=Materials(writing_assist,roleplay,world_logic)
    app.state.creative_materials=creative_materials;app.include_router(material_routes(creative_materials))
    from app.creative.reviews import ReviewCenter,routes as literary_routes
    literary=ReviewCenter(registry,characters,tools,workbench,ai_center,project_manager,references)
    from app.creative.director import Director, routes as director_routes
    from app.creative.visual import Visual,routes as visual_routes
    visual=Visual(tools,creative_materials,Assets(registry,Bible(registry)))
    app.state.creative_visual=visual;app.include_router(visual_routes(visual))
    creative_director=Director(writing_assist,literary)
    app.state.creative_director=creative_director
    app.include_router(director_routes(creative_director))
    from app.creative.workflows import Workflows,routes as workflow_routes
    app.state.workflows=Workflows(creative_director,world_studio)
    app.include_router(workflow_routes(app.state.workflows))
    app.state.literary_review=literary;app.include_router(literary_routes(literary))
    from app.creative.plot_matrix import PlotMatrix,routes as matrix_routes
    plot_matrix=PlotMatrix(tools,ai_center)
    app.state.plot_matrix=plot_matrix;app.include_router(matrix_routes(plot_matrix))
    from app.creative.literary_core import LiteraryCore,routes as literary_core_routes
    references.literary_board=tools.board
    literary_core=LiteraryCore(writing_assist,literary,world_logic,plot_matrix)
    writing_assist.literary_core=literary_core;literary.literary_core=literary_core
    app.state.literary_core=literary_core;app.include_router(literary_core_routes(literary_core))
    from app.creative.evaluation import Evaluation,routes as evaluation_routes
    literary_evaluation=Evaluation(literary,literary_core)
    app.state.literary_evaluation=literary_evaluation;app.include_router(evaluation_routes(literary_evaluation))
    from app.creative.creative_insights import CreativeInsights,routes as insights_routes
    app.state.creative_insights=CreativeInsights(tools,plot_matrix,literary)
    app.include_router(insights_routes(app.state.creative_insights))
    from app.assistant.actions import Actions
    from app.assistant.service import AssistantCenter,assistant_routes
    assistant=AssistantCenter(app,Actions(app,characters,character_tasks,changes,planning,project_manager),project_manager)
    app.state.assistant=assistant;app.include_router(assistant_routes(assistant))
    from app.automation.service import Control,routes as control_routes
    app.state.automation=Control(assistant);app.include_router(control_routes(app.state.automation))
    from app.extensions.service import PluginHub
    from app.extensions.api import routes as plugin_routes
    app.state.plugins=PluginHub(app,data_center.settings_path.parent)
    app.include_router(plugin_routes(app.state.plugins))
    from app.live2d import LiveCompanion,live_companion_routes
    companion=LiveCompanion(personal_companion,app)
    app.state.live_companion=companion;app.include_router(live_companion_routes(companion))

    @app.get('/api/studio/running-tasks')
    async def running_tasks(): return app.state.active_tasks()

    from app.cache_maintenance import CacheMaintenance,Cleanup
    maintenance=CacheMaintenance(settings.workspace,registry)
    @app.get('/api/studio/cache-maintenance')
    def cache_preview(project:str=''):return maintenance.scan(project)
    @app.post('/api/studio/cache-maintenance')
    def cache_cleanup(body:Cleanup,project:str=''):return maintenance.cleanup(body,project)

    @app.get('/api/studio/storage-health')
    def storage_health():
        import shutil
        catalog=data_center.catalog()
        latest=max(catalog,key=lambda x:x.get('created_at',''),default={})
        indexes=list((settings.workspace/'projects').glob('*/storage/index.sqlite'))
        return {'workspace':str(settings.workspace),'app_data':str(data_center.settings_path.parent),
                'free_bytes':shutil.disk_usage(settings.workspace).free,
                'last_backup':latest.get('created_at'),'index':f'{len(indexes)} 部作品已有本地索引；可在数据中心重建',
                'codex':dict(health),'images':{'connected':False,'reason':'按需连接；请在生图页面检查服务'}}

    health_lock=asyncio.Lock()
    @app.post('/api/studio/codex/check')
    async def recheck_codex():
        if health_lock.locked() or health.get('checking'):raise ConsoleError('Codex 检查正在进行，请稍候',409)
        async with health_lock:
            health.update(checking=True,reason='正在检查本机 Codex')
            await probe()
        return health

    @app.middleware('http')
    async def local_only(request: Request, call_next):
        host = request.headers.get('host', '').split(':')[0]
        origin = request.headers.get('origin')
        if host not in {'127.0.0.1', 'localhost', 'testserver'} or (origin and origin not in settings.origins):
            return JSONResponse({'detail': '仅允许本机控制台来源'}, 403)
        if host == 'testserver' and not getattr(app.state, 'testing', False):
            return JSONResponse({'detail': '无效 Host'}, 403)
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and request.headers.get('x-novel-request') != nonce:
            return JSONResponse({'detail': '缺少本机会话请求校验','code':'SESSION_INVALID','params':{}}, 403)
        if not getattr(app.state,'testing',False) and request.url.path in ['/api/status','/api/files','/api/files/content','/api/chapters','/api/tasks']:
            return JSONResponse({'detail':'V0.3 小说操作必须使用 /api/projects/{project_id}/...'},422)
        if not getattr(app.state,'testing',False) and request.url.path.startswith(('/api/tasks/','/api/chapters/')):
            return JSONResponse({'detail':'请选择当前小说 project_id'},422)
        lease=None
        try:
            # Shared OS lease covers every HTTP mutation and image publication.
            # A cancellation must remain reachable while a Codex writer holds it.
            independent_print=request.method=='POST' and bool(__import__('re').fullmatch(r'/api/projects/novel_[0-9a-f]{32}/(?:book/print-preview(?:/[0-9a-f]{32}/cancel)?|audio-export/audio_[0-9a-f]{32}/cancel)',request.url.path))
            # This nonce-protected endpoint only reads login/runtime health, never story data.
            independent_probe=request.method=='POST' and request.url.path=='/api/studio/codex/check'
            if request.method in {'POST','PUT','PATCH','DELETE'} and not independent_print and not independent_probe and not ('/tasks/' in request.url.path and request.url.path.endswith('/cancel')):
                from app.tasks.lease import acquire
                lease=acquire(settings.workspace,'studio-data.lock')
                request.state.data_lease=lease
            response = await call_next(request)
            if lease and response.status_code in {200,201}:
                import re
                match=re.match(r'^/api/(?:projects|references)/(novel_[0-9a-f]{32})/',request.url.path)
                if match and '/tasks/' not in request.url.path:
                    # Knowledge.view/reindex validates its source stamp before every query.
                    # Saving/recovery does not need to rebuild the derived graph synchronously.
                    response.headers['X-Novel-Index']='refresh-on-query'

        except ConsoleError as error:
            return JSONResponse(error.payload(redact),error.status)
        finally:
            from app.tasks.lease import release
            release(lease)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN' if request.url.path=='/live2d/frame.html' else 'DENY'
        if request.url.path=='/live2d/frame.html':response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; object-src 'none'; form-action 'none'; frame-ancestors 'self'"
        if request.url.path.startswith('/api'): response.headers['Cache-Control'] = 'no-store'
        elif request.url.path.startswith('/locales/'): response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.exception_handler(OSError)
    async def storage_error(request, error):
        import errno
        message='本地文件操作失败，请检查存储目录与文件是否可用；当前编辑尚未确认保存。'
        status=503;code='LOCAL_SERVICE_UNAVAILABLE'
        if error.errno==errno.ENOSPC:message='磁盘空间不足，请释放空间后重试；未确认保存成功。';status=507;code='STORAGE_FULL'
        elif isinstance(error,PermissionError):message='数据目录不可写或文件正在被占用，请检查目录权限后重试；未确认保存成功。';code='STORAGE_PERMISSION'
        elif isinstance(error,FileNotFoundError):message='所需文件不存在，请刷新或从备份恢复。';status=404;code='FILE_NOT_FOUND'
        return JSONResponse({'detail':message,'code':code,'params':{},'fallback_message':message},status)

    @app.exception_handler(sqlite3.OperationalError)
    async def index_error(request, error):
        return JSONResponse({'detail':'本地索引暂时不可用或被占用，请稍后重试；未执行自动覆盖或清理。','code':'INDEX_UNAVAILABLE','params':{}},503)

    @app.exception_handler(ConsoleError)
    async def domain_error(request, error):
        return JSONResponse({**error.payload(redact), **({'ai_notice':error.ai_notice} if hasattr(error,'ai_notice') else {})}, error.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Never echo submitted values (a mistyped secret/command is still input).
        summary = '; '.join('.'.join(map(str, row['loc'])) + ': ' + row['msg'] for row in error.errors())
        return JSONResponse({'detail': redact(summary),'code':'INVALID_REQUEST','params':{}}, 422)

    @app.exception_handler(ValidationError)
    async def invalid_model(request,error):
        summary='; '.join('.'.join(map(str,row['loc']))+': '+row['msg'] for row in error.errors())
        return JSONResponse({'detail':redact(summary)},422)

    @app.exception_handler(Exception)
    async def unknown_error(request, error):
        return JSONResponse({'detail': '本地服务错误：' + redact(str(error))[:800]}, 500)

    @app.get('/api/session')
    async def session(): return {'request_token': nonce}

    @app.get('/api/health')
    async def get_health(): return {**health, 'workspace': str(ws.root),'console_version':'0.6.0'}

    @app.get('/api/status')
    async def status():
        result = await asyncio.to_thread(ws.status)
        result['recent_tasks'] = [t.public() for t in list(manager.tasks.values())[-5:][::-1]]
        return result

    @app.get('/api/files')
    async def files(): return await asyncio.to_thread(ws.list_files)

    @app.get('/api/files/content')
    async def content(path: str): return await asyncio.to_thread(ws.content, path, allow_reviews=True)

    @app.put('/api/files/content')
    async def save(body: FileWrite): return await asyncio.to_thread(ws.save, body.path, body.content, body.etag)

    @app.get('/api/chapters')
    async def chapters(): return await asyncio.to_thread(ws.chapters)

    @app.get('/api/chapters/{number}')
    async def chapter(number: int):
        if not 1 <= number <= 99999: raise ConsoleError('无效章节号', 422)
        return {**ws.chapter(number), 'availability': router.availability(number)}

    @app.get('/api/task-types')
    async def task_types(): return list(dict.fromkeys(list(ROUTES) + TYPES + CHARACTER_TASKS + PLANNING_TASKS + SPECIALIST_TASKS + ['custom_prompt']))

    @app.get('/api/writing-stack')
    async def writing_stack():return catalog(settings.workspace)

    @app.get('/api/projects/{project_id}/research')
    async def research_list(project_id:str,query:str='',archived:bool=False):
        return research.list(project_id,query,archived)

    @app.get('/api/projects/{project_id}/research/{topic_id}')
    async def research_get(project_id:str,topic_id:str):return research.get(project_id,topic_id)

    @app.put('/api/projects/{project_id}/research/{topic_id}')
    async def research_edit(project_id:str,topic_id:str,body:ResearchWrite):
        return research.save(project_id,topic_id,body.content,body.etag)

    @app.post('/api/projects/{project_id}/research/{topic_id}/archive')
    async def research_archive(project_id:str,topic_id:str,body:ResearchAction):
        return research.archive(project_id,topic_id,body)

    @app.get('/api/projects')
    async def projects(include_archived:bool=False):
        return {'projects':await asyncio.to_thread(registry.list,include_archived),'registry_errors':registry.errors}

    @app.post('/api/projects',status_code=201)
    async def create_project(body:ProjectCreate):
        # Exact Windows deny roots are materialized for the duration of a task.
        # Do not introduce a new sibling while that permission snapshot is live.
        if any(t.status in ['RUNNING','CANCELLING'] for scoped in [manager,*managers.values(),*draft_managers.values()] for t in scoped.tasks.values()):raise ConsoleError('Codex 任务运行中，请结束后确认创建项目',409)
        async with manager._serial:
            return await asyncio.to_thread(registry.create,drafts,body)

    @app.get('/api/projects/{project_id}')
    async def project(project_id:str):
        return {'manifest':registry.get(project_id),'etag':registry.workspace(project_id).content('project.yaml')['etag']}

    @app.patch('/api/projects/{project_id}')
    async def patch_project(project_id:str,body:ProjectPatch):return registry.patch(project_id,body.etag,body.title,body.phase)

    @app.post('/api/projects/{project_id}/archive')
    async def archive_project(project_id:str,body:ProjectPatch):return registry.patch(project_id,body.etag,phase='ARCHIVED')

    @app.get('/api/projects/{project_id}/status')
    async def project_status(project_id:str):
        result=await asyncio.to_thread(registry.status,project_id)
        result['recent_tasks']=[t.public() for t in list(project_manager(project_id).tasks.values())[-5:][::-1]]
        return result

    @app.get('/api/projects/{project_id}/files')
    async def project_files(project_id:str):return registry.workspace(project_id).list_files(include_reviews=True)

    @app.get('/api/projects/{project_id}/files/content')
    async def project_content(project_id:str,path:str):return registry.workspace(project_id).content(path,allow_reviews=True)

    @app.put('/api/projects/{project_id}/files/content')
    async def project_save(project_id:str,body:FileWrite):
        if registry.get(project_id)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
        if body.path.startswith(('outlines/volumes/','outlines/chapters/')) and body.path.endswith('.yaml'):planning.validate(project_id,[{'path':body.path,'content':body.content,'action':'write'}])
        result=registry.workspace(project_id).save(body.path,body.content,body.etag)
        if body.path.startswith('chapters/'):
            try:await asyncio.to_thread(tools.index,project_id)
            except Exception:result['index_warning']='正文已保存；检索索引暂不可用，可在数据中心重建。'
        return result

    @app.get('/api/projects/{project_id}/chapters')
    async def project_chapters(project_id:str):return registry.workspace(project_id).chapters()

    @app.get('/api/projects/{project_id}/chapters/{number}')
    async def project_chapter(project_id:str,number:int):
        if not 1<=number<=99999:raise ConsoleError('无效章号',422)
        active=registry.workspace(project_id)
        return {**active.chapter(number),'availability':project_manager(project_id).router.availability(number)}

    @app.get('/api/projects/{project_id}/proposals/{change_id}')
    async def project_proposal(project_id:str,change_id:str):return foundation.review(project_id,change_id)

    @app.post('/api/projects/{project_id}/proposals/{change_id}/accept')
    async def accept_change(project_id:str,change_id:str,body:ReviewAccept):return foundation.accept(project_id,change_id,body)

    @app.patch('/api/projects/{project_id}/proposals/{change_id}')
    async def edit_change(project_id:str,change_id:str,body:ChangeEdit):return foundation.edit(project_id,change_id,body)

    @app.post('/api/projects/{project_id}/proposals/{change_id}/discard')
    async def discard_change(project_id:str,change_id:str,body:ReviewAccept):return foundation.discard(project_id,change_id,body)

    @app.get('/api/projects/{project_id}/files/revision')
    async def file_revision(project_id:str,path:str):
        content=await asyncio.to_thread(registry.workspace(project_id).content,path)
        return {k:content[k] for k in ['path','etag','modified_at']}

    @app.get('/api/projects/{project_id}/characters')
    async def character_list(project_id:str):return characters.list(project_id)

    @app.get('/api/projects/{project_id}/character-template')
    async def character_template(project_id:str):
        registry.get(project_id);return CharacterCanon(id='temporary').model_dump()

    @app.post('/api/projects/{project_id}/characters',status_code=201)
    async def character_create(project_id:str,body:CharacterCanon):return characters.create(project_id,body.model_dump())

    @app.get('/api/projects/{project_id}/characters/{character_id}')
    async def character_get(project_id:str,character_id:str):return characters.get(project_id,character_id)

    @app.put('/api/projects/{project_id}/characters/{character_id}')
    async def character_save(project_id:str,character_id:str,body:CharacterSave):
        return characters.save(project_id,character_id,body.canonical.model_dump(),body.etag)

    @app.get('/api/projects/{project_id}/changes/{change_id}')
    async def domain_change(project_id:str,change_id:str):return changes.get(project_id,change_id)

    @app.post('/api/projects/{project_id}/changes/{change_id}/accept')
    async def domain_accept(project_id:str,change_id:str,body:ReviewAccept):
        value=changes.get(project_id,change_id)
        if value['kind'] in PLANNING_TASKS:return changes.commit(project_id,change_id,body.version,lambda ops:planning.validate(project_id,ops))
        return changes.commit(project_id,change_id,body.version,lambda ops:character_tasks.validate(project_id,ops),initialize=lambda value:[init for op in value['operations'] for init in characters.runtime_initializations(registry.workspace(project_id),registry.workspace(project_id).parse_yaml(op['content']))])

    @app.patch('/api/projects/{project_id}/changes/{change_id}')
    async def domain_edit(project_id:str,change_id:str,body:ProposalEdit):
        value=body.model_dump();old=changes.get(project_id,change_id)
        validator=planning.validate if old['kind'] in PLANNING_TASKS else character_tasks.validate
        return changes.update(project_id,change_id,value['version'],value['operations'],lambda ops:validator(project_id,ops))

    @app.post('/api/projects/{project_id}/changes/{change_id}/discard')
    async def domain_discard(project_id:str,change_id:str,body:ReviewAccept):return changes.discard(project_id,change_id,body.version)

    @app.get('/api/projects/{project_id}/planning')
    async def planning_board(project_id:str,volume:str|None=None):return planning.board(project_id,volume)

    @app.get('/api/projects/{project_id}/planning/{kind}/{stable_id}')
    async def planning_detail(project_id:str,kind:str,stable_id:str):return planning.get(project_id,stable_id,kind)

    @app.post('/api/projects/{project_id}/planning/actions')
    async def planning_action(project_id:str,body:PlanAction):return planning.manual(project_id,body)

    @app.post('/api/drafts',status_code=201)
    async def create_draft(body:DraftCreate):
        if any(t.status=='RUNNING' for scoped in [manager,*managers.values(),*draft_managers.values()] for t in scoped.tasks.values()):raise ConsoleError('Codex 任务运行中，请结束后新建草稿',409)
        async with manager._serial:return drafts.create(body.input)

    @app.get('/api/drafts')
    async def list_drafts():return drafts.list()

    @app.post('/api/drafts/{draft_id}/discard')
    async def discard_draft(draft_id:str,body:DraftDiscard):
        if any(t.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'} for t in draft_manager(draft_id).tasks.values()):raise ConsoleError('请先结束草稿任务',409)
        async with manager._serial:return drafts.discard(draft_id,body.version)

    @app.get('/api/drafts/{draft_id}')
    async def draft(draft_id:str):return drafts.get(draft_id)

    @app.get('/api/drafts/{draft_id}/creation')
    async def creation_view(draft_id:str):return creation.view(draft_id)

    @app.patch('/api/drafts/{draft_id}/creation')
    async def creation_edit(draft_id:str,body:CreationEdit):return creation.edit(draft_id,body)

    @app.post('/api/drafts/{draft_id}/creation/tasks',status_code=202)
    async def creation_task(draft_id:str,body:InterviewRequest):
        # Persist the author message before an unavailable provider is reported.
        return creation.start(draft_id,body,draft_manager(draft_id)).public()

    @app.post('/api/drafts/{draft_id}/creation/context')
    async def creation_context(draft_id:str,body:InterviewRequest):
        return creation.start(draft_id,body,draft_manager(draft_id),preview=True)

    @app.post('/api/drafts/{draft_id}/creation/branch')
    async def creation_branch(draft_id:str,body:DraftDiscard):
        return creation.branch(draft_id,body.version)

    @app.patch('/api/drafts/{draft_id}')
    async def draft_edit(draft_id:str,body:DraftEdit):
        changes={}
        if body.input:changes['input']=body.input.model_dump()
        if body.proposal:changes['proposal']=body.proposal.model_dump()
        if body.discard_proposal:changes.update(proposal=None,accepted=False)
        if body.wizard_step is not None:changes['wizard_step']=body.wizard_step
        if body.accepted is not None:changes['accepted']=body.accepted
        return drafts.update(draft_id,body.version,**changes)

    @app.get('/api/drafts/{draft_id}/discovery')
    async def draft_discovery(draft_id:str):
        drafts.get(draft_id)
        return await asyncio.to_thread(CodexAdapter(drafts.path(draft_id),settings.workspace).health)

    @app.post('/api/drafts/{draft_id}/tasks',status_code=202)
    async def draft_start(draft_id:str,body:FoundationTask):
        from app.ai.center import GROUPS
        group=GROUPS.get(body.type)
        if not health.get('codex') and (not group or ai_center.choose(draft_id,group)[0] is None):raise ConsoleError('Codex 未就绪',503)
        return foundation.start_draft(draft_id,body,draft_manager(draft_id)).public()

    @app.post('/api/projects/{project_id}/tasks',status_code=202)
    async def project_start(project_id:str,request:Request):
        if registry.get(project_id)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
        data=await request.json()
        from app.ai.center import GROUPS
        group=GROUPS.get(data.get('type'))
        if not health.get('codex') and (not group or ai_center.choose(project_id,group)[0] is None):raise ConsoleError('Codex 未就绪',503)
        if data.get('type') in SPECIALIST_TASKS:return specialists.start(project_id,SpecialistRequest.model_validate(data),project_manager(project_id)).public()
        if data.get('type') in PLANNING_TASKS:return planning_tasks.start(project_id,DomainTask.model_validate(data),project_manager(project_id)).public()
        if data.get('type') in CHARACTER_TASKS:return character_tasks.start(project_id,DomainTask.model_validate(data),project_manager(project_id)).public()
        if data.get('type') in TYPES:return foundation.start_project(project_id,FoundationTask.model_validate(data),project_manager(project_id)).public()
        return project_manager(project_id).start(TaskRequest.model_validate(data)).public()

    # Scope is part of every task URL: IDs from another project cannot be resolved.
    def register_task_reads(prefix,lookup):
        async def scoped_list(scope_id:str):return [t.public() for t in list(lookup(scope_id).tasks.values())[::-1]]
        async def scoped_task(scope_id:str,task_id:str):return lookup(scope_id).get(task_id).public()
        async def scoped_cancel(scope_id:str,task_id:str):return (await lookup(scope_id).cancel(task_id)).public()
        async def scoped_log(scope_id:str,task_id:str):
            m=lookup(scope_id);m.get(task_id);return m.store.page(task_id)['events']
        async def scoped_log_page(scope_id:str,task_id:str,before:int|None=None,limit:int=200):
            m=lookup(scope_id);m.get(task_id);return m.store.page(task_id,before,limit)
        async def scoped_events(scope_id:str,task_id:str,request:Request,after:int=0):
            m=lookup(scope_id);m.get(task_id)
            try:cursor=max(after,int(request.headers.get('last-event-id','0')))
            except ValueError:raise ConsoleError('无效事件序号',422)
            return StreamingResponse(m.events(task_id,cursor),media_type='text/event-stream',headers={'X-Accel-Buffering':'no','Cache-Control':'no-cache'})
        app.add_api_route(prefix+'/tasks',scoped_list,methods=['GET'])
        app.add_api_route(prefix+'/tasks/{task_id}',scoped_task,methods=['GET'])
        app.add_api_route(prefix+'/tasks/{task_id}/cancel',scoped_cancel,methods=['POST'])
        app.add_api_route(prefix+'/tasks/{task_id}/log',scoped_log,methods=['GET'])
        app.add_api_route(prefix+'/tasks/{task_id}/log-page',scoped_log_page,methods=['GET'])
        app.add_api_route(prefix+'/tasks/{task_id}/events',scoped_events,methods=['GET'])
    register_task_reads('/api/projects/{scope_id}',project_manager)
    register_task_reads('/api/drafts/{scope_id}',draft_manager)

    @app.get('/api/history')
    async def history(project_id:str|None=None,type:str|None=None,status:str|None=None,offset:int=0,limit:int=50):
        if project_id:registry.get(project_id)
        rows=TaskStore(settings.workspace).rows()
        if project_id:rows=[r for r in rows if r['project_id']==project_id]
        if type:rows=[r for r in rows if r['type']==type]
        if status:rows=[r for r in rows if r['status']==status]
        visible=[]
        for r in rows[::-1][max(0,offset):max(0,offset)+min(max(1,limit),100)]:
            r=dict(r);r.pop('request',None);r.pop('workspace',None);r.pop('result',None)
            try:r['project_title']=registry.get(r['project_id'])['title'] if r['project_id'].startswith('novel_') else drafts.get(r['project_id'])['input']['title']
            except ConsoleError:r['project_title']='已结束草稿 / 旧工作区'
            visible.append(r)
        return {'tasks':visible,'total':len(rows)}

    @app.get('/api/history/{task_id}')
    async def history_detail(task_id:str):
        store=TaskStore(settings.workspace);store.path(task_id)
        row=next((r for r in store.rows() if r['id']==task_id),None)
        if row is None:raise ConsoleError('历史任务不存在',404)
        row.pop('request',None);row.pop('workspace',None);return row

    @app.get('/api/history/{task_id}/log-page')
    async def history_log(task_id:str,before:int|None=None,limit:int=100):
        await history_detail(task_id);return TaskStore(settings.workspace).page(task_id,before,limit)

    @app.get('/api/tasks')
    async def tasks(): return [t.public() for t in list(manager.tasks.values())[::-1]]

    @app.post('/api/tasks', status_code=202)
    async def start(body: TaskRequest):
        if not health.get('codex'):
            raise ConsoleError(health.get('reason') or 'Codex 尚未就绪', 503)
        return manager.start(body).public()

    @app.get('/api/tasks/{task_id}')
    async def task(task_id: str): return manager.get(task_id).public()

    @app.post('/api/tasks/{task_id}/cancel')
    async def cancel(task_id: str): return (await manager.cancel(task_id)).public()

    @app.get('/api/tasks/{task_id}/events')
    async def events(task_id: str, request: Request, after: int = 0):
        manager.get(task_id)
        try: cursor = max(after, int(request.headers.get('last-event-id', '0')))
        except ValueError: raise ConsoleError('无效事件序号', 422)
        return StreamingResponse(manager.events(task_id, cursor), media_type='text/event-stream',
                                 headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'})

    @app.get('/api/tasks/{task_id}/log')
    async def log(task_id: str): return list(manager.get(task_id).events)

    dist = settings.static_dir or Path(os.environ.get('NOVEL_STATIC_DIR', Path(__file__).resolve().parents[2] / 'frontend/dist'))
    if dist.is_dir():
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')
        if (dist / 'locales').is_dir():
            app.mount('/locales', StaticFiles(directory=dist / 'locales'), name='locales')
        if (dist / 'i18n-help').is_dir():
            app.mount('/i18n-help', StaticFiles(directory=dist / 'i18n-help'), name='i18n-help')
        if (dist / 'live2d').is_dir():
            app.mount('/live2d', StaticFiles(directory=dist / 'live2d'), name='live2d-ui')
        if (dist / 'pdf').is_dir():
            app.mount('/pdf', StaticFiles(directory=dist / 'pdf'), name='pdf')
        @app.get('/')
        async def index(): return FileResponse(dist / 'index.html',headers={'Cache-Control':'no-store'})
    return app


app = create_app()
