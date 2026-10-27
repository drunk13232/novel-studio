"""Local print adapter and immutable-artifact tests, with isolated authored fixtures."""
import copy,os
from pathlib import Path
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.book_center import PrintRequest,heading
from app import print_preview as pp
from app.errors import ConsoleError
from app.library.storage import digest

@pytest.fixture
def service(tmp_path):
    engine=tmp_path/'engine';engine.mkdir();config=tmp_path/'app-data';config.mkdir()
    projects=tmp_path/'projects';projects.mkdir()
    def project(id):
        if id!='isolated':raise ConsoleError('No project',404)
        return {'title':'隔离排版示例'}
    rows=[{'id':'chapter-1','number':1,'title':'山间来信','volume':'','volume_title':'','text':'中文排版示例。A letter in the mountain.\n他把信放在窗前。','han':15}]
    books=SimpleNamespace(config=config,registry=SimpleNamespace(engine=engine,root=projects,get=project),
        assemble=lambda p,b:({'title':'隔离排版示例'},copy.deepcopy(rows),[],None))
    return pp.PrintPreview(books,heading),rows,tmp_path

def test_html_is_offline_escaped_and_uses_real_paged_css(service):
    _,rows,_=service;b=PrintRequest(cover='none',paper_size='POCKET32',gutter_mm=4,margin=1.5)
    rows[0]['title']='山间</style><script>alert(1)</script>'
    rows[0]['text']='<img src="https://example.invalid/private">'
    source=pp.document_html('隔离书名',rows,b,heading)
    assert 'size:130mm 185mm' in source and 'margin-left:19.0mm' in source
    assert '@page chapter0' in source and 'counter(page)' in source and 'orphans:2;widows:2' in source
    assert '<script>' not in source and '<img src=' not in source
    assert '&lt;img' in source and '\\3c /style' in source
    assert "default-src &#x27;none&#x27;" in source and "connect-src &#x27;none&#x27;" in source
    assert 'https://example.invalid/private' in source  # Escaped prose is text, not an external load.

def test_font_and_unusable_page_geometry_are_rejected(service):
    _,rows,_=service
    with pytest.raises(ConsoleError):pp.document_html('test',rows,PrintRequest(font='https://fonts.invalid/a'),heading)
    with pytest.raises(ConsoleError):pp.document_html('test',rows,PrintRequest(paper_size='POCKET32',margin=5),heading)
    with pytest.raises(ValidationError):PrintRequest(paper_size='poster')

def test_long_paragraph_warning_uses_actual_source_line_and_is_not_a_fake_orphan_check(service):
    _,rows,_=service;rows[0]['text']='第一行。\n'+'长'*1001
    warning=pp.layout_warnings(rows)
    assert warning==[{'kind':'LONG_PARAGRAPH','chapter_id':'chapter-1','chapter_number':1,'line':2,'characters':1001,'snippet':'长'*90}]
    assert pp.layout_warnings([{**rows[0],'text':'短'*1000}])==[]

def test_browser_missing_keeps_manuscript_and_reports_external_requirement(service,monkeypatch):
    renderer,_,_=service;monkeypatch.setattr(pp,'installed_browser',lambda:None)
    with pytest.raises(ConsoleError) as caught:renderer.preview('isolated',PrintRequest())
    assert caught.value.status==503 and not renderer.root('isolated').exists()

@pytest.mark.skipif(os.environ.get('NOVEL_VERIFY_PRINT')!='1',reason='Explicit opt-in for real local headless Edge rendering')
@pytest.mark.parametrize('paper',list(pp.PAPERS))
def test_actual_local_edge_print_preview_and_export_are_identical_bytes(service,paper):
    renderer,rows,root=service
    if not pp.installed_browser():pytest.skip('No installed Edge/Chrome')
    rows[0]['text']=('中文排版示例，确认字符和页面尺寸。English typography check.\n'*35)
    request=PrintRequest(cover='none',toc=False,paper_size=paper,margin=1.5,gutter_mm=3,drafts=True,font='Microsoft YaHei')
    record=renderer.preview('isolated',request);stored,path=renderer.get('isolated',record['id'])
    from pypdf import PdfReader
    reader=PdfReader(path);text=''.join(page.extract_text() for page in reader.pages)
    assert '中文排版示例' in text and 'Englishtypographycheck' in ''.join(text.split())
    width,height=pp.PAPERS[paper]
    assert abs(float(reader.pages[0].mediabox.width)*25.4/72-width)<0.2
    assert abs(float(reader.pages[0].mediabox.height)*25.4/72-height)<0.2
    assert record['pages']==len(reader.pages)>=2
    assert record['chapter_pages'][0]['page']==2 and record['front_pages']==1
    assert reader.outline and reader.get_destination_page_number(reader.outline[0])==1
    assert all('file:///' not in page.extract_text() for page in reader.pages)
    assert not any(child.name.startswith('render-') for child in renderer.root('isolated').iterdir())
    before=path.read_bytes();again=renderer.preview('isolated',request)
    assert again['sha256']==record['sha256'] and path.read_bytes()==before
    exported=renderer.export('isolated',record['id'],str(root/'output'),allow_snapshot=True)
    assert Path(exported['path']).read_bytes()==before and exported['sha256']==digest(before)
    for target in [renderer.books.registry.engine,renderer.books.registry.root,renderer.books.config]:
        with pytest.raises(ConsoleError):renderer.export('isolated',record['id'],str(target))
    with pytest.raises(ConsoleError):renderer.get('other',record['id'])
    path.write_bytes(before+b'changed')
    with pytest.raises(ConsoleError) as caught:renderer.get('isolated',record['id'])
    assert caught.value.status==409


def test_long_paragraph_warning_carries_verified_utf16_source_evidence(service):
    _,rows,_=service;line='长'*1001;rows[0]['text']='短段。\n'+line
    raw='# 章节标题\n\n短段。\n'+line
    sources={'chapter-1':{'content':raw,'path':'chapters/chapter-1/draft.txt','etag':'a'*64}}
    warning=pp.layout_warnings(rows,sources)[0];start=raw.index(line)
    assert warning['path']=='chapters/chapter-1/draft.txt'
    assert warning['document_revision']=='a'*64 and warning['evidence'] is True
    assert warning['start']==len(raw[:start].encode('utf-16-le'))//2
    assert raw[start:start+90]==warning['exact'] and warning['end']-warning['start']==90


@pytest.mark.skipif(os.environ.get('NOVEL_VERIFY_PRINT')!='1',reason='Explicit opt-in for actual local HTTP/PDF integration')
def test_actual_application_print_endpoints_keep_project_files_unchanged(tmp_path,monkeypatch):
    import shutil
    from fastapi.testclient import TestClient
    from app.config import Settings
    from app.main import create_app
    from app import writing_metrics
    engine=Path(__file__).resolve().parents[3];workspace=tmp_path/'fixture-engine';workspace.mkdir()
    shutil.copytree(engine/'engine',workspace/'engine');shutil.copytree(engine/'templates',workspace/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'isolated-app-data'))
    old=writing_metrics.observer
    try:
        app=create_app(Settings(workspace=workspace));app.state.testing=True
        with TestClient(app) as client:
            client.headers['X-Novel-Request']=client.get('/api/session').json()['request_token']
            draft=client.post('/api/drafts',json={'input':{'title':'本地印刷验证','premise':'隔离演示','writing':{'form':'short'}}}).json()
            created=client.post('/api/projects',json={'draft_id':draft['id'],'version':draft['version'],'confirm':True});assert created.status_code==201,created.text
            project=created.json()['id'];base=f'/api/projects/{project}';manuscript='chapters/story/draft.txt'
            doc=client.get(base+'/files/content',params={'path':manuscript}).json()
            result=client.put(base+'/files/content',json={'path':manuscript,'content':'这是中文排版隔离检查。Local PDF integration sample.','etag':doc['etag']});assert result.status_code==200,result.text
            project_root=app.state.registry.workspace(project).root
            before={file.relative_to(project_root).as_posix():digest(file.read_bytes()) for file in project_root.rglob('*') if file.is_file()}
            response=client.post(base+'/book/print-preview',json={'format':'pdf','cover':'none','toc':False,'drafts':True,'confirm_warnings':True,'margin':1.5})
            assert response.status_code==200,response.text
            artifact=response.json();pdf=client.get(artifact['file_url']);assert pdf.status_code==200 and pdf.headers['content-type']=='application/pdf'
            assert digest(pdf.content)==artifact['sha256'] and artifact['pages']>=2
            exported=client.post(base+'/book/print/'+artifact['id']+'/export',json={'directory':str(tmp_path/'export-output')})
            assert exported.status_code==200,exported.text
            assert Path(exported.json()['path']).read_bytes()==pdf.content
            after={file.relative_to(project_root).as_posix():digest(file.read_bytes()) for file in project_root.rglob('*') if file.is_file()}
            assert before==after
    finally:writing_metrics.observer=old


def test_appended_source_cannot_bind_old_assembled_text_to_new_revision(service,monkeypatch):
    renderer,rows,_=service;monkeypatch.setattr(pp,'installed_browser',lambda:Path('fake-browser.exe'))
    old=rows[0]['text'];rows[0].update(draft='chapters/chapter-1/draft.txt',final=None,document_revision='old-revision')
    renderer.books.registry.workspace=lambda p:SimpleNamespace(content=lambda path:{'content':old+'\n新增的一句。','etag':'new-revision'})
    with pytest.raises(ConsoleError) as caught:renderer.preview('isolated',PrintRequest(cover='none',drafts=True))
    assert caught.value.status==409 and not renderer.root('isolated').exists()


@pytest.mark.skipif(os.environ.get('NOVEL_VERIFY_PRINT')!='1',reason='Actual local Edge chapter-page verification')
def test_actual_chapter_navigation_ignores_toc_and_description_mentions(service):
    renderer,rows,_=service
    if not pp.installed_browser():pytest.skip('No installed Edge/Chrome')
    first='山谷里传来一封无人署名的信。第一章的真实正文从这里开始。'
    second='码头边的清晨有人点起灯。第二章的真实正文从这里开始。'
    rows[0]['text']=first*25
    rows.append({'id':'chapter-2','number':2,'title':'码头清晨','volume':'','volume_title':'','text':second*25,'han':500})
    record=renderer.preview('isolated',PrintRequest(cover='none',toc=True,running_header=False,description=first,margin=1.5))
    first_page,second_page=[chapter['page'] for chapter in record['chapter_pages']]
    assert first_page is not None and first_page>1
    assert second_page is not None and second_page>first_page
    from pypdf import PdfReader
    reader=PdfReader(renderer.get('isolated',record['id'])[1])
    assert '山间来信' in reader.pages[0].extract_text()  # Title in TOC is not mistaken for chapter start.
    assert first[:10] in reader.pages[first_page-1].extract_text()
    assert second[:10] in reader.pages[second_page-1].extract_text()

def test_unextractable_or_ambiguous_chapter_pages_are_not_guessed(service):
    _,rows,_=service;b=PrintRequest()
    class Page:
        def __init__(self,text,heading):self.text=text;self.heading=heading
        def extract_text(self,visitor_text):
            visitor_text(self.heading,[1,0,0,1,0,0],[1,0,0,1,0,0],None,b.size*1.3)
            return self.text
    label=heading(rows[0]);body=rows[0]['text']
    result,front=pp.chapter_locations(SimpleNamespace(pages=[Page(body,label),Page(body,label)]),rows,b,heading)
    assert result[0]['page'] is None and result[0]['reason']=='AMBIGUOUS' and front is None
    result,front=pp.chapter_locations(SimpleNamespace(pages=[Page('缺少正文锚点',label)]),rows,b,heading)
    assert result[0]['page'] is None and result[0]['status']=='UNRESOLVED'


def test_cancel_before_registration_is_idempotent_and_cannot_later_run(service,monkeypatch):
    renderer,_,_=service;request='1'*32
    monkeypatch.setattr(pp,'installed_browser',lambda:pytest.fail('Cancelled job must not start a browser'))
    first=renderer.cancel('isolated',request);second=renderer.cancel('isolated',request)
    assert first==second and first['status']=='CANCELLED'
    assert renderer.preview('isolated',PrintRequest(request_id=request))['status']=='CANCELLED'
    with pytest.raises(ConsoleError):renderer.cancel('other',request)
    assert not renderer.root('isolated').exists()


def test_cancel_running_job_and_same_project_reentry_are_bounded(service,monkeypatch):
    import threading
    renderer,_,_=service;entered=threading.Event();results=[]
    monkeypatch.setattr(pp,'installed_browser',lambda:Path('fake-browser.exe'))
    def render(browser,source,target,profile,timeout=60,cancel=lambda:False):
        entered.set()
        while not cancel():entered.wait(0.01)
        raise pp.PrintCancelled()
    monkeypatch.setattr(pp,'render_pdf',render)
    worker=threading.Thread(target=lambda:results.append(renderer.preview('isolated',PrintRequest(cover='none',request_id='2'*32))))
    worker.start()
    try:
        assert entered.wait(2)
        with pytest.raises(ConsoleError) as caught:renderer.preview('isolated',PrintRequest(cover='none',request_id='3'*32))
        assert caught.value.code=='PRINT_ALREADY_RUNNING'
        receipt=renderer.cancel('isolated','2'*32);assert receipt['status']=='CANCELLED'
        worker.join(timeout=3);assert not worker.is_alive() and results[0]['status']=='CANCELLED'
        assert not list(renderer.root('isolated').glob('*.pdf'))
        assert not list(renderer.root('isolated').glob('*.json'))
    finally:
        renderer.cancel('isolated','2'*32);worker.join(timeout=3)


def test_cancel_queued_job_does_not_wait_for_unrelated_render(service,monkeypatch):
    import threading
    renderer,_,_=service;renderer.books.registry.get=lambda p:{'title':'isolated'}
    monkeypatch.setattr(pp,'installed_browser',lambda:Path('fake-browser.exe'));renderer.lock.acquire()
    results=[];thread=threading.Thread(target=lambda:results.append(renderer.preview('isolated',PrintRequest(cover='none',request_id='4'*32))))
    thread.start()
    try:
        import time
        deadline=time.monotonic()+2
        while ('isolated','4'*32) not in renderer.jobs and time.monotonic()<deadline:time.sleep(.01)
        receipt=renderer.cancel('isolated','4'*32);thread.join(timeout=2)
        assert receipt['status']=='CANCELLED' and not thread.is_alive() and results[0]['status']=='CANCELLED'
    finally:
        renderer.lock.release();thread.join(timeout=3)


@pytest.mark.skipif(os.environ.get('NOVEL_VERIFY_PRINT')!='1',reason='Actual owned headless Edge cancellation')
def test_actual_local_edge_cancellation_reaps_only_its_owned_process(tmp_path,monkeypatch):
    import threading
    browser=pp.installed_browser()
    if not browser:pytest.skip('No installed browser')
    source=tmp_path/'source.html';source.write_text('<!doctype html><html><body>'+('<p>Local cancellation fixture.</p>'*1000)+'</body></html>',encoding='utf-8')
    cancel=threading.Event();processes=[];original=pp.subprocess.Popen
    def track(*args,**kwargs):
        process=original(*args,**kwargs);processes.append(process);return process
    monkeypatch.setattr(pp.subprocess,'Popen',track)
    timer=threading.Timer(.05,cancel.set);timer.start()
    try:
        with pytest.raises(pp.PrintCancelled):pp.render_pdf(browser,source,tmp_path/'out.pdf',tmp_path/'profile',cancel=cancel.is_set)
        assert len(processes)==1 and processes[0].poll() is not None
    finally:timer.cancel()


def test_source_revision_status_requires_explicit_old_snapshot_export(service,monkeypatch):
    renderer,_,root=service
    record={'id':'5'*32,'sha256':digest(b'%PDF-isolated'),'chapter_count':1,'filename':'isolated.pdf','pages':1,'file_url':'/local.pdf',
            'source_versions':[{'chapter_id':'one','path':'chapters/chapter-1/draft.txt','document_revision':'old'}]}
    folder=renderer.root('isolated');folder.mkdir(parents=True);pdf=folder/(record['id']+'.pdf');pdf.write_bytes(b'%PDF-isolated')
    from app.library.storage import write
    write(folder/(record['id']+'.json'),record)
    latest={'etag':'old'};renderer.books.registry.workspace=lambda p:SimpleNamespace(content=lambda path:latest)
    assert renderer.source_status('isolated',record['id'])['status']=='CURRENT'
    latest['etag']='new';status=renderer.source_status('isolated',record['id'])
    assert status['status']=='CHANGED' and status['changed'][0]['reason']=='REVISION_CHANGED'
    with pytest.raises(ConsoleError) as caught:renderer.export('isolated',record['id'],str(root/'output'))
    assert caught.value.code=='PRINT_SNAPSHOT_STALE' and not (root/'output').exists()
    saved=renderer.export('isolated',record['id'],str(root/'output'),allow_snapshot=True)
    assert Path(saved['path']).read_bytes()==pdf.read_bytes() and saved['sha256']==record['sha256']

def test_print_request_id_is_bound_and_completed_artifact_is_reverified(service,monkeypatch):
    from app.library.storage import write
    renderer,_,_=service
    calls=[]
    def artifact(p,b,job):
        identifier='b'*32;root=renderer.root(p);root.mkdir(parents=True,exist_ok=True)
        pdf=root/(identifier+'.pdf');pdf.write_bytes(b'%PDF-1.4\nIsolated immutable artifact fixture')
        record={'id':identifier,'sha256':digest(pdf.read_bytes()),'filename':'isolated.pdf'}
        write(root/(identifier+'.json'),record);calls.append(job.id);return record
    monkeypatch.setattr(renderer,'_preview_artifact',artifact)
    request=PrintRequest(request_id='a'*32,paper_size='A5')
    first=renderer.preview('isolated',request);assert first['status']=='SUCCEEDED'
    assert renderer.preview('isolated',request)['sha256']==first['sha256'] and len(calls)==1
    with pytest.raises(ConsoleError) as caught:renderer.preview('isolated',request.model_copy(update={'paper_size':'POCKET32'}))
    assert caught.value.code=='PRINT_REQUEST_CONFLICT' and len(calls)==1
    (renderer.root('isolated')/(first['id']+'.pdf')).write_bytes(b'Externally replaced PDF fixture')
    with pytest.raises(ConsoleError) as caught:renderer.preview('isolated',request)
    assert caught.value.status==409 and len(calls)==1
