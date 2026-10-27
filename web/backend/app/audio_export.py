"""Resumable offline SAPI WAV export over the existing manuscript assembly."""
import copy, hashlib, json, os, re, threading, time, wave
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from app.book_center import ExportRequest, heading
from app.errors import ConsoleError
from app.library.storage import safe, read, write, digest, uid, now

class AudioRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    chapters:list[str]=Field(default_factory=list,max_length=2000)
    drafts:bool=False
    voice:str=Field(min_length=1,max_length=600)
    rate:int=Field(default=0,ge=-10,le=10)
    directory:str=Field(min_length=1,max_length=1000)
    confirm:bool=False
    preview_id:str=Field(default='',pattern=r'^(?:preview_[0-9a-f]{32})?$')

def clean_name(text):
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',text).strip(' .')[:70] or 'Untitled'
    if re.match(r'^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)',name,re.I):name='_'+name
    return name

def file_digest(path):
    # A long chapter WAV can be large; never load it into Python memory to hash it.
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def publish_new_file(source,target):
    # Preserve externally changed files: publication never replaces an existing name.
    if os.name=='nt':os.rename(source,target)
    else:
        os.link(source,target)
        source.unlink()

def sapi_to_wav(text,path,voice_id,rate,cancel):
    # A separate owned COM apartment avoids rerouting the live read-aloud voice.
    import comtypes
    from comtypes.client import CreateObject
    comtypes.CoInitialize();voice=stream=None
    try:
        voice=CreateObject('SAPI.SpVoice');tokens=voice.GetVoices()
        token=next((tokens.Item(i) for i in range(tokens.Count) if tokens.Item(i).Id==voice_id),None)
        if token is None:raise ConsoleError('选择的本机语音包已不可用',422,code='AUDIO_VOICE')
        voice.Voice=token;voice.Rate=rate
        stream=CreateObject('SAPI.SpFileStream');stream.Format.Type=22 # SAFT22kHz16BitMono
        stream.Open(str(path),3,False);voice.AudioOutputStream=stream
        # Each paragraph is bounded and cancellation is polled without a UI message loop.
        for start in range(0,len(text),3000):
            if cancel.is_set():raise InterruptedError('CANCELLED')
            voice.Speak(text[start:start+3000],1|16) # Async + NOT XML
            deadline=time.monotonic()+180
            while not voice.WaitUntilDone(50):
                if cancel.is_set():voice.Speak('',3);raise InterruptedError('CANCELLED')
                if time.monotonic()>deadline:voice.Speak('',3);raise ConsoleError('本机语音合成超时；可继续导出已完成的章节',504,code='AUDIO_TIMEOUT')
        stream.Close();stream=None
        with wave.open(str(path),'rb') as wav:
            if wav.getnframes()==0:raise ConsoleError('语音包没有生成音频',422,code='AUDIO_EMPTY')
            seconds=wav.getnframes()/wav.getframerate()
        return {'duration_seconds':seconds,'bytes':path.stat().st_size,'sha256':file_digest(path)}
    finally:
        if voice:
            try:voice.Speak('',3)
            except Exception:pass
        if stream:
            try:stream.Close()
            except Exception:pass
        voice=stream=None;comtypes.CoUninitialize()

class AudioExport:
    def __init__(self,books,speech):self.books=books;self.registry=books.registry;self.speech=speech;self.lock=threading.RLock();self.jobs={};self.previews={};self.closed=False;self.cancels={};self.threads={};self.render=sapi_to_wav
    def job_dir(self,p):return safe(self.registry.workspace(p).root,'metadata/studio/audio-exports')
    def capabilities(self,p):
        self.registry.get(p);status=self.speech.status()
        for _ in range(50):
            if status.get('available') or status.get('error'):break
            time.sleep(.02);status=self.speech.status()
        return {'available':status.get('available',False),'voices':status.get('voices',[]),'error':status.get('error'),'format':'WAV','network':False,'estimate':'UNKNOWN_UNTIL_SYNTHESIZED'}
    def row(self,p,id):
        if not re.fullmatch(r'audio_[0-9a-f]{32}',id):raise ConsoleError('音频任务不存在',404,code='AUDIO_NOT_FOUND')
        with self.lock:
            value=copy.deepcopy(self.jobs.get((p,id)) or read(safe(self.job_dir(p),id+'.json')))
        if not value:raise ConsoleError('音频任务不存在',404,code='AUDIO_NOT_FOUND')
        if (p,id) not in self.jobs and value['status'] in {'QUEUED','RUNNING','CANCELLING'}:value['status']='INTERRUPTED'
        return value
    def save(self,p,row):write(safe(self.job_dir(p),row['id']+'.json'),row)
    def history(self,p):
        rows=[];warnings=[]
        candidates=[]
        for file in self.job_dir(p).glob('audio_*.json'):
            try:candidates.append((file.stat().st_mtime,file))
            except OSError:warnings.append({'code':'AUDIO_HISTORY_DAMAGED','record':file.stem})
        candidates=[file for _,file in sorted(candidates,key=lambda item:item[0],reverse=True)]
        for file in candidates[:200]:
            try:
                row=self.row(p,file.stem)
                if not isinstance(row,dict) or not isinstance(row.get('chapters'),list) or not isinstance(row.get('completed'),dict) or row.get('id')!=file.stem:raise ValueError('invalid audio receipt')
                AudioRequest.model_validate(row.get('request'))
                if row.get('status') not in {'QUEUED','RUNNING','CANCELLING','SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:raise ValueError('invalid status')
                if any(not isinstance(ch,dict) or not isinstance(ch.get('id'),str) or not isinstance(ch.get('title'),str) for ch in row['chapters']):raise ValueError('invalid chapters')
                if any(not isinstance(done,dict) or not isinstance(done.get('duration_seconds'),(int,float)) or not isinstance(done.get('bytes'),int) for done in row['completed'].values()):raise ValueError('invalid completion')
                rows.append(row)
                if len(rows)>=50:break
            except (ConsoleError,ValueError,KeyError,TypeError,OSError):
                warnings.append({'code':'AUDIO_HISTORY_DAMAGED','record':file.stem})
        rows=sorted(rows,key=lambda row:row.get('created_at',''),reverse=True)
        return {'jobs':rows[:50],'warnings':warnings,'history_limited':len(candidates)>200}
    def list(self,p):return self.history(p)['jobs']
    def estimate(self,p,b,characters):
        samples=[]
        for job in self.history(p)['jobs']:
            request=job.get('request',{})
            if job.get('project_id')!=p:continue
            if request.get('voice')!=b.voice or request.get('rate')!=b.rate:continue
            chapters={row['id']:row for row in job['chapters']}
            for identifier,done in job['completed'].items():
                chapter=chapters.get(identifier,{})
                if done.get('revision')!=chapter.get('revision'):continue
                count=chapter.get('characters',0);seconds=done.get('duration_seconds',0)
                if isinstance(count,(int,float)) and isinstance(seconds,(int,float)) and count>0 and seconds>0 and seconds/count<20:samples.append((count,seconds))
        count=sum(item[0] for item in samples)
        if count<500:return {'estimated_seconds':None,'estimated_bytes':None,'estimate_basis':'VOICE_DEPENDENT_UNKNOWN'}
        seconds=round(characters*sum(item[1] for item in samples)/count)
        return {'estimated_seconds':seconds,'estimated_bytes':seconds*44100,'estimate_basis':'PRIOR_LOCAL_AUDIO_SAME_VOICE_RATE','estimate_sample_characters':count,'estimate_sample_chapters':len(samples),'estimate_caveat':'TEXT_LANGUAGE_AND_PUNCTUATION_CHANGE_DURATION'}
    def directory(self,value):
        if value.startswith(('\\\\','//')):raise ConsoleError('请选择本机磁盘目录，离线导出不访问网络共享',403,code='AUDIO_LOCAL_ONLY')
        original=Path(value).expanduser()
        if not original.is_absolute():raise ConsoleError('请选择绝对输出目录',422,code='AUDIO_DIRECTORY')
        if any(parent.is_symlink() or parent.is_junction() for parent in [original,*original.parents]):raise ConsoleError('输出目录不能经过链接',403,code='AUDIO_SYMLINK')
        directory=original.resolve()
        protected=[self.registry.engine.resolve(),self.registry.root.resolve(),self.books.config.resolve()]
        if any(directory.is_relative_to(root) for root in protected):raise ConsoleError('音频必须导出到作品和软件工程之外',403,code='AUDIO_PROTECTED_DIRECTORY')
        return directory
    def _preview(self,p,b):
        directory=self.directory(b.directory);catalog,rows,warnings,_=self.books.assemble(p,ExportRequest(chapters=b.chapters,drafts=b.drafts,cover='none'))
        if not rows:raise ConsoleError('所选范围没有可导出的正文；可选择章节或明确包含草稿',422,code='AUDIO_EMPTY_SCOPE')
        if sum(len(r['text']) for r in rows)>8_000_000:raise ConsoleError('本次音频范围过大，请分卷导出',413,code='AUDIO_LIMIT')
        return {'title':catalog['title'],'chapters':[{'id':r['id'],'title':heading(r),'characters':len(r['text']),'revision':digest(r['text'].encode())} for r in rows],'warnings':warnings,'directory':str(directory),**self.estimate(p,b,sum(len(r['text']) for r in rows)),'format':'WAV'}
    def preview(self,p,b):
        result=self._preview(p,b);identifier=uid('preview')
        with self.lock:
            self.previews={key:value for key,value in self.previews.items() if time.monotonic()-value['created']<900}
            if len(self.previews)>=100:self.previews.pop(next(iter(self.previews)))
            self.previews[p,identifier]={'created':time.monotonic(),'request':b.model_dump(exclude={'confirm','preview_id'}),'preview':copy.deepcopy(result)}
        return {**result,'preview_id':identifier,'valid_for_seconds':900}
    def start(self,p,b):
        if not b.confirm:raise ConsoleError('请确认本机声音、章节范围和输出目录后开始',409,code='AUDIO_CONFIRM')
        cap=self.capabilities(p)
        if not cap['available'] or not any(v['id']==b.voice for v in cap['voices']):raise ConsoleError('没有可用的本机语音包，请先安装或选择 Windows 语音',503,code='AUDIO_UNAVAILABLE')
        with self.lock:
            if self.closed:raise ConsoleError('软件正在退出，未启动新的导出',409,code='AUDIO_CLOSING')
            prepared=self.previews.get((p,b.preview_id))
            if not prepared or time.monotonic()-prepared['created']>=900:raise ConsoleError('音频预览已过期，请重新核对音频范围',409,code='AUDIO_PREVIEW_EXPIRED')
            if prepared['request']!=b.model_dump(exclude={'confirm','preview_id'}):raise ConsoleError('范围或声音设置已变化，请重新预览',409,code='AUDIO_PREVIEW_CHANGED')
            preview=self._preview(p,b)
            frozen_keys=('title','chapters','warnings','directory','format')
            if any(preview.get(key)!=prepared['preview'].get(key) for key in frozen_keys):raise ConsoleError('正文范围或版本已变化，请建立新的导出，旧音频不冒充新正文',409,code='AUDIO_SOURCE_CHANGED')
            identifier='audio_'+b.preview_id.removeprefix('preview_')
            if (p,identifier) in self.jobs:return copy.deepcopy(self.jobs[p,identifier])
            if any(r['status'] in {'QUEUED','RUNNING','CANCELLING'} for r in self.jobs.values()):raise ConsoleError('已有音频导出运行中，请等待或取消',409,code='AUDIO_BUSY')
            row={'id':identifier,'project_id':p,'created_at':now(),'status':'QUEUED','request':b.model_dump(),'title':preview['title'],'chapters':preview['chapters'],'completed':{},'current':None,'error':None,'warnings':preview['warnings']}
            self.jobs[p,row['id']]=row;self.save(p,row);self.launch(p,row)
            return copy.deepcopy(row)
    def launch(self,p,row):
        cancel=threading.Event();self.cancels[p,row['id']]=cancel
        thread=threading.Thread(target=self.run,args=(p,row,cancel),daemon=True,name='NovelStudio-AudioExport');self.threads[p,row['id']]=thread;thread.start()
    def resume(self,p,id):
        with self.lock:
            if self.closed:raise ConsoleError('软件正在退出，未启动新的导出',409,code='AUDIO_CLOSING')
            row=self.row(p,id)
            request=AudioRequest.model_validate(row['request'])
            cap=self.capabilities(p)
            if not cap['available'] or not any(v['id']==request.voice for v in cap['voices']):raise ConsoleError('恢复前请安装原本机语音包；不能静默换用其他声音',503,code='AUDIO_UNAVAILABLE')
            if row.get('project_id')!=p:raise ConsoleError('恢复的音频记录仅供查看，请在当前作品重新创建导出',409,code='AUDIO_RESTORED')
            if row['status'] not in {'FAILED','CANCELLED','INTERRUPTED'}:raise ConsoleError('此任务不需要继续',409,code='AUDIO_NOT_RESUMABLE')
            if any(r['status'] in {'QUEUED','RUNNING','CANCELLING'} for r in self.jobs.values()):raise ConsoleError('已有音频导出运行中',409,code='AUDIO_BUSY')
            self.jobs[p,id]=row;row.update(status='QUEUED',error=None);self.save(p,row);self.launch(p,row);return copy.deepcopy(row)
    def cancel(self,p,id):
        with self.lock:
            row=self.row(p,id)
            if row['status'] in {'QUEUED','RUNNING','CANCELLING'}:
                self.cancels[p,id].set();self.jobs[p,id]['status']='CANCELLING';self.save(p,self.jobs[p,id])
            return self.row(p,id)
    def run(self,p,row,cancel):
        temporary=None
        try:
            request=AudioRequest.model_validate(row['request']);directory=self.directory(request.directory)
            catalog,rows,_,_=self.books.assemble(p,ExportRequest(chapters=request.chapters,drafts=request.drafts,cover='none'))
            expected={r['id']:r['revision'] for r in row['chapters']}
            if set(expected)!={r['id'] for r in rows} or any(digest(r['text'].encode())!=expected[r['id']] for r in rows):raise ConsoleError('正文范围或版本已变化，请建立新的导出，旧音频不冒充新正文',409,code='AUDIO_SOURCE_CHANGED')
            folder=self.directory(str(directory/(clean_name(row['title'])+'-'+row['id'][-8:])));folder.mkdir(parents=True,exist_ok=True)
            with self.lock:
                if cancel.is_set():raise InterruptedError('CANCELLED')
                row['status']='RUNNING';self.save(p,row)
            for i,chapter in enumerate(rows,1):
                if cancel.is_set():raise InterruptedError('CANCELLED')
                done=row['completed'].get(chapter['id'])
                if done and done.get('revision')==expected[chapter['id']]:
                    existing=safe(folder,done['filename'])
                    if existing.is_file() and file_digest(existing)==done['sha256']:continue
                with self.lock:row['current']=chapter['id'];self.save(p,row)
                sub=self.directory(str(folder/clean_name(chapter['volume_title'] or 'Main')));sub.mkdir(exist_ok=True)
                if sub.is_symlink() or sub.is_junction():raise ConsoleError('音频输出子目录不能是链接',403,code='AUDIO_SYMLINK')
                output=sub/(str(i).zfill(4)+'-'+clean_name(heading(chapter))+'.wav');temporary=output.with_name(output.stem+'-'+uid('part')+'.pending.wav')
                info=self.render(chapter['text'],temporary,request.voice,request.rate,cancel)
                with self.lock:
                    if cancel.is_set():raise InterruptedError('CANCELLED')
                    # A user may have edited a previous WAV or placed a file here. Keep it.
                    original=output
                    for collision in range(1000):
                        try:publish_new_file(temporary,output);break
                        except FileExistsError:output=original.with_name(original.stem+'-'+str(collision+2)+original.suffix)
                    else:raise ConsoleError('输出文件同名过多，请选择新的导出目录',409,code='AUDIO_OUTPUT_CONFLICT')
                    temporary=None
                    row['completed'][chapter['id']]={**info,'filename':output.relative_to(folder).as_posix(),'revision':expected[chapter['id']]};self.save(p,row)
            with self.lock:
                if cancel.is_set():raise InterruptedError('CANCELLED')
                row.update(status='SUCCEEDED',current=None,finished_at=now(),output_directory=str(folder));self.save(p,row)
        except InterruptedError:
            with self.lock:row.update(status='CANCELLED',current=None,finished_at=now());self.save(p,row)
        except Exception as error:
            with self.lock:row.update(status='FAILED',current=None,error=str(error)[:600],error_code=getattr(error,'code',None),finished_at=now());self.save(p,row)
        finally:
            if temporary:temporary.unlink(missing_ok=True)
    def close(self):
        with self.lock:
            self.closed=True
            for cancel in self.cancels.values():cancel.set()
            threads=list(self.threads.values())
        for thread in threads:thread.join(timeout=3)

def routes(service):
    router=APIRouter(prefix='/api/projects/{p}/audio-export')
    @router.get('')
    def get(p:str):return {'capabilities':service.capabilities(p),**service.history(p)}
    @router.post('/preview')
    def preview(p:str,b:AudioRequest):return service.preview(p,b)
    @router.post('')
    def start(p:str,b:AudioRequest):return service.start(p,b)
    @router.get('/{id}')
    def get_job(p:str,id:str):return service.row(p,id)
    @router.post('/{id}/cancel')
    def cancel(p:str,id:str):return service.cancel(p,id)
    @router.post('/{id}/resume')
    def resume(p:str,id:str):return service.resume(p,id)
    return router
