"""Consistent project snapshots, validated restores, versions and trash."""
import copy
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import threading
import uuid
import zipfile
from datetime import datetime,timezone
from pathlib import Path
import yaml
from app.errors import ConsoleError
from .storage import safe,read,write,write_bytes,uid,now,digest,files,revisions,revision_content,checkpoint,write_guard,rebuild
from app.studio import APP_STATE_FILES,application_backup,validate_application,restore_application

TOPS={'bible','chapters','characters','metadata','outlines','reviews','settings','state','.research','assets','art','history','trash','storage','covers','project.yaml','AGENTS.md','.gitignore','docs'}
IMAGE_DIRS=('assets/original/','assets/generated/','assets/thumbnails/')
MAX_ARCHIVE=1024*1024*1024
MAX_EXPANDED=4*1024*1024*1024

def remap_restored_records(root,old_id,new_id):
    """Re-scope control records, retaining their original bytes as provenance.

    Story text, Canon and State never undergo string replacements. Completed
    proposal journals still need a matching scoped proposal on the next launch.
    """
    mapped=[]
    for rel,p in list(files(root)):
        if rel.startswith(('.research/library/documents/','.research/library/profiles/','.research/library/notes/','.research/library/bindings.json')) and p.suffix=='.json':
            blob=p.read_bytes();value=json.loads(blob)
            def remap_reference(node):
                if isinstance(node,dict):
                    for key,item in node.items():
                        if key in {'scope','source_scope'} and item==old_id:node[key]=new_id
                        elif isinstance(item,(list,dict)):remap_reference(item)
                elif isinstance(node,list):
                    for item in node:remap_reference(item)
            remap_reference(value)
            if value!=json.loads(blob):
                write_bytes(safe(root,'metadata/restore-source-records/'+old_id+'/'+rel),blob)
                write(p,value);mapped.append(rel)
            continue
        if rel=='metadata/studio/reading.json':
            blob=p.read_bytes();value=json.loads(blob)
            for key in ('notes','todos','revision_tasks'):
                for item in value.get(key,[]):
                    if item.get('project')==old_id:item['project']=new_id
            if value!=json.loads(blob):
                write_bytes(safe(root,'metadata/restore-source-records/'+old_id+'/'+rel),blob)
                write(p,value);mapped.append(rel)
            continue
        if not rel.startswith(('metadata/domain-proposals/','metadata/proposals/','metadata/studio/candidates/','metadata/world-logic/','metadata/studio/writing/','metadata/studio/director/','metadata/studio/workflows/','metadata/roleplay/','reviews/literary/','art/jobs/')) or p.suffix not in {'.yaml','.json'}:continue
        blob=p.read_bytes();v=json.loads(blob) if p.suffix=='.json' else yaml.safe_load(blob)
        if not isinstance(v,dict):continue
        changed=False
        if v.get('project_id')==old_id:v['project_id']=new_id;changed=True
        if rel.startswith('metadata/roleplay/') and v.get('pending_task'):
            v.update(pending_task=None,last_task_status='INTERRUPTED');changed=True
        if rel.startswith('metadata/studio/director/'):
            if v.get('active_task') or v.get('status') in {'PLANNING','GENERATING','REVIEWING','CANCELLING','QUEUED','RUNNING'}:
                v.update(status='INTERRUPTED',active_task=None,pause_requested=True,phase='恢复的历史任务；不会自动重新请求 AI');changed=True
            if v.get('auto_continue'):
                v['auto_continue']=False;changed=True
        if rel.startswith('metadata/studio/workflows/runs/'):
            if v.get('active_task') or v.get('status')=='RUNNING':
                steps=v.get('snapshot',{}).get('steps',[]);index=v.get('index',0)
                if 0<=index<len(steps):
                    entry=v.get('steps',{}).get(steps[index]['id'])
                    if entry and entry.get('status')=='RUNNING':entry.update(status='INTERRUPTED',finished_at=now())
                v.update(status='PAUSED',active_task=None,active_operation=None,epoch=v.get('epoch',0)+1,last_error='从备份恢复的流程不会自动执行；请重新检查上下文后继续 / Restored workflow requires author review');changed=True
            if v.get('auto_continue'):
                v['auto_continue']=False;changed=True
        if rel.startswith('metadata/studio/candidates/') and v.get('status')=='RUNNING':
            v.update(status='INTERRUPTED',error='恢复的候选任务不会自动重新调用 AI',finished_at=now());changed=True
        if rel.startswith('art/jobs/') and v.get('status') in {'QUEUED','RUNNING'}:
            v.update(status='INTERRUPTED',error='从备份恢复的任务不自动重新提交，请检查历史后手动重试',finished_at=now());changed=True
        if changed:
            write_bytes(safe(root,'metadata/restore-source-records/'+old_id+'/'+rel),blob)
            write_bytes(p,(json.dumps(v,ensure_ascii=False,indent=2) if p.suffix=='.json' else yaml.safe_dump(v,allow_unicode=True,sort_keys=False)).encode('utf8'))
            mapped.append(rel)
    return mapped

def private_record(rel):
    return (rel.startswith(('metadata/roleplay/nodes/','metadata/studio/director/','metadata/restored-task-history/','metadata/restore-source-records/')) or bool(re.fullmatch(r'metadata/roleplay/session_[0-9a-f]{32}\.json',rel)))

def backup_member(name):
    if name.split('/')[0] not in TOPS or any(x in {'.env','auth.json','credentials.json','.codex','.agents','.git','node_modules','__pycache__'} for x in name.split('/')):return False
    return not name.startswith('.research/library/storage/') and not name.endswith(('.sqlite-wal','.sqlite-shm')) and '.pending-' not in name and '.web-save-' not in name

class DataCenter:
    def reference_backup(self,scope):
        library=self.references;root=library.root(scope)
        with library.lock:
            if any(s==scope for s,_ in library.pending):raise ConsoleError('资料仍在解析，请完成后备份',409)
            entries=[('library/'+rel,f) for rel,f in files(root) if not rel.startswith('storage/') and '.pending' not in rel]
            if scope!='public':
                shared=set();bindings=library.bindings(scope)
                for kind in ['documents','profiles']:
                    for binding in bindings[kind]:
                        if binding['source_scope']!='public':continue
                        row=library.get('public',kind,binding['id']);shared.add(kind+'/'+row['id']+'.json')
                        docs=[row] if kind=='documents' else [library.get('public','documents',s['document_id']) for s in row['sources']]
                        for doc in docs:
                            shared.update(['documents/'+doc['id']+'.json',doc['original'],'extracted/'+doc['id']+'.json'])
                for note in library.rows(scope,'notes'):
                    if note.get('source_scope')=='public':
                        doc=library.get('public','documents',note['document_id'])
                        shared.update(['documents/'+doc['id']+'.json',doc['original'],'extracted/'+doc['id']+'.json'])
                entries += [('public/'+rel,safe(library.root('public'),rel)) for rel in shared if safe(library.root('public'),rel).is_file()]
            directory=Path(self.config()['directory']).resolve();directory.mkdir(parents=True,exist_ok=True)
            id=uid('backup');target=directory/(id+'-reference.zip')
            manifest={'backup_version':2,'kind':'reference_library','reference_scope':scope,'id':id,'created_at':now(),'files':[]}
            temp=target.with_suffix('.pending')
            app_state=application_backup(self.settings_path.parent,scope)
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
                for name,f in entries:
                    blob=f.read_bytes();z.writestr(name,blob);manifest['files'].append({'path':name,'size':len(blob),'sha256':digest(blob)})
                for name,blob in app_state.items():
                    z.writestr(name,blob);manifest['files'].append({'path':name,'size':len(blob),'sha256':digest(blob)})
                z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False))
            if application_backup(self.settings_path.parent,scope)!=app_state:
                temp.unlink(missing_ok=True);raise ConsoleError('备份期间阅读或偏好已更新，请重试',409)
            with zipfile.ZipFile(temp) as z:
                for entry in manifest['files']:
                    if digest(z.read(entry['path']))!=entry['sha256']:raise ConsoleError('资料备份验证失败',409)
            os.replace(temp,target)
            record={'id':id,'project_id':scope,'reference_scope':scope,'kind':'reference_library','path':str(target),'title':'资料与文风库','created_at':manifest['created_at'],'sha256':digest(target.read_bytes()),'status':'VERIFIED','file_count':len(manifest['files']),'includes_images':False}
            write(self.catalog_path(),[record,*self.catalog()]);return record

    def reference_restore(self,scope,blob):
        library=self.references;library.root(scope)
        with library.lock:
            if any(s in {scope,'public'} for s,_ in library.pending):raise ConsoleError('请等待解析结束再恢复',409)
            try:
                with zipfile.ZipFile(io.BytesIO(blob)) as z:
                    infos=z.infolist();names=[i.filename for i in infos]
                    if len(infos)>20000 or len(names)!=len(set(names)) or sum(i.file_size for i in infos)>512*1024*1024:raise ConsoleError('备份资源规模不安全',413)
                    manifest=json.loads(z.read('manifest.json'))
                    if manifest.get('kind')!='reference_library' or manifest.get('backup_version')!=2 or set(names)!={'manifest.json',*[r['path'] for r in manifest['files']]}:raise ConsoleError('不是完整的资料库备份',422)
                    pending=[];app_state={}
                    for info in infos:
                        if info.flag_bits&1 or stat.S_ISLNK(info.external_attr>>16) or info.file_size>64*1024*1024:raise ConsoleError('备份含不安全文件',422)
                    for record in manifest['files']:
                        name=record['path'];prefix,relative=name.split('/',1)
                        if prefix=='application':
                            data=z.read(name)
                            if len(data)!=record['size'] or digest(data)!=record['sha256']:raise ConsoleError('备份哈希错误',422)
                            validate_application(name,data,manifest['reference_scope']);app_state[name]=data;continue
                        if prefix not in {'library','public'} or relative.split('/')[0] not in {'documents','originals','extracted','notes','profiles','analyses','history','categories.json','bindings.json'}:raise ConsoleError('备份含未经允许的路径',403)
                        target=safe(library.root('public' if prefix=='public' else scope),relative);data=z.read(name)
                        if len(data)!=record['size'] or digest(data)!=record['sha256']:raise ConsoleError('备份哈希错误',422)
                        if prefix=='public' and target.exists() and target.read_bytes()!=data:raise ConsoleError('公共资料已有不同版本，请先在公共库处理冲突',409)
                        if relative.startswith('originals/') and target.exists() and target.read_bytes()!=data:raise ConsoleError('原始文件哈希冲突',409)
                        if relative.startswith('documents/'):
                            row=json.loads(data);safe(library.root(scope),row['original'])
                            if not row['original'].startswith('originals/'+row['sha256']+'.'):raise ConsoleError('原文件引用不合法',422)
                            if prefix=='library':row['scope']=scope;data=json.dumps(row,ensure_ascii=False,indent=2).encode('utf8')
                        if prefix=='library' and relative.endswith('.json') and relative.startswith(('notes/','profiles/','bindings.json')):
                            row=json.loads(data);old_scope=manifest.get('reference_scope')
                            def remap(value):
                                if isinstance(value,dict):
                                    for key,item in value.items():
                                        if key in {'scope','source_scope'} and item==old_scope:value[key]=scope
                                        elif isinstance(item,(dict,list)):remap(item)
                                elif isinstance(value,list):
                                    for item in value:remap(item)
                            remap(row);data=json.dumps(row,ensure_ascii=False,indent=2).encode('utf8')
                            if relative=='bindings.json':
                                if not isinstance(row,dict) or set(row)!={'documents','profiles'}:raise ConsoleError('备份引用结构无效',422)
                                for kind,items in row.items():
                                    if not isinstance(items,list):raise ConsoleError('备份引用列表无效',422)
                                    for item in items:
                                        if not isinstance(item,dict) or item.get('source_scope') not in {scope,'public'}:raise ConsoleError('备份不能引用其他小说私人库',403)
                                        if item.get('role') not in {'main','auxiliary','analysis'} or not re.fullmatch(('document' if kind=='documents' else 'profile')+r'_[0-9a-f]{32}',str(item.get('id',''))):raise ConsoleError('备份引用无效',422)
                        pending.append((prefix,relative,target,data))
                    for prefix,relative,target,data in pending:
                        if target.exists() and target.read_bytes()!=data and target.suffix=='.json':checkpoint(library.root('public' if prefix=='public' else scope),relative,'PRE_RESTORE','恢复资料备份前保留')
                        write_bytes(target,data)
            except (ValueError,KeyError,zipfile.BadZipFile) as error:raise ConsoleError('资料备份损坏或字段缺失',422) from error
            library.reindex(scope)
            if any(p=='public' for p,_,_,_ in pending):library.reindex('public')
            restored=restore_application(self.settings_path.parent,app_state,manifest['reference_scope'],scope)
            return {'restored':True,'files':len(pending),'scope':scope,'references_preserved':True,'application_state':restored}

    def __init__(self,registry,settings_path):
        self.registry=registry;self.settings_path=settings_path;self.stop=threading.Event();self.thread=None;self.lease=None
    def root(self,p):return self.registry.workspace(p).root
    def config(self):return read(self.settings_path,{'directory':str(self.registry.engine.parent/'NovelStudio Backups'),'schedule':'OFF','on_exit':False,'retain_backups':20,'revision_retention':'ALL'})
    def configure(self,value):
        if value.get('schedule') not in {'OFF','DAILY','WEEKLY'} or not isinstance(value.get('on_exit'),bool):raise ConsoleError('备份设置无效',422)
        p=Path(value.get('directory','')).expanduser()
        if not p.is_absolute() or p.resolve().is_relative_to(self.registry.root):raise ConsoleError('备份目录必须是小说项目之外的绝对路径',422)
        if any(q.is_symlink() or q.is_junction() for q in [p,*p.parents]):raise ConsoleError('备份目录不能通过链接跳转',403)
        for forbidden in [self.registry.engine/'release',self.registry.engine/'desktop',self.registry.engine/'web/frontend',self.registry.engine/'web/backend',Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))]:
            if p.resolve().is_relative_to(forbidden.resolve()):raise ConsoleError('备份不能写入应用资源、依赖或凭证目录',403)
        retention=value.get('revision_retention','ALL')
        if retention not in {'ALL','DEDUP_PREVIEW'}:raise ConsoleError('无效历史保留策略',422)
        row={**self.config(),**{k:value[k] for k in ['directory','schedule','on_exit']},'retain_backups':max(1,min(500,int(value.get('retain_backups',20)))),'revision_retention':retention}
        write(self.settings_path,row);return row
    def catalog_path(self):return self.settings_path.with_name('backup-catalog.json')
    def catalog(self):return read(self.catalog_path(),[])
    def stats(self,p):
        root=self.root(p);counts={k:0 for k in ['body','settings','original_images','thumbnails','history','temporary','other']};total=0;image_count=0;han=0
        for rel,path in files(root):
            size=path.stat().st_size;total+=1
            key='body' if rel.startswith('chapters/') else 'settings' if rel.startswith(('characters/','bible/','settings/')) else 'original_images' if rel.startswith(IMAGE_DIRS[:2]) else 'thumbnails' if rel.startswith(IMAGE_DIRS[2]) else 'history' if rel.startswith('history/') else 'temporary' if rel.startswith('art/tmp/') else 'other'
            counts[key]+=size
            if key=='original_images':image_count+=1
        # One chosen text per chapter, not draft+final+revision totals.
        for folder in safe(root,'chapters').glob('chapter-*'):
            if not folder.is_dir():continue
            candidates=sorted(folder.glob('manual-*.txt'),key=lambda f:f.stat().st_mtime,reverse=True)
            chosen=next(iter(candidates),None) or next((f for f in [folder/'final.txt',folder/'final.md',folder/'draft.txt',folder/'draft.md'] if f.exists()),None)
            if chosen:
                text=safe(root,chosen.relative_to(root).as_posix()).read_text(encoding='utf-8-sig')
                from app.studio import body_counts
                han+=body_counts(text)['han']
        backups=[r for r in self.catalog() if r['project_id']==p]
        return {'project_path':str(root),'file_count':total,'sizes':counts,'bytes':sum(counts.values()),'han':han,'images':image_count,'revisions':len(revisions(root)),'backups':backups,'backup_bytes':sum(Path(r['path']).stat().st_size for r in backups if Path(r['path']).is_file()),'config':self.config()}
    def _task_files(self,p):
        root=self.root(p)
        for task in (self.registry.engine/'web/runtime/tasks').glob('*/task.json'):
            safe(self.registry.engine,task.relative_to(self.registry.engine).as_posix())
            row=read(task,{})
            if str(row.get('workspace','')).casefold()!=str(root).casefold():continue
            for rel,f in files(task.parent):
                if f.suffix in {'.json','.jsonl','.txt','.md'}:yield 'local-tasks/'+task.parent.name+'/'+rel,f
    def backup(self,p,images=True,note='MANUAL',private_history=True):
        from app.tasks.lease import acquire,release
        ai=acquire(self.registry.engine)
        directory=Path(self.config()['directory']).resolve();root=self.root(p)
        if directory.is_relative_to(self.registry.root):release(ai);raise ConsoleError('备份目录不能位于项目中',403)
        directory.mkdir(parents=True,exist_ok=True)
        id=uid('backup');target=directory/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+p[-8:]+'-'+id[-8:]+'.zip');temp=target.with_suffix('.pending')
        dbtemp=directory/(id+'.sqlite');manifest={'backup_version':1,'schema_version':'1.2','project_id':p,'title':self.registry.get(p)['title'],'created_at':now(),'id':id,'includes_images':images,'note':note,'includes_private_history':private_history,'files':[]}
        baseline={}
        excluded_history={str(row['id']) for row in revisions(root) if private_record(row.get('path',''))} if not private_history else set()
        def selected(rel):return not any(rel.startswith('history/revisions/'+id+'/') for id in excluded_history)
        try:
            app_state=application_backup(self.settings_path.parent,p,private_history)
            with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as archive:
                entries=[('project/'+rel,f) for rel,f in files(root) if backup_member(rel) and (images or not rel.startswith(IMAGE_DIRS)) and (private_history or not private_record(rel)) and selected(rel)]
                entries+=list(self._task_files(p)) if private_history else []
                for name,f in entries:
                    before=f.stat();data=f.read_bytes()
                    if name=='project/storage/index.sqlite':
                        # SQLite Online Backup API creates a transactionally consistent copy including WAL.
                        source=sqlite3.connect(f.as_uri()+'?mode=ro',uri=True);dest=sqlite3.connect(dbtemp)
                        try:source.backup(dest)
                        finally:source.close();dest.close()
                        data=dbtemp.read_bytes()
                    baseline[str(f)]=(before.st_mtime_ns,before.st_size,digest(f.read_bytes()) if name=='project/storage/index.sqlite' else digest(data))
                    archive.writestr(name,data);manifest['files'].append({'path':name,'size':len(data),'sha256':digest(data)})
                for name,data in app_state.items():
                    archive.writestr(name,data);manifest['files'].append({'path':name,'size':len(data),'sha256':digest(data)})
                archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
            if application_backup(self.settings_path.parent,p,private_history)!=app_state:raise ConsoleError('备份期间阅读或偏好已更新，请重试',409)
            # Detect external editors bypassing the app's OS-held mutation boundary.
            for name,(mtime,size,hash) in baseline.items():
                f=Path(name)
                if not f.exists() or (f.stat().st_mtime_ns,f.stat().st_size)!=(mtime,size) or digest(f.read_bytes())!=hash:raise ConsoleError('备份期间文件被外部程序修改，请重试',409)
            current={str(f) for rel,f in files(root) if backup_member(rel) and (images or not rel.startswith(IMAGE_DIRS)) and (private_history or not private_record(rel)) and selected(rel)}|({str(f) for _,f in self._task_files(p)} if private_history else set())
            if current!=set(baseline):raise ConsoleError('备份期间文件列表发生变化，请重试',409)
            os.replace(temp,target)
            row={k:manifest[k] for k in ['id','project_id','title','created_at','includes_images','note']};row.update(path=str(target),sha256=digest(target.read_bytes()),status='VERIFIED',file_count=len(manifest['files']))
            self.inspect(target) # Verify actual ZIP, not a claimed success.
            write(self.catalog_path(),[row,*self.catalog()]);return row
        finally:temp.unlink(missing_ok=True);dbtemp.unlink(missing_ok=True);release(ai)
    def inspect(self,path):
        if path.stat().st_size>MAX_ARCHIVE:raise ConsoleError('备份超过本版 1 GiB 导入限制',413)
        try:
            with zipfile.ZipFile(path) as z:
                infos=z.infolist();names=[i.filename for i in infos]
                if len(infos)>50000 or sum(i.file_size for i in infos)>MAX_EXPANDED or len(names)!=len(set(names)):raise ConsoleError('备份规模过大或含重复成员',422)
                for i in infos:
                    safe(Path('C:/novel-backup-validation'),i.filename)
                    if i.is_dir() or stat.S_ISLNK(i.external_attr>>16) or i.flag_bits&1:raise ConsoleError('不接受链接、目录成员或加密备份',422)
                    if i.file_size>256*1024*1024:raise ConsoleError('备份单文件超过 256 MiB',413)
                m=json.loads(z.read('manifest.json'))
                if not isinstance(m,dict) or m.get('backup_version')!=1 or not re.fullmatch(r'novel_[0-9a-f]{32}',m.get('project_id','')):raise ConsoleError('备份格式不支持',422)
                if not isinstance(m.get('files'),list) or any(not isinstance(x,dict) or not {'path','size','sha256'}<=x.keys() for x in m['files']):raise ConsoleError('备份文件清单无效',422)
                if set(names)!={'manifest.json',*[r['path'] for r in m['files']]}:raise ConsoleError('备份文件清单不匹配',422)
                for r in m['files']:
                    name=r['path']
                    if name.startswith('project/'):
                        if not backup_member(name[8:]):raise ConsoleError('备份包含不允许的项目路径',422)
                    elif name not in APP_STATE_FILES and not re.fullmatch(r'local-tasks/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+',name):raise ConsoleError('备份包含未授权内容',422)
                    data=z.read(name)
                    if len(data)!=r['size'] or digest(data)!=r['sha256']:raise ConsoleError('备份哈希不匹配：'+name,422)
                    if name in APP_STATE_FILES:validate_application(name,data,m['project_id'])
                    if name.startswith('project/metadata/transactions/') and name.endswith(('.yaml','.yml')) and yaml.safe_load(data).get('status')=='PENDING':
                        raise ConsoleError('备份包含未完成的设定事务，请先在原工作区恢复该事务',409)
                project=yaml.safe_load(z.read('project/project.yaml'))
                if project.get('id')!=m['project_id'] or not project.get('title'):raise ConsoleError('备份项目清单无效',422)
                return {**m,'verified':True,'warning':None if m['includes_images'] else '轻量备份不含原图和缩略图，恢复后素材可能缺失。'}
        except (zipfile.BadZipFile,KeyError,ValueError,TypeError,yaml.YAMLError) as e:raise ConsoleError('备份损坏或格式不完整',422) from e
    def stage(self,data):
        if len(data)>MAX_ARCHIVE:raise ConsoleError('备份超过 1 GiB',413)
        token=uid('import');path=self.registry.engine/'web/.runtime/backup-imports'/(token+'.zip')
        write_bytes(path,data)
        try:m=self.inspect(path)
        except Exception:path.unlink(missing_ok=True);raise
        return {'token':token,'manifest':m,'sha256':digest(data)}
    def staged(self,token):
        if not re.fullmatch(r'import_[0-9a-f]{32}',token):raise ConsoleError('无效导入凭证',403)
        p=self.registry.engine/'web/.runtime/backup-imports'/(token+'.zip')
        if not p.exists():raise ConsoleError('待恢复备份不存在，请重新导入',404)
        return p
    def restore(self,token,mode='new',target=None,confirm='',chapter=None,expected_hash=None,personal=False):
        path=self.staged(token)
        if digest(path.read_bytes())!=expected_hash:raise ConsoleError('备份与已查看的校验信息不一致，请重新验证',409)
        m=self.inspect(path)
        if mode=='history':
            if not target or not isinstance(chapter,int) or not 1<=chapter<=99999:raise ConsoleError('请选择目标小说与章号',422)
            root=self.root(target);count=0
            with zipfile.ZipFile(path) as z:
                for r in m['files']:
                    prefix=f'project/chapters/chapter-{chapter}/'
                    if r['path'].startswith(prefix) and r['path'].endswith(('.md','.txt')):
                        relative=r['path'][8:];data=z.read(r['path']);id=uid('revision');base=safe(root,'history/revisions/'+id);suffix=Path(relative).suffix
                        write_bytes(base/('content'+suffix),data);write(base/'revision.json',{'id':id,'path':relative,'created_at':now(),'source':'BACKUP_IMPORT','note':'从备份导入为历史，未覆盖正文','sha256':digest(data),'size':len(data),'blob':id+'/content'+suffix});count+=1
            return {'imported_versions':count,'project_id':target}
        if mode not in {'new','overwrite'}:raise ConsoleError('无效恢复模式',422)
        if mode=='overwrite':
            if target!=m['project_id'] or confirm!='覆盖 '+target:raise ConsoleError('覆盖需同一项目且明确输入“覆盖 项目ID”',409)
            self.backup(target,True,'PRE_RESTORE')
        id=target if mode=='overwrite' else uid('novel')
        staging=self.registry.engine/'web/.runtime/restore'/uid('restore');staging.mkdir(parents=True)
        destination=self.registry.root/id;old=staging.with_name(staging.name+'-previous')
        try:
            app_state={}
            with zipfile.ZipFile(path) as z:
                for r in m['files']:
                    name=r['path']
                    if name in APP_STATE_FILES:app_state[name]=z.read(name);continue
                    # Index is derived. Codex thread maps cannot be resumed in a new project.
                    if name.startswith('project/storage/'):continue
                    relative=name[8:] if name.startswith('project/') else 'metadata/restored-task-history/'+name[12:]
                    write_bytes(safe(staging,relative),z.read(name))
            manifest=yaml.safe_load((staging/'project.yaml').read_text(encoding='utf-8-sig'))
            if mode=='new':
                manifest['id']=id;manifest['title']+='（恢复副本）';manifest['status']['updated_at']=now()
                manifest['codex']={k:v for k,v in manifest.get('codex',{}).items() if 'thread' not in k.lower() and 'session' not in k.lower()}
                write_bytes(staging/'project.yaml',yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False).encode('utf8'))
            rebuild(staging) # Validate the derived SQLite index before publishing a new project.
            mapped=remap_restored_records(staging,m['project_id'],id)
            write(staging/'metadata/restore-receipt.json',{'source_project':m['project_id'],'project_id':id,'id_map':{m['project_id']:id},'remapped_control_records':mapped,'restored_at':now(),'backup_id':m['id'],'tasks':'historical only; no resumable threads','includes_images':m['includes_images']})
            if destination.exists():
                if mode!='overwrite':raise ConsoleError('目标项目已存在',409)
                os.replace(destination,old)
            os.replace(staging,destination)
            if mode=='overwrite':
                # Engine-owned SDK thread mappings are execution state, never story plot threads.
                (self.registry.engine/'web/.runtime/threads'/(id+'.json')).unlink(missing_ok=True)
            self.registry.workspaces.pop(id,None);self.registry.scan()
            if id not in self.registry.rows:raise ConsoleError('恢复后项目清单校验失败',422)
            restored=restore_application(self.settings_path.parent,app_state,m['project_id'],id,personal)
            return {'project_id':id,'title':manifest['title'],'id_map':{m['project_id']:id},'warning':m['warning'],'application_state':restored}
        except Exception:
            if old.exists():
                if destination.exists():
                    failed=staging.with_name(staging.name+'-failed');os.replace(destination,failed)
                os.replace(old,destination)
            elif mode=='new' and destination.exists():
                # Never leave an apparently usable half-restored project on failure.
                os.replace(destination,staging.with_name(staging.name+'-failed'))
            self.registry.workspaces.pop(id,None);self.registry.scan()
            raise
        finally:
            if staging.exists() and staging.resolve().is_relative_to((self.registry.engine/'web/.runtime/restore').resolve()):shutil.rmtree(staging)
            # Pre-restore ZIP is verified; previous tree retained until explicit cleanup.
    def restore_revision(self,p,id,etag):
        root=self.root(p);row,data=revision_content(root,id);relative=row['path'];ws=self.registry.workspace(p)
        if not relative.startswith(('chapters/','characters/','bible/','settings/','outlines/','.research/')):raise ConsoleError('此历史不能恢复到可编辑文件',403)
        target=safe(root,relative)
        current=digest(target.read_bytes()) if target.exists() else ''
        if current!=etag:raise ConsoleError('当前版本已变化，请刷新后恢复',409)
        if ws.protected_body(relative):
            relative=str(Path(relative).parent).replace('\\','/')+'/manual-'+uuid.uuid4().hex+'.txt';target=safe(root,relative)
        elif relative.startswith('characters/'):
            from app.domain.characters import validate_card,normalize
            validate_card(normalize(yaml.safe_load(data)),target.stem,normalize(yaml.safe_load(target.read_bytes())) if target.exists() else None)
        elif relative.startswith('bible/entities/'):
            old=read(target,{})
            if old.get('status')=='LOCKED' or old.get('locked_fields'):raise ConsoleError('锁定设定的历史请先作为候选对照并明确解锁',409)
            restored=json.loads(data);restored.update(version=old.get('version',0)+1,updated_at=now());data=json.dumps(restored,ensure_ascii=False,indent=2).encode('utf8')
        checkpoint(root,relative,'PRE_RESTORE','恢复前保留')
        before=target.read_text('utf-8-sig') if relative.startswith('chapters/') and target.exists() else ''
        write_bytes(target,data)
        if relative.startswith('chapters/'):
            from app.writing_metrics import notify_saved
            notify_saved(root,relative,before,data.decode('utf-8-sig'),'RESTORE')
        checkpoint(root,relative,'RESTORED','来自历史 '+id)
        return {'path':relative,'etag':digest(data),'restored_from':id}
    def trash(self,p,relative,confirm=''):
        root=self.root(p);path=safe(root,relative);ws=self.registry.workspace(p)
        if not path.is_file() or not relative.startswith(('characters/','bible/entities/','assets/metadata/','chapters/','.research/')):raise ConsoleError('只能回收人物、实体、素材、正文或研究文件',403)
        if ws.protected_body(relative):raise ConsoleError('正式稿和已提交章节保留；仅独立修订稿可移入回收站',409)
        if relative.startswith('characters/'):
            ledger=ws.yaml_file('state/chapter-ledger.yaml')
            if any(path.stem in json.dumps(r,ensure_ascii=False) for r in ledger.get('entries',[])):raise ConsoleError('已提交剧情引用此人物，不能删除 Canon',409)
        if relative.startswith('bible/entities/') and read(path,{}).get('status')=='LOCKED':raise ConsoleError('请先明确解锁设定',409)
        if confirm!=relative:raise ConsoleError('回收前必须明确确认目标路径',409)
        paths=[relative]
        if relative.startswith('assets/metadata/'):
            row=read(path);paths += [r for r in [row['file'],row['thumbnail']] if safe(root,r).exists()]
        id=uid('trash');entry={'id':id,'deleted_at':now(),'path':relative,'files':[]}
        for rel in paths:
            original=safe(root,rel);data=original.read_bytes();dest=safe(root,'trash/'+id+'/files/'+rel)
            write_bytes(dest,data);entry['files'].append({'path':rel,'sha256':digest(data)})
        write(safe(root,'trash/'+id+'/entry.json'),entry)
        for rel in paths:safe(root,rel).unlink()
        return entry
    def trash_list(self,p):return [read(safe(self.root(p),x.relative_to(self.root(p)).as_posix())) for x in safe(self.root(p),'trash').glob('trash_*/entry.json')]
    def trash_action(self,p,id,action,confirm=''):
        if not re.fullmatch(r'trash_[0-9a-f]{32}',id):raise ConsoleError('无效回收记录',403)
        root=self.root(p);folder=safe(root,'trash/'+id);row=read(folder/'entry.json')
        if not row:raise ConsoleError('回收记录不存在',404)
        if action=='restore':
            for f in row['files']:
                if safe(root,f['path']).exists():raise ConsoleError('同路径已有文件，请先处理冲突',409)
                data=safe(root,'trash/'+id+'/files/'+f['path']).read_bytes()
                if digest(data)!=f['sha256']:raise ConsoleError('回收内容校验失败',409)
            for f in row['files']:write_bytes(safe(root,f['path']),safe(root,'trash/'+id+'/files/'+f['path']).read_bytes())
        elif action=='delete':
            if confirm!='永久删除 '+id:raise ConsoleError('永久删除需要输入完整确认短语',409)
        else:raise ConsoleError('无效回收站操作',422)
        if folder.resolve().parent!=safe(root,'trash').resolve():raise ConsoleError('回收路径越界',403)
        shutil.rmtree(folder);return {'ok':True}
    def cleanup(self,p,execute=False,confirm=''):
        root=self.root(p);rows=[];cutoff=datetime.now(timezone.utc).timestamp()-7*86400
        for rel,f in files(root):
            if rel.startswith('assets/thumbnails/') or rel.startswith('art/tmp/') and f.stat().st_mtime<cutoff:rows.append({'path':rel,'size':f.stat().st_size})
        duplicates=[]
        if self.config().get('revision_retention')=='DEDUP_PREVIEW':
            seen=set()
            for row in revisions(root):
                key=(row['path'],row['sha256'])
                if key in seen and row['source']=='PRE_WRITE' and not row['note']:
                    revision_content(root,row['id']) # Verify before allowing deletion of a duplicate.
                    duplicates.append(row['id']);folder=safe(root,'history/revisions/'+row['id'])
                    rows.extend({'path':f.relative_to(root).as_posix(),'size':safe(root,f.relative_to(root).as_posix()).stat().st_size} for f in folder.iterdir() if f.is_file())
                seen.add(key)
        if execute:
            if confirm!='清理可重建缓存':raise ConsoleError('请先预览并确认缓存清理',409)
            for r in rows:safe(root,r['path']).unlink()
            for id in duplicates:
                folder=safe(root,'history/revisions/'+id)
                if folder.exists() and not any(folder.iterdir()):folder.rmdir()
        return {'files':rows,'bytes':sum(r['size'] for r in rows),'cleaned':execute}
    def export(self,p,kind,format):
        root=self.root(p);selected=[]
        if kind=='book':
            for folder in sorted(safe(root,'chapters').glob('chapter-*'),key=lambda x:int(x.name.split('-')[-1]) if x.name.split('-')[-1].isdigit() else 0):
                f=next((f for f in [folder/'final.txt',folder/'final.md'] if f.is_file()),None)
                if f:selected.append((f.relative_to(root).as_posix(),f.read_bytes()))
            if format in {'txt','md'}:return '\n\n'.join(d.decode('utf-8-sig') for _,d in selected).encode('utf8'),'text/plain; charset=utf-8','novel.'+format
        elif kind=='settings':
            for rel,f in files(root):
                if rel.startswith(('characters/','bible/','settings/')) and f.suffix in {'.json','.yaml','.yml','.md'}:selected.append((rel,f.read_bytes()))
            if format in {'json','yaml','md'}:
                obj={n:(json.loads(d) if n.endswith('.json') else yaml.safe_load(d) if n.endswith(('.yaml','.yml')) else d.decode('utf-8-sig')) for n,d in selected}
                text=json.dumps(obj,ensure_ascii=False,indent=2) if format=='json' else yaml.safe_dump(obj,allow_unicode=True,sort_keys=False) if format=='yaml' else '\n\n'.join('## '+n+'\n\n'+d.decode('utf-8-sig') for n,d in selected)
                return text.encode('utf8'),'text/plain; charset=utf-8','settings.'+format
        elif kind=='assets':
            selected=[(r,f.read_bytes()) for r,f in files(root) if r.startswith(('assets/original/','assets/generated/','assets/metadata/'))]
        else:raise ConsoleError('不支持的导出种类',422)
        if format!='zip':raise ConsoleError('请选择有效导出格式',422)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for n,d in selected:z.writestr(n,d)
        return buf.getvalue(),'application/zip',kind+'.zip'
    def scheduled(self,exit=False):
        cfg=self.config()
        if exit and not cfg['on_exit'] or not exit and cfg['schedule']=='OFF':return []
        interval=86400 if cfg['schedule']=='DAILY' else 7*86400;results=[]
        self.registry.scan()
        for p,m in list(self.registry.rows.items()):
            if m['status']['phase']=='ARCHIVED':continue
            last=next((r for r in self.catalog() if r['project_id']==p),None)
            if not exit and last and datetime.now(timezone.utc).timestamp()-datetime.fromisoformat(last['created_at']).timestamp()<interval:continue
            with write_guard(self.registry.engine):results.append(self.backup(p,True,'ON_EXIT' if exit else cfg['schedule']))
        return results
    def start(self):
        from app.tasks.lease import acquire
        try:self.lease=acquire(self.registry.engine,'studio-backup-worker.lock')
        except ConsoleError:return
        def run():
            while not self.stop.wait(60):
                try:self.scheduled()
                except Exception as e:write(self.settings_path.with_name('backup-error.json'),{'time':now(),'error':str(e)[:1000]})
        self.thread=threading.Thread(target=run,daemon=True,name='novel-backup');self.thread.start()
    def close(self):
        from app.tasks.lease import release
        self.stop.set()
        if self.thread:self.thread.join(30)
        release(self.lease)
