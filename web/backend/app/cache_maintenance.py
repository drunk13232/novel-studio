"""Explicit, frozen cache cleanup; never accepts filesystem paths from clients."""
import os,time,uuid,threading
from pathlib import Path
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError

class Cleanup(BaseModel):
    model_config=ConfigDict(extra='forbid')
    preview_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    buckets:list[Literal['npm','vite','build','thumbnails']]=Field(min_length=1,max_length=4)
    confirm:Literal[True]

class CacheMaintenance:
    def __init__(self,engine,registry):
        self.engine=engine.resolve();self.registry=registry;self.lock=threading.RLock();self.previews={}
    def bases(self,project):
        rows={'npm':self.engine/'web/.build-cache/npm','vite':self.engine/'web/frontend/node_modules/.vite','build':self.engine/'desktop/build'}
        if project:rows['thumbnails']=self.registry.workspace(project).root/'assets/thumbnails'
        return rows
    def guarded(self,path,base):
        base=Path(base);path=Path(path)
        if not path.is_relative_to(base):raise ConsoleError('缓存路径越界',403)
        for part in [path,*path.parents]:
            if part.is_symlink() or part.is_junction():raise ConsoleError('缓存链接被拒绝',403)
            if part==base.parent:break
        # Also guard all ancestors of the cache root, not only its children.
        for part in [base,*base.parents]:
            if part.is_symlink() or part.is_junction():raise ConsoleError('缓存根目录链接被拒绝',403)
        return path
    def busy(self):
        return (self.engine/'desktop/.cache-operation.lock').exists()
    def scan(self,project=''):
        with self.lock:
            self.previews={k:v for k,v in self.previews.items() if time.monotonic()-v['at']<900}
            if self.busy():raise ConsoleError('正在构建或维护缓存，请稍后再试',409)
            cutoff=time.time()-48*3600;files=[];summary=[];truncated=False
            for key,base in self.bases(project).items():
                size=0;count=0;skipped=0;stack=[base] if base.exists() else []
                while stack:
                    directory=self.guarded(stack.pop(),base)
                    try:
                        with os.scandir(directory) as children:
                            for entry in children:
                                path=Path(entry.path)
                                if entry.is_symlink() or path.is_junction():skipped+=1;continue
                                if entry.is_dir(follow_symlinks=False):stack.append(path);continue
                                stat=entry.stat(follow_symlinks=False)
                                if not entry.is_file(follow_symlinks=False) or stat.st_mtime>=cutoff:continue
                                if key=='thumbnails' and path.suffix.lower()!='.jpg':continue
                                files.append((key,str(path),stat.st_size,stat.st_mtime_ns));size+=stat.st_size;count+=1
                                if len(files)>=20000:truncated=True;stack=[];break
                    except (OSError,ConsoleError):skipped+=1
                    if truncated:break
                summary.append({'id':key,'bytes':size,'files':count,'skipped':skipped})
                if truncated:break
            token=uuid.uuid4().hex;self.previews[token]={'at':time.monotonic(),'project':project,'files':files}
            return {'preview_id':token,'buckets':summary,'truncated':truncated,'minimum_age_hours':48,'expires_seconds':900,'automatic':False}
    def cleanup(self,body,project=''):
        with self.lock:
            frozen=self.previews.get(body.preview_id)
            if not frozen or frozen['project']!=project or time.monotonic()-frozen['at']>=900:raise ConsoleError('缓存预览已过期或不属于当前作品，请重新扫描',409)
            lock=self.engine/'desktop/.cache-operation.lock';lock.parent.mkdir(parents=True,exist_ok=True)
            try:handle=lock.open('x')
            except FileExistsError:raise ConsoleError('正在构建或维护缓存，请稍后再试',409)
            try:
                selected=[row for row in frozen['files'] if row[0] in body.buckets];bases=self.bases(project)
                for key,name,size,mtime in selected:
                    p=self.guarded(Path(name),bases[key])
                    try:s=p.stat()
                    except OSError:raise ConsoleError('缓存已变化，请重新扫描；尚未删除任何文件',409)
                    if s.st_size!=size or s.st_mtime_ns!=mtime:raise ConsoleError('缓存已变化，请重新扫描；尚未删除任何文件',409)
                # Consume before mutation; neither a double click nor retry can replay.
                self.previews.pop(body.preview_id,None);deleted=0;total=0;skipped=0
                for key,name,size,mtime in selected:
                    p=self.guarded(Path(name),bases[key])
                    try:
                        s=p.stat()
                        if s.st_mtime_ns!=mtime or s.st_size!=size:skipped+=1;continue
                        p.unlink();deleted+=1;total+=size
                    except OSError:skipped+=1
                return {'deleted_files':deleted,'logical_bytes':total,'skipped':skipped,'reclaimed_bytes':None,'automatic':False}
            finally:
                handle.close();lock.unlink(missing_ok=True)
