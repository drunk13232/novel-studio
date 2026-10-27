import asyncio
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from app.errors import ConsoleError
from .references import References, AnalysisRequest, Metadata
from .document_parse import MAX_UPLOAD
from .storage import safe, read, write


def reference_routes(registry, config, data_center):
    library=References(registry,config);data_center.references=library
    router=APIRouter(prefix='/api/references')

    @router.get('/{scope}')
    def overview(scope:str,kind:str='reference'):
        if kind not in {'reference','style'}:raise ConsoleError('无效资料库',422)
        return library.summary(scope,kind)

    @router.post('/{scope}/upload',status_code=201)
    async def upload(scope:str,kind:str='reference',file:UploadFile=File(...)):
        blob=bytearray()
        try:
            while chunk:=await file.read(1024*1024):
                blob.extend(chunk)
                if len(blob)>MAX_UPLOAD:raise ConsoleError('文件超过 64 MiB',413)
            return await asyncio.to_thread(library.upload,scope,bytes(blob),file.filename or '未命名.txt',kind)
        finally:await file.close()

    @router.post('/{scope}/categories')
    def category(scope:str,body:dict):return library.category(scope,body)
    @router.get('/{scope}/search')
    def search(scope:str,q:str,kind:str='reference'):return library.search(scope,q,kind)
    @router.post('/{scope}/reindex')
    def reindex(scope:str):return library.reindex(scope)
    @router.get('/{scope}/documents/{id}')
    def document(scope:str,id:str):
        checked={}
        return {**library.get(scope,'documents',id),**library.extracted(scope,id),'notes':[{**n,'evidence_status':library.citation_status(scope,n,checked)} for n in library.rows(scope,'notes') if n['document_id']==id]}
    @router.get('/{scope}/documents/{id}/file')
    def original(scope:str,id:str,download:bool=False):
        row=library.get(scope,'documents',id)
        mime={'pdf':'application/pdf','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','epub':'application/epub+zip'}.get(row['format'],'text/plain; charset=utf-8')
        return FileResponse(safe(library.root(scope),row['original']),media_type=mime,filename=row['filename'] if download else None,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
    @router.patch('/{scope}/documents/{id}')
    def edit(scope:str,id:str,body:dict):return library.update(scope,id,body)
    @router.post('/{scope}/documents/{id}/retry')
    def retry(scope:str,id:str):library.parse(scope,id);return {'queued':True}
    @router.post('/{scope}/documents/{id}/notes')
    def note(scope:str,id:str,body:dict):return library.note(scope,id,body)
    @router.get('/{scope}/sources/{source}/documents/{id}/notes')
    def source_notes(scope:str,source:str,id:str):
        library.source_document(scope,source,id)
        checked={}
        return [{**n,'evidence_status':library.citation_status(scope,n,checked)} for n in library.rows(scope,'notes') if n['document_id']==id and n['source_scope']==source]
    @router.patch('/{scope}/notes/{id}')
    def edit_note(scope:str,id:str,body:dict):
        row=library.get(scope,'notes',id)
        for k in ['text','tags']:
            if k in body:row[k]=body[k]
        if 'links' in body:
            links=body['links']
            if scope=='public' and links:raise ConsoleError('请先把公共资料启用到小说，再在小说中关联',409)
            from .bible import Bible
            for link in links: Bible(registry).check_target(scope,link['type'],link['id'])
            row['links']=links
        if body.get('adopt_analysis'):
            analysis=library.get(scope,'analyses',body['adopt_analysis'])
            if analysis['mode']!='adopt' or row['document_id'] not in analysis['document_ids']:raise ConsoleError('采用建议来源不匹配',409)
            from .storage import now
            row['adoption']={'text':str(body.get('adoption_text',''))[:10000],'status':'USER_CONFIRMED','at':now(),'analysis_id':analysis['id'],'canon':False}
        return library.put(scope,'notes',row,body.get('etag'))
    @router.get('/{scope}/notes/{id}')
    def get_note(scope:str,id:str):return library.get(scope,'notes',id)
    @router.get('/{scope}/notes/{id}/evidence')
    def evidence(scope:str,id:str):return library.citation_status(scope,library.get(scope,'notes',id))
    @router.post('/{scope}/profiles')
    def profile(scope:str,body:dict):return library.profile(scope,body)
    @router.get('/{scope}/profiles/{id}')
    def get_profile(scope:str,id:str):return library.get(scope,'profiles',id)
    @router.post('/{scope}/bindings')
    def bindings(scope:str,body:dict):return library.bind(scope,body)
    @router.get('/{scope}/enabled')
    def enabled(scope:str):
        bindings=library.bindings(scope);result={k:[] for k in bindings}
        for kind,rows in bindings.items():
            for item in rows:
                try:
                    row=library.get(item['source_scope'],kind,item['id'])
                    if not row.get('trashed'):result[kind].append({**row,**item,**item.get('profile_snapshot',{})})
                except ConsoleError:pass
        return result
    @router.post('/{scope}/analyses',status_code=202)
    async def analyze(scope:str,body:AnalysisRequest):return library.start(scope,body).public()
    @router.get('/{scope}/tasks/{id}')
    def task(scope:str,id:str):
        library.root(scope)
        if scope not in library.managers:raise ConsoleError('任务不属于此作用范围',404)
        return library.managers[scope].get(id).public()
    @router.post('/{scope}/tasks/{id}/cancel')
    async def cancel(scope:str,id:str):
        if scope not in library.managers:raise ConsoleError('任务不属于此作用范围',404)
        return (await library.managers[scope].cancel(id)).public()
    @router.post('/{scope}/backup')
    def backup(scope:str):return data_center.reference_backup(scope)
    @router.get('/{scope}/backups/{id}')
    def download(scope:str,id:str):
        row=next((r for r in data_center.catalog() if r['id']==id and r.get('reference_scope')==scope),None)
        if not row:raise ConsoleError('备份不属于此资料库',404)
        return FileResponse(row['path'],filename='reference-library.zip')
    @router.post('/{scope}/restore')
    async def restore(scope:str,file:UploadFile=File(...)):
        blob=await file.read(256*1024*1024+1)
        if len(blob)>256*1024*1024:raise ConsoleError('资料备份超过 256 MiB',413)
        await file.close()
        return await asyncio.to_thread(data_center.reference_restore,scope,blob)
    return router,library
