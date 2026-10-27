import difflib
import hashlib
import json
import os
import re
import uuid
from pathlib import Path
import yaml
from fastapi import APIRouter,Request
from fastapi.responses import FileResponse,Response
from app.errors import ConsoleError
from .bible import Bible
from .assets import Assets,MAX_BYTES,CATEGORIES
from .comfy import ImageStudio,compatible,TASK_TYPES
from .data import DataCenter,MAX_ARCHIVE
from .storage import safe,read,write,write_bytes,checkpoint,revisions,revision_content,digest,rebuild,search,now,write_guard

async def limited(request,maximum):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>maximum:raise ConsoleError('上传超过大小限制',413)
    return bytes(data)

def library_routes(registry,settings,drafts=None):
    router=APIRouter(prefix='/api')
    namespace=hashlib.sha256(str(settings.workspace.resolve()).casefold().encode()).hexdigest()[:20]
    config=Path(os.environ.get('NOVEL_STUDIO_DATA',settings.workspace/'web/runtime/studio'))/namespace
    bible=Bible(registry);assets=Assets(registry,bible)
    if drafts is not None:
        from .covers import CoverScopes
        scopes=CoverScopes(registry,drafts);image_bible=Bible(scopes);image_assets=Assets(scopes,image_bible)
    else:scopes=registry;image_bible=bible;image_assets=assets
    images=ImageStudio(scopes,image_bible,image_assets,config/'comfy.json');data=DataCenter(registry,config/'data-settings.json')

    @router.get('/studio/image-service')
    def image_status():
        provider=images.provider()
        try:return {**provider.status(),'config':images.config(),'task_types':TASK_TYPES,'categories':CATEGORIES,'worker_available':bool(images.worker_lease)}
        finally:provider.close()
    @router.put('/studio/image-service')
    def configure_images(body:dict):return images.configure(body)
    @router.get('/studio/data-settings')
    def data_settings():return {**data.config(),'last_error':read(config/'backup-error.json')}
    @router.put('/studio/data-settings')
    def save_data_settings(body:dict):return data.configure(body)
    @router.post('/studio/backups/inspect')
    async def inspect_backup(request:Request):return data.stage(await limited(request,MAX_ARCHIVE))
    @router.post('/studio/backups/restore')
    def restore_backup(body:dict):return data.restore(body.get('token'),body.get('mode','new'),body.get('target'),body.get('confirm',''),body.get('chapter'),body.get('sha256'),body.get('personal_settings') is True)

    @router.get('/projects/{p}/bible')
    def get_bible(p:str):
        ws=registry.workspace(p)
        legacy=[{'path':r['path'],'name':r['name']} for r in ws.list_files() if r['path'].startswith(('bible/','settings/')) and not r['path'].startswith(('bible/entities/','bible/designs/','bible/template-versions/')) and r['path'] not in {'bible/categories.json','bible/relations.json','bible/blueprint.json'}]
        return {'categories':bible.categories(p),'entities':bible.list(p),'relations':bible.relations(p),'targets':bible.targets(p),'legacy':legacy}
    @router.post('/projects/{p}/bible/categories')
    def category(p:str,body:dict):return bible.category(p,body)
    @router.post('/projects/{p}/bible/entities')
    def save_entity(p:str,body:dict):return bible.save(p,body['entity'],body.get('etag'),body.get('approve') is True)
    @router.post('/projects/{p}/bible/entities/{id}/unlock')
    def unlock(p:str,id:str,body:dict):
        row=bible.get(p,id)
        if body.get('confirm')!='解锁 '+row['name'] or body.get('etag')!=row.pop('etag'):raise ConsoleError('请明确确认解锁且使用最新版本',409)
        row.update(status='FORMAL',locked_fields=[],version=row['version']+1,updated_at=now());write(safe(bible.root(p),'bible/entities/'+id+'.json'),row);return bible.get(p,id)
    @router.post('/projects/{p}/bible/relations')
    def link(p:str,body:dict):return bible.link(p,body)
    @router.delete('/projects/{p}/bible/relations/{id}')
    def unlink(p:str,id:str):
        if id.startswith('field:'):raise ConsoleError('请编辑实体对应字段以解除这项关联',409)
        rows=bible.explicit_relations(p);write(safe(bible.root(p),'bible/relations.json'),{'relations':[r for r in rows if r['id']!=id]});return {'ok':True}
    @router.post('/projects/{p}/bible/entities/{id}/copy')
    def copy_entity(p:str,id:str,body:dict):return bible.copy(p,id,body['target_project'])

    @router.get('/projects/{p}/assets')
    def asset_list(p:str):return {'assets':assets.list(p),'targets':bible.targets(p),'categories':CATEGORIES}
    @router.post('/projects/{p}/assets/import')
    async def import_asset(p:str,request:Request,name:str='图片'):return assets.import_image(p,await limited(request,MAX_BYTES),name)
    @router.put('/projects/{p}/assets/{id}')
    def asset_update(p:str,id:str,body:dict):return assets.update(p,id,body['changes'],body['etag'])
    @router.get('/projects/{p}/assets/{id}/file')
    def asset_file(p:str,id:str,thumbnail:bool=False,download:bool=False):
        path=assets.path(p,id,thumbnail);return FileResponse(path,filename=path.name if download else None,headers={'Cache-Control':'private, max-age=60'})

    @router.get('/projects/{p}/images')
    def image_library(p:str):return {'workflows':images.rows(p,'workflows'),'styles':images.rows(p,'styles'),'jobs':images.rows(p,'jobs'),'targets':bible.targets(p),'task_types':TASK_TYPES,'assets':assets.list(p)}
    @router.post('/projects/{p}/images/workflows')
    def workflow_save(p:str,body:dict):return images.put_workflow(p,body)
    @router.post('/projects/{p}/images/workflows/{id}/check')
    def workflow_check(p:str,id:str):
        provider=images.provider()
        try:return compatible(images.get(p,'workflows',id),provider.object_info())
        except Exception as e:raise ConsoleError('工作流兼容性尚未验证：'+str(e)[:1000],503) from e
        finally:provider.close()
    @router.post('/projects/{p}/images/styles')
    def style_save(p:str,body:dict):return images.put_style(p,body)
    @router.delete('/projects/{p}/images/{kind}/{id}')
    def remove_preset(p:str,kind:str,id:str):
        if kind not in {'styles','workflows'}:raise ConsoleError('不能删除生成历史',403)
        images.get(p,kind,id);root=images.root(p);rel=f'art/{kind}/{id}.json';checkpoint(root,rel,'PRE_DELETE','删除预设前保留');safe(root,rel).unlink();return {'ok':True}
    @router.post('/projects/{p}/images/jobs')
    def enqueue(p:str,body:dict):return images.enqueue(p,body)
    @router.post('/projects/{p}/images/jobs/{id}/cancel')
    def cancel(p:str,id:str):return images.cancel(p,id)
    @router.post('/projects/{p}/images/description')
    def description(p:str,body:dict):
        type=body.get('type');id=body.get('id');selected=body.get('fields',[])
        bible.check_target(p,type,id)
        if type=='character':
            from app.domain.characters import CharacterService
            card=CharacterService(registry).get(p,id)['canonical']
            available={'appearance':card['appearance'],'age':card['identity']['age_at_start'],'periods':card.get('periods',[])}
            # Only literal visual locks, never other Canon or author-only motives.
            available['visual_locks']=[r['statement'] for r in card['canon']['hard'] if r['path'].startswith('appearance.')]
        elif type=='entity':
            card=bible.get(p,id);available={k:card[k] for k in ['summary','details','periods']}
        else:available={}
        return {'fields':available,'prompt':'\n'.join(k+'：'+json.dumps(available[k],ensure_ascii=False) for k in selected if k in available)}

    @router.get('/projects/{p}/data')
    def stats(p:str):return data.stats(p)
    @router.get('/projects/{p}/data/search')
    def find(p:str,q:str):
        with write_guard(registry.engine):return search(data.root(p),q[:200],bible.relations(p))
    @router.post('/projects/{p}/data/reindex')
    def reindex(p:str):
        if hasattr(registry,'knowledge'):registry.knowledge.refresh(p,True)
        result=rebuild(data.root(p),bible.relations(p))
        return result
    @router.get('/projects/{p}/data/revisions')
    def history(p:str,path:str|None=None):return revisions(data.root(p),path)
    @router.post('/projects/{p}/data/checkpoint')
    def create_checkpoint(p:str,body:dict):
        root=data.root(p);relative=body.get('path','')
        if not relative.startswith(('chapters/','characters/','bible/','settings/','outlines/','.research/')):raise ConsoleError('不允许对此文件建立作者检查点',403)
        row=checkpoint(root,relative,'MANUAL',str(body.get('note',''))[:500])
        if not row:raise ConsoleError('文件不存在',404)
        return row
    @router.get('/projects/{p}/data/revisions/{id}')
    def historical(p:str,id:str):
        root=data.root(p);row,blob=revision_content(root,id);current=safe(root,row['path']);text=blob.decode('utf-8-sig');present=current.read_bytes() if current.exists() else b''
        return {**row,'content':text,'current_etag':digest(present) if current.exists() else '', 'diff':'\n'.join(difflib.unified_diff(present.decode('utf-8-sig').splitlines(),text.splitlines(),fromfile='当前',tofile='所选历史',lineterm=''))}
    @router.post('/projects/{p}/data/revisions/{id}/restore')
    def restore_history(p:str,id:str,body:dict):return data.restore_revision(p,id,body.get('etag',''))
    @router.post('/projects/{p}/data/backup')
    def backup(p:str,body:dict):return data.backup(p,body.get('images',True) is True,str(body.get('note','MANUAL'))[:200],body.get('private_history',True) is True)
    @router.get('/projects/{p}/data/backups/{id}')
    def download_backup(p:str,id:str):
        registry.get(p);row=next((r for r in data.catalog() if r['id']==id and r['project_id']==p),None)
        if not row:raise ConsoleError('备份不存在',404)
        path=Path(row['path'])
        if not path.is_file() or digest(path.read_bytes())!=row['sha256']:raise ConsoleError('备份缺失或校验失败',409)
        return FileResponse(path,filename=path.name)
    @router.get('/projects/{p}/data/export')
    def export(p:str,kind:str,format:str):
        blob,mime,name=data.export(p,kind,format);return Response(blob,media_type=mime,headers={'Content-Disposition':'attachment; filename="'+name+'"'})
    @router.post('/projects/{p}/data/import-text')
    def import_text(p:str,body:dict):
        text=body.get('content');n=body.get('chapter')
        if not isinstance(n,int) or not 1<=n<=99999 or not isinstance(text,str) or len(text.encode('utf8'))>2*1024*1024:raise ConsoleError('请选择章号及 UTF-8 正文（2 MiB 以内）',422)
        rel=f'chapters/chapter-{n}/manual-{uuid.uuid4().hex}.txt';write_bytes(safe(data.root(p),rel),text.encode('utf8'));return {'path':rel}
    @router.post('/projects/{p}/data/import-settings')
    def import_settings(p:str,body:dict):
        # Imported sources become independent draft entries; no replacing legacy Canon.
        text=body.get('content','')
        if not isinstance(text,str) or len(text)>2*1024*1024:raise ConsoleError('设定文件过大',413)
        from app.workspace.service import WorkspaceService
        value=WorkspaceService.parse_yaml(text)
        # Collection exports remain importable. Non-native settings are retained
        # as named research drafts rather than being mistaken for current Canon.
        if isinstance(value,dict) and any('/' in str(k) for k in value):
            rows=[]
            for name,v in value.items():
                if name in {'bible/categories.json','bible/relations.json'}:continue
                if isinstance(v,dict) and v.get('name') and v.get('category'):
                    rows.append(v)
                else:rows.append({'name':(v.get('name') if isinstance(v,dict) else None) or str(name),'category':'overview','summary':'导入资料，待作者整理：'+str(name),'details':v if isinstance(v,str) else yaml.safe_dump(v,allow_unicode=True,sort_keys=False)})
        else:rows=value if isinstance(value,list) else [value]
        if len(rows)>200:raise ConsoleError('单次最多导入 200 项设定',422)
        pending=[]
        from .bible import Entity
        for row in rows:
            if not isinstance(row,dict):raise ConsoleError('请导入单项实体或实体列表 YAML / JSON',422)
            if not row.get('category'):
                row={'name':row.get('name') or str(body.get('name','导入设定')),'category':'overview','summary':'外部设定资料，待作者整理','details':yaml.safe_dump(row,allow_unicode=True,sort_keys=False)}
            row={k:v for k,v in row.items() if k in Entity.model_fields};row.update(id='',status='DRAFT',canon_level='REFERENCE',locked_fields=[],source='RESEARCH',writer_view='',writer_public=False,writer_known_by=[],template_snapshot=None,template_version=0,parent_id='')
            pending.append(Entity.model_validate(row).model_dump())
        categories={c['id'] for c in bible.categories(p)}
        if any(r['category'] not in categories for r in pending):raise ConsoleError('请先导入缺少的分类模板',422)
        for row in pending:
            # Imported pointers cannot silently reference unrelated local IDs.
            category=next(c for c in bible.categories(p) if c['id']==row['category'])
            for f in category['fields']:
                if f['type'] in {'entity','image'} and row['fields'].get(f['id']):
                    row['details']+='\n导入时未建立关联：'+f['name']+' = '+str(row['fields'].pop(f['id']))
        return [bible.save(p,r) for r in pending]
    @router.get('/projects/{p}/data/trash')
    def trash_list(p:str):return data.trash_list(p)
    @router.post('/projects/{p}/data/trash')
    def trash(p:str,body:dict):
        relative=body.get('path','');stem=Path(relative).stem
        if relative.startswith(('characters/','bible/entities/')):
            refs=[r for r in bible.relations(p) if stem in {r['source_id'],r['target_id']}]
            if hasattr(registry,'knowledge'):
                kind='character' if relative.startswith('characters/') else 'entity'
                indexed=registry.knowledge.view(p,type=kind,id=stem)
                refs=indexed['relations']
            if refs:raise ConsoleError('仍有 '+str(len(refs))+' 项可追踪引用，请先在知识关联中心查看来源；未删除任何实体或正文',409)
        return data.trash(p,relative,body.get('confirm',''))
    @router.post('/projects/{p}/data/trash/{id}/{action}')
    def trash_action(p:str,id:str,action:str,body:dict):return data.trash_action(p,id,action,body.get('confirm',''))
    @router.post('/projects/{p}/data/cleanup')
    def cleanup(p:str,body:dict):return data.cleanup(p,body.get('execute') is True,body.get('confirm',''))
    return router,images,data
