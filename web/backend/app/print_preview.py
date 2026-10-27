"""Bounded local Chromium print adapter; one immutable PDF for preview and export.

Uses installed Edge/Chrome. No browser download, user profile, scripts, URLs or
remote fonts. This service never writes manuscript, Canon, State or Knowledge.
"""
import base64,contextlib,html,json,math,os,re,shutil,subprocess,tempfile,threading,time,unicodedata,uuid
from pathlib import Path
from app.errors import ConsoleError
from app.library.storage import safe,read,write,digest,write_bytes,now

PAPERS={'A5':(148,210),'POCKET32':(130,185)}
FONTS={'SimSun','Microsoft YaHei','KaiTi','FangSong','Noto Serif CJK SC','Noto Sans CJK SC'}
MAX_CHARACTERS=2000000
MAX_PDF_BYTES=50*1024*1024

def installed_browser():
    candidates=[]
    for root in [os.environ.get('ProgramFiles(x86)'),os.environ.get('ProgramFiles'),os.environ.get('LOCALAPPDATA')]:
        if root:
            candidates.extend([Path(root)/'Microsoft/Edge/Application/msedge.exe',Path(root)/'Google/Chrome/Application/chrome.exe'])
    if os.name!='nt':
        for name in ['chromium','chromium-browser','google-chrome']:
            value=shutil.which(name)
            if value:candidates.append(Path(value))
    return next((path for path in candidates if path.is_file()),None)

def capabilities():
    browser=installed_browser()
    return {'pdf_available':bool(browser),'pdf_engine':'Microsoft Edge' if browser and browser.name=='msedge.exe' else 'Chromium' if browser else None,
            'pdf_papers':{key:{'width_mm':size[0],'height_mm':size[1]} for key,size in PAPERS.items()},'pdf_fonts':sorted(FONTS)}

def layout_warnings(rows,sources=None):
    warnings=[]
    for row in rows:
        source=(sources or {}).get(row['id']);cursor=0
        for index,line in enumerate(row['text'].splitlines(),1):
            found=source['content'].find(line,cursor) if source and line else -1
            if found>=0:cursor=found+len(line)
            if len(line)>1000:
                warning={'kind':'LONG_PARAGRAPH','chapter_id':row['id'],'chapter_number':row.get('number'),
                         'line':index,'characters':len(line),'snippet':line[:90]}
                if found>=0:
                    exact=line[:90];raw=source['content'];start=len(raw[:found].encode('utf-16-le'))//2
                    warning.update(path=source['path'],document_revision=source['etag'],exact=exact,start=start,
                                   end=start+len(exact.encode('utf-16-le'))//2,prefix=raw[max(0,found-32):found],suffix=raw[found+len(exact):found+len(exact)+32],evidence=True)
                warnings.append(warning)
            if len(warnings)>=100:return warnings
    return warnings

def chapter_locations(reader,rows,b,heading):
    """Verify H2 text at the renderer's real font size AND the body prefix.

    TOC entries are normal-size list text, so a title appearing there cannot
    establish a chapter page. Ambiguous or unextractable glyphs stay unresolved.
    """
    normalized=lambda text:re.sub(r'\s+','',unicodedata.normalize('NFC',text))
    pages=[];expected_size=b.size*1.3
    for page in reader.pages:
        titles=[]
        def visit(text,cm,tm,font,size):
            scale=math.hypot(cm[0],cm[1])
            if text.strip() and abs(float(size)*scale-expected_size)<0.25:titles.append(text)
        text=page.extract_text(visitor_text=visit)
        pages.append({'heading':normalized(''.join(titles)),'text':normalized(text)})
    result=[];first_page=None;previous=0
    for row in rows:
        label=heading(row);needle=normalized(row['text'])[:64]
        matches=[index+1 for index,page in enumerate(pages) if index+1>previous and page['heading']==normalized(label) and needle and needle in page['text']]
        located=matches[0] if len(matches)==1 else None
        if located:
            previous=located
            if first_page is None:first_page=located
        result.append({'id':row['id'],'title':label,'number':row.get('number'),'page':located,
                       'status':'LOCATED' if located else 'UNRESOLVED',
                       'reason':None if located else 'EMPTY_BODY' if not needle else 'AMBIGUOUS' if len(matches)>1 else 'NO_VERIFIED_MATCH'})
    return result,result[0]['page']-1 if result and result[0]['page'] is not None else None

def document_html(title,rows,b,heading,cover=None):
    if b.font not in FONTS:raise ConsoleError('请选择印刷预览支持的系统字体；不会下载外部字体',422)
    width,height=PAPERS[b.paper_size];margin=b.margin*10;gutter=b.gutter_mm
    if width-2*margin-gutter<60 or height-2*margin<80:raise ConsoleError('页边距和装订留白过大，正文区域不足，请缩小后重试',422)
    def page_style(name,label):
        clean=re.sub(r'\s+',' ',label)[:30]+('…' if len(label)>30 else '')
        header='"'+clean.replace('\\','\\\\').replace('"','\\"').replace('<','\\3c ').replace('>','\\3e ')+'"' if b.running_header else 'none' 
        footer='counter(page)' if b.page_numbers else 'none'
        common=f'@page {name}{{size:{width}mm {height}mm;margin:{margin}mm;@top-center{{content:{header};font-size:8pt;color:#555}}@bottom-center{{content:{footer};font-size:9pt}}}}'
        return common+f'@page {name}:right{{margin-left:{margin+gutter}mm;margin-right:{margin}mm}}@page {name}:left{{margin-right:{margin+gutter}mm;margin-left:{margin}mm}}'
    styles=[page_style('front',title)]
    parts=['<section class="front"><h1>'+html.escape(title)+'</h1>']
    if b.author:parts.append('<p class="author">'+html.escape(b.author)+'</p>')
    if b.description:parts.append('<p class="description">'+html.escape(b.description)+'</p>')
    if cover:
        if cover.stat().st_size>10*1024*1024:raise ConsoleError('封面超过本地印刷预览的 10 MB 限制，请先缩小或选择不使用封面',422)
        from PIL import Image
        import io
        with Image.open(cover) as image:
            image.thumbnail((1400,1800));buffer=io.BytesIO();image.convert('RGB').save(buffer,format='JPEG',quality=85)
        parts.append('<img class="cover" alt="" src="data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii')+'">')
    if b.toc:parts.extend(['<h2>目录 / Contents</h2><ol class="contents">',*['<li>'+html.escape(heading(row))+'</li>' for row in rows],'</ol>'])
    parts.append('</section>')
    for index,row in enumerate(rows):
        name='chapter'+str(index);label=heading(row);styles.append(page_style(name,label))
        parts.append('<section class="chapter" style="page:'+name+'"><h2>'+html.escape(label)+'</h2>')
        parts.extend('<p>'+html.escape(line)+'</p>' for line in row['text'].splitlines() if line.strip())
        parts.append('</section>')
    css=''.join(styles)+f'html{{font-family:"{b.font}","Microsoft YaHei","Noto Serif CJK SC",serif;font-size:{b.size}pt;color:#151515}}body{{margin:0}}.front{{page:front}}h1{{font-size:22pt;text-align:center;margin-top:24mm}}h2{{font-size:{b.size*1.3}pt;break-after:avoid;text-align:{b.title_style}}}p{{text-indent:{b.indent}em;line-height:{b.leading};margin:0 0 {b.spacing}pt;orphans:2;widows:2;white-space:pre-wrap;overflow-wrap:anywhere}}.author{{text-align:center;text-indent:0}}.description{{margin-block:12mm}}.cover{{display:block;max-width:100%;max-height:110mm;object-fit:contain;margin:8mm auto}}.contents{{line-height:1.8}}'
    csp="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; script-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'"
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="'+html.escape(csp,quote=True)+'"><title>Novel Studio Print</title><style>'+css+'</style></head><body>'+''.join(parts)+'</body></html>' 

class PrintCancelled(Exception):pass
class PrintJob:
    def __init__(self,project,id,fingerprint=''):
        self.fingerprint=fingerprint;self.project=project;self.id=id;self.cancel=threading.Event();self.status='QUEUED';self.result=None

def render_pdf(browser,source,target,profile,timeout=60,cancel=lambda:False):
    command=[str(browser),'--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-extensions',
             '--disable-background-networking','--disable-component-update','--disable-sync','--disable-features=Translate,MediaRouter,OptimizationHints',
             '--proxy-server=http://127.0.0.1:9','--proxy-bypass-list=<-loopback>','--no-pdf-header-footer',
             '--user-data-dir='+str(profile),'--print-to-pdf='+str(target),source.as_uri()]
    process=None;job=None
    try:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                 cwd=str(source.parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if os.name=='nt':
            # Use the already-installed Windows Job API, scoped to this process tree.
            import win32job,win32api
            job=win32job.CreateJobObject(None,'');limits=win32job.QueryInformationJobObject(job,win32job.JobObjectExtendedLimitInformation)
            limits['BasicLimitInformation']['LimitFlags']=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE|win32job.JOB_OBJECT_LIMIT_JOB_MEMORY|win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            limits['BasicLimitInformation']['ActiveProcessLimit']=24;limits['JobMemoryLimit']=1536*1024*1024
            win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,limits)
            handle=win32api.OpenProcess(0x0100|0x0001,False,process.pid)
            try:win32job.AssignProcessToJobObject(job,handle)
            finally:handle.Close()
        deadline=time.monotonic()+timeout
        while process.poll() is None:
            if cancel():raise PrintCancelled()
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired(command,timeout)
            try:process.wait(timeout=min(0.1,remaining))
            except subprocess.TimeoutExpired:continue
        if cancel():raise PrintCancelled()
        code=process.returncode
        if code or not target.is_file():raise ConsoleError('本地 PDF 排版未完成，请检查系统浏览器是否可用或缩小章节范围后重试',422,params={'exit_code':code,'output_present':target.is_file()})
        if target.stat().st_size>MAX_PDF_BYTES:raise ConsoleError('生成的 PDF 超过 50 MB，请缩小导出范围',422)
    except subprocess.TimeoutExpired:raise ConsoleError('本地 PDF 排版超过 60 秒，已停止本次浏览器子进程；请缩小范围重试',408) from None
    except (ConsoleError,PrintCancelled):raise
    except Exception as error:raise ConsoleError('无法启动受限的本地 PDF 排版进程；不会退回无隔离浏览器',503) from error
    finally:
        if job:job.Close()
        if process and process.poll() is None:
            process.kill()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:pass

class PrintPreview:
    def __init__(self,books,heading):
        self.books=books;self.heading=heading;self.lock=threading.Lock();self.jobs_lock=threading.RLock();self.jobs={};self.closed=False
    def _check(self,job):
        if job.cancel.is_set() or self.closed:raise PrintCancelled()
    def _trim_jobs(self):
        terminal=[key for key,job in self.jobs.items() if job.status in {'SUCCEEDED','FAILED','CANCELLED'}]
        for key in terminal[:-64]:self.jobs.pop(key,None)
    @contextlib.contextmanager
    def render_slot(self,job):
        acquired=False
        try:
            while not acquired:
                self._check(job);acquired=self.lock.acquire(timeout=0.1)
            self._check(job)
            with self.jobs_lock:job.status='RUNNING'
            yield
        finally:
            if acquired:self.lock.release()
    def cancel(self,p,id):
        self.books.registry.get(p)
        if not re.fullmatch(r'[0-9a-f]{32}',id):raise ConsoleError('无效的排版请求编号',422)
        with self.jobs_lock:
            key=(p,id);job=self.jobs.get(key)
            if not job:
                job=PrintJob(p,id);job.status='CANCELLED';job.cancel.set();self.jobs[key]=job
            elif job.status not in {'SUCCEEDED','FAILED'}:job.cancel.set();job.status='CANCELLED'
            self._trim_jobs()
            return {'request_id':id,'project_id':p,'status':job.status,'artifact_id':job.result['id'] if job.result else None}
    def close(self):
        with self.jobs_lock:
            self.closed=True
            for job in self.jobs.values():
                if job.status in {'QUEUED','RUNNING'}:job.cancel.set()
    def preview(self,p,b):
        self.books.registry.get(p);id=b.request_id or uuid.uuid4().hex;key=(p,id)
        request_fingerprint=digest(json.dumps(b.model_dump(exclude={'request_id'}),ensure_ascii=False,sort_keys=True).encode())
        with self.jobs_lock:
            if self.closed:raise ConsoleError('软件正在退出，不能开始新的印刷预览',503)
            previous=self.jobs.get(key)
            if previous:
                if previous.status=='CANCELLED':return {'status':'CANCELLED','project_id':p,'request_id':id}
                if previous.fingerprint!=request_fingerprint:raise ConsoleError('排版请求编号已用于另一组参数，请重新生成',409,code='PRINT_REQUEST_CONFLICT')
                if previous.status=='SUCCEEDED' and previous.result:
                    verified,_=self.get(p,previous.result['id'])
                    return {**verified,'status':'SUCCEEDED','request_id':id}
                raise ConsoleError('这次排版请求仍在执行或已经结束，请等待或使用新的请求编号',409,code='PRINT_ALREADY_RUNNING')
            if any(job.project==p and job.status in {'QUEUED','RUNNING'} for job in self.jobs.values()):raise ConsoleError('本书已有排版正在执行，请先等待或取消',409,code='PRINT_ALREADY_RUNNING')
            if sum(job.status in {'QUEUED','RUNNING'} for job in self.jobs.values())>=4:raise ConsoleError('本地排版队列已满，请稍后重试',429)
            job=PrintJob(p,id,request_fingerprint);self.jobs[key]=job;self._trim_jobs()
        try:
            record=self._preview_artifact(p,b,job)
            with self.jobs_lock:
                self._check(job);job.status='SUCCEEDED';job.result=record
            return {**record,'status':'SUCCEEDED','request_id':id}
        except PrintCancelled:
            with self.jobs_lock:job.status='CANCELLED'
            return {'status':'CANCELLED','project_id':p,'request_id':id}
        except Exception:
            with self.jobs_lock:job.status='FAILED'
            raise

    def root(self,p):self.books.registry.get(p);return safe(self.books.config,'print-previews/'+p)
    def get(self,p,id):
        if not re.fullmatch(r'[0-9a-f]{32}',id):raise ConsoleError('印刷预览记录不存在',404)
        root=self.root(p);record=read(safe(root,id+'.json'),None);path=safe(root,id+'.pdf')
        if not record or not path.is_file() or path.stat().st_size>MAX_PDF_BYTES or digest(path.read_bytes())!=record['sha256']:raise ConsoleError('印刷预览已缺失或被外部修改，请重新生成',409)
        return record,path
    def _preview_artifact(self,p,b,job):
        self._check(job);browser=installed_browser()
        if not browser:raise ConsoleError('需要本机已有 Microsoft Edge 或 Chrome 才能生成 PDF；软件不会自动下载浏览器，TXT / Word / EPUB 仍可使用',503)
        # Existing assembler owns selection, draft/Final and stable chapter checks.
        catalog,rows,warnings,cover=self.books.assemble(p,b)
        count=sum(len(row['text']) for row in rows)
        if count>MAX_CHARACTERS or len(rows)>1000:raise ConsoleError('单次印刷预览最多 1000 章或 200 万字符，请分卷生成',422)
        if warnings and not b.confirm_warnings:raise ConsoleError('请先确认草稿、空章节等原有导出警告后再生成 PDF',409)
        sources={}
        for row in rows:
            self._check(job)
            path=row.get('final') or row.get('draft')
            if not path:continue
            doc=self.books.registry.workspace(p).content(path);raw=doc['content'].replace('\r\n','\n')
            from app.book_center import prose
            expected=raw if row.get('kind')=='story' else prose(raw)
            if row['text']!=expected or row.get('document_revision')!=doc['etag']:raise ConsoleError('正文在准备印刷预览时已变化，请重新生成',409)
            sources[row['id']]={'path':path,'etag':doc['etag'],'content':raw}
        options=b.model_dump(exclude={'directory','confirm_warnings','request_id'})
        fingerprint=digest(json.dumps({'version':2,'project':p,'options':options,'rows':rows,'source_revisions':{key:doc['etag'] for key,doc in sources.items()},'cover':digest(cover.read_bytes()) if cover else None},ensure_ascii=False,sort_keys=True).encode())
        id=fingerprint[:32];root=self.root(p)
        with self.render_slot(job):
            self._check(job)
            if safe(root,id+'.json').is_file():return self.get(p,id)[0]
            root.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='pdf-',dir=self.books.config) as temporary:
                folder=Path(temporary);source=folder/'book.html';target=folder/'book.pdf'
                source.write_text(document_html(catalog['title'],rows,b,self.heading,cover),encoding='utf-8')
                render_pdf(browser,source,target,folder/'isolated-profile',cancel=job.cancel.is_set)
                self._check(job)
                data=target.read_bytes()
                if not data.startswith(b'%PDF-'):raise ConsoleError('本地排版没有返回有效 PDF，请重试',422)
                from pypdf import PdfReader
                import io
                try:
                    reader=PdfReader(io.BytesIO(data));pages=len(reader.pages)
                    if not pages:raise ValueError('No pages')
                    chapter_pages,front_pages=chapter_locations(reader,rows,b,self.heading)
                    # Chromium rounds physical paper dimensions to device pixels.
                    # Normalize the blank outer edge once before either preview or
                    # export sees the artifact; glyph coordinates are unchanged.
                    from pypdf import PdfWriter
                    from pypdf.generic import RectangleObject
                    width_mm,height_mm=PAPERS[b.paper_size];writer=PdfWriter()
                    for page in reader.pages:
                        self._check(job)
                        page.mediabox=RectangleObject([0,0,width_mm*72/25.4,height_mm*72/25.4])
                        page.cropbox=RectangleObject([0,0,width_mm*72/25.4,height_mm*72/25.4]);writer.add_page(page)
                    for chapter in chapter_pages:
                        if chapter['page'] is not None:writer.add_outline_item(chapter['title'],chapter['page']-1)
                    normalized=io.BytesIO();writer.add_metadata({'/Title':'Novel Studio Print','/Creator':'Novel Studio local print preview'});writer.write(normalized);data=normalized.getvalue()
                except PrintCancelled:raise
                except Exception:raise ConsoleError('生成的 PDF 无法读取，请缩小范围重试',422) from None
                self._check(job)
                width,height=PAPERS[b.paper_size]
                record={'id':id,'project_id':p,'created_at':now(),'sha256':digest(data),'source_fingerprint':fingerprint,
                        'pages':pages,'chapter_pages':chapter_pages,'front_pages':front_pages,'size':len(data),'paper_size':b.paper_size,'width_mm':width,'height_mm':height,
                        'engine_page_rounding_normalized':True,'chapter_count':len(rows),'han':sum(row['han'] for row in rows),'source_warnings':warnings,
                        'layout_warnings':layout_warnings(rows,sources),'source_versions':[{'chapter_id':key,'path':doc['path'],'document_revision':doc['etag']} for key,doc in sources.items()],'limits':['WIDOW_ORPHAN_NOT_MEASURED','SYSTEM_FONT_FALLBACK_POSSIBLE'],
                        'file_url':f'/api/projects/{p}/book/print/{id}/file','filename':'NovelStudio-Print-'+id[:8]+'.pdf'}
                with self.jobs_lock:
                    self._check(job)
                    write_bytes(safe(root,id+'.pdf'),data);write(safe(root,id+'.json'),record)
                    job.status='SUCCEEDED';job.result=record
                return record
    def source_status(self,p,id):
        record,_=self.get(p,id);references=record.get('source_versions',[]);changed=[];verified=0
        for reference in references:
            try:
                doc=self.books.registry.workspace(p).content(reference['path'])
                if doc['etag']!=reference['document_revision']:changed.append({'chapter_id':reference['chapter_id'],'path':reference['path'],'reason':'REVISION_CHANGED'})
                else:verified+=1
            except ConsoleError:changed.append({'chapter_id':reference.get('chapter_id'),'path':reference.get('path'),'reason':'MISSING'})
        status='CHANGED' if changed else 'UNKNOWN' if not references or len(references)<record['chapter_count'] else 'CURRENT'
        return {'project_id':p,'artifact_id':id,'status':status,'checked_at':now(),'verified_chapters':verified,
                'source_chapters':record['chapter_count'],'changed':changed}
    def export(self,p,id,directory='',allow_snapshot=False):
        record,path=self.get(p,id)
        current=self.source_status(p,id)
        if current['status']!='CURRENT' and not allow_snapshot:raise ConsoleError('正文版本已变化或无法核实；请重新生成，或明确选择导出旧快照',409,code='PRINT_SNAPSHOT_STALE')
        if directory.startswith(('\\\\','//')):raise ConsoleError('离线 PDF 导出只接受本机磁盘目录',403)
        target_root=Path(directory).expanduser().resolve() if directory else (self.books.registry.engine.parent/'NovelStudio Exports').resolve()
        if any(target_root.is_relative_to(root.resolve()) for root in [self.books.registry.root,self.books.registry.engine,self.books.config]):raise ConsoleError('PDF 输出目录必须在小说、应用数据和工程目录之外',403)
        try:
            target_root.mkdir(parents=True,exist_ok=True)
            target=target_root/record['filename']
            if target.exists():
                if digest(target.read_bytes())!=record['sha256']:raise ConsoleError('同名文件已存在且内容不同，请选择其他输出目录',409)
            else:write_bytes(target,path.read_bytes())
            if digest(target.read_bytes())!=record['sha256']:raise ConsoleError('导出校验未通过；印刷预览原件仍然保留',409)
        except OSError:raise ConsoleError('PDF 输出目录不可写、空间不足或文件正在使用；预览原件仍保留，请选择其他目录重试',422) from None
        return {'saved':True,'path':str(target),'sha256':record['sha256'],'pages':record['pages'],'download_url':record['file_url']}
