import io,json,shutil,threading,time,wave,tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app import writing_metrics
from app.world_maps import MapSave
from app.audio_export import AudioRequest
from app.errors import ConsoleError
from app.library.storage import uid,digest
ENGINE=Path(__file__).resolve().parents[3]

@pytest.fixture
def local(tmp_path,monkeypatch):
    shutil.copytree(ENGINE/'engine',tmp_path/'engine');shutil.copytree(ENGINE/'templates',tmp_path/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'app-data'))
    old=writing_metrics.observer;app=create_app(Settings(workspace=tmp_path));app.state.testing=True
    client=TestClient(app);client.headers['X-Novel-Request']=client.get('/api/session').json()['request_token']
    d=client.post('/api/drafts',json={'input':{'title':'Original test book','premise':'Public isolated fixture','writing':{'form':'short'}}}).json()
    r=client.post('/api/projects',json={'draft_id':d['id'],'version':d['version'],'confirm':True});assert r.status_code==201,r.text
    p=r.json()['id'];url='/api/projects/'+p
    doc=client.get(url+'/files/content',params={'path':'chapters/story/draft.txt'}).json()
    r=client.put(url+'/files/content',json={'path':doc['path'],'content':'这是隔离测试正文。 Hello, world.','etag':doc['etag']});assert r.status_code==200,r.text
    yield client,app,p
    app.state.audio_export.close();app.state.speech.close();client.close();writing_metrics.observer=old

def test_map_real_api_locations_assets_and_backup_restore(local,tmp_path):
    from PIL import Image
    client,app,p=local;url='/api/projects/'+p;root=app.state.registry.workspace(p).root
    before=(root/'chapters/story/draft.txt').read_bytes()
    empty=client.get(url+'/world-maps');assert empty.status_code==200 and empty.json()['maps']==[]
    assert not (root/'metadata/studio/world-maps.json').exists()
    r=client.post(url+'/bible/entities',json={'entity':{'name':'Original Harbor','category':'location','status':'DRAFT'}});assert r.status_code==200,r.text
    entity=r.json();assert entity['status']=='DRAFT' and entity['canon_level']=='REFERENCE'
    stream=io.BytesIO();Image.new('RGB',(80,60),'ivory').save(stream,format='PNG')
    r=client.post(url+'/assets/import?name=Original%20Map',content=stream.getvalue(),headers={'Content-Type':'image/png'});assert r.status_code==200,r.text
    asset=r.json();parent=uid('map');child=uid('map');pin=uid('pin');shape=uid('shape')
    maps=[{'id':parent,'name':'World','background':asset['id'],'pins':[{'id':pin,'entity_id':entity['id'],'x':123,'y':456,'child_map':child}], 'shapes':[{'id':shape,'name':'Trade route','kind':'route','points':[{'x':1,'y':2},{'x':5,'y':8}]}]}, {'id':child,'name':'City','parent_id':parent}]
    r=client.put(url+'/world-maps',json={'etag':empty.json()['etag'],'maps':maps});assert r.status_code==200,r.text
    assert client.put(url+'/world-maps',json={'etag':empty.json()['etag'],'maps':maps}).status_code==409
    reread=client.get(url+'/world-maps').json();assert reread['maps'][0]['pins'][0]['child_map']==child
    assert reread['locations'][0]['summary']==entity['summary']
    entity['name']='Renamed Harbor';r=client.post(url+'/bible/entities',json={'entity':{k:v for k,v in entity.items() if k!='etag'},'etag':entity['etag']});assert r.status_code==200,r.text
    assert client.get(url+'/world-maps').json()['locations'][0]['name']=='Renamed Harbor'
    backup=app.state.data_center.backup(p,images=True,note='ISOLATED_MAP_TEST')
    staged=app.state.data_center.stage(Path(backup['path']).read_bytes())
    restored=app.state.data_center.restore(staged['token'],expected_hash=staged['sha256'])
    new=restored['project_id'];restored_map=client.get('/api/projects/'+new+'/world-maps').json()
    assert restored_map['maps']==reread['maps'];assert app.state.world_maps.assets.path(new,asset['id']).read_bytes()==stream.getvalue()
    assert (root/'chapters/story/draft.txt').read_bytes()==before

def test_map_rejects_hierarchy_foreign_locations_and_limits(local):
    client,app,p=local;service=app.state.world_maps;initial=service.get(p);a=uid('map');b=uid('map')
    for rows in [ [{'id':a,'name':'A','parent_id':b},{'id':b,'name':'B','parent_id':a}], [{'id':a,'name':'A','pins':[{'id':uid('pin'),'entity_id':uid('entity'),'x':1,'y':1}]}] ]:
        with pytest.raises(ConsoleError):service.save(p,MapSave(etag=initial['etag'],maps=rows))
    with pytest.raises(ValueError):MapSave(etag='',maps=[{'id':a,'name':'A','pins':[{'id':uid('pin'),'entity_id':uid('entity'),'x':float('nan'),'y':1}]}])
    assert not service.path(p).exists()

def test_audio_cancel_resume_integrity_and_no_manuscript_write(local):
    client,app,p=local;service=app.state.audio_export;root=service.registry.workspace(p).root;before=(root/'chapters/story/draft.txt').read_bytes()
    service.speech=type('SpeechFixture',(),{'status':lambda self:{'available':True,'voices':[{'id':'fixture','name':'Fixture'}]}})()
    entered=threading.Event();release=threading.Event();calls=[]
    def fixture_render(text,path,voice,rate,cancel):
        calls.append(text);entered.set()
        if not release.wait(3):raise RuntimeError('fixture timeout')
        if cancel.is_set():raise InterruptedError()
        with wave.open(str(path),'wb') as output:output.setnchannels(1);output.setsampwidth(2);output.setframerate(22050);output.writeframes(b'\x00\x00'*100)
        return {'duration_seconds':100/22050,'bytes':path.stat().st_size,'sha256':digest(path.read_bytes())}
    service.render=fixture_render
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-Checks-') as output_dir:
        request=AudioRequest(directory=output_dir,voice='fixture',drafts=True,confirm=False)
        preview=service.preview(p,request);assert len(preview['chapters'])==1 and preview['estimated_seconds'] is None
        with pytest.raises(ConsoleError):service.start(p,request)
        job=service.start(p,request.model_copy(update={'confirm':True,'preview_id':preview['preview_id']}));assert entered.wait(3)
        service.cancel(p,job['id']);release.set();service.threads[p,job['id']].join(5)
        assert service.row(p,job['id'])['status']=='CANCELLED';assert not list(Path(output_dir).rglob('*.wav'))
        resumed=service.resume(p,job['id']);service.threads[p,job['id']].join(5);finished=service.row(p,job['id'])
        assert finished['status']=='SUCCEEDED' and len(finished['completed'])==1
        wav=next(Path(output_dir).rglob('*.wav'))
        with wave.open(str(wav),'rb') as result:assert result.getnframes()==100
        assert (root/'chapters/story/draft.txt').read_bytes()==before
        assert len(calls)==2
        with pytest.raises(ConsoleError):service.resume(p,job['id'])
        with pytest.raises(ConsoleError):service.directory(str(root))


def test_audio_missing_voice_and_changed_source(local):
    client,app,p=local;service=app.state.audio_export
    service.speech=type('SpeechFixture',(),{'status':lambda self:{'available':False,'voices':[]}})()
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-Checks-') as output_dir:
        with pytest.raises(ConsoleError):service.start(p,AudioRequest(directory=output_dir,voice='missing',drafts=True,confirm=True))
    assert service.list(p)==[]


def test_audio_completed_chapters_are_skipped_and_new_source_rejected(local):
    client,app,p=local;service=app.state.audio_export;root=service.registry.workspace(p).root
    folder=root/'chapters/chapter-1';folder.mkdir(parents=True);(folder/'draft.txt').write_text('第二个隔离音频片段。',encoding='utf8')
    service.speech=type('SpeechFixture',(),{'status':lambda self:{'available':True,'voices':[{'id':'fixture','name':'Fixture'}]}})()
    entered=threading.Event();release=threading.Event();calls=[]
    def render(text,path,voice,rate,cancel):
        calls.append(text)
        if len(calls)==2:
            entered.set();release.wait(4)
        if cancel.is_set():raise InterruptedError()
        with wave.open(str(path),'wb') as output:output.setnchannels(1);output.setsampwidth(2);output.setframerate(22050);output.writeframes(b'\x00\x00'*120)
        return {'duration_seconds':120/22050,'bytes':path.stat().st_size,'sha256':digest(path.read_bytes())}
    service.render=render
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-Full-') as output_dir:
        request=AudioRequest(directory=output_dir,voice='fixture',drafts=True,confirm=True)
        prepared=service.preview(p,request);request=request.model_copy(update={'preview_id':prepared['preview_id']})
        job=service.start(p,request);assert entered.wait(4)
        service.cancel(p,job['id']);release.set();service.threads[p,job['id']].join(5)
        paused=service.row(p,job['id']);assert paused['status']=='CANCELLED' and len(paused['completed'])==1
        first=next(Path(output_dir).rglob('*.wav'));first_bytes=first.read_bytes();first_time=first.stat().st_mtime_ns
        service.resume(p,job['id']);service.threads[p,job['id']].join(5)
        finished=service.row(p,job['id']);assert finished['status']=='SUCCEEDED' and len(finished['completed'])==2
        assert first.read_bytes()==first_bytes and first.stat().st_mtime_ns==first_time and len(calls)==3
        # A cancelled snapshot cannot silently export newer manuscript text.
        request=request.model_copy(update={'preview_id':service.preview(p,request)['preview_id']})
        job2=service.start(p,request);service.cancel(p,job2['id']);service.threads[p,job2['id']].join(5)
        changed=root/'chapters/story/draft.txt';changed.write_text('原文已经变化。',encoding='utf8')
        service.resume(p,job2['id']);service.threads[p,job2['id']].join(5)
        assert service.row(p,job2['id'])['status']=='FAILED'
        assert '版本已变化' in service.row(p,job2['id'])['error']


def test_real_application_curves_and_personas_only_change_project_metadata(local):
    client,app,p=local;url='/api/projects/'+p;root=app.state.registry.workspace(p).root
    doc=client.get(url+'/files/content',params={'path':'chapters/story/draft.txt'}).json()
    text='她听到枪声，危险正在逼近。\n“我们还有希望。”'
    saved=client.put(url+'/files/content',json={'path':doc['path'],'content':text,'etag':doc['etag']});assert saved.status_code==200,saved.text
    curve=client.get(url+'/creative-insights/curve');assert curve.status_code==200,curve.text
    response=client.post(url+'/creative-insights/curve/analyze',json={'whole_book':True});assert response.status_code==200,response.text
    data=response.json();point=data['points'][0];chapter=data['chapters'][0]
    assert point['status']=='ROUGH_LOCAL_SIGNALS' and point['evidence']
    from app.studio_tools import utf16_slice
    evidence=point['evidence'][0];assert utf16_slice(text,evidence['start'],evidence['end'])==evidence['quote']
    override=client.put(url+'/creative-insights/curve/override',json={'etag':data['etag'],'chapter_id':chapter['id'],'series_id':'book','tension':8,'note':'Author sees more pressure here.'});assert override.status_code==200,override.text
    reread=client.get(url+'/creative-insights/curve').json();assert reread['points'][0]['tension']==8 and reread['points'][0]['override_current']
    profiles=client.get(url+'/creative-insights/readers');assert profiles.status_code==200,profiles.text
    created=client.put(url+'/creative-insights/readers/personas',json={'etag':profiles.json()['etag'],'persona':{'name':'Isolated mystery reader','age_group':'adult','preferences':'mystery','abandonment_triggers':'unexplained contradictions'}});assert created.status_code==200,created.text
    assert len(client.get(url+'/creative-insights/readers').json()['profiles'])==1
    assert (root/doc['path']).read_text(encoding='utf8')==text
    assert not list((root/'reviews').rglob('*.json')) # No AI request or reader review was started.


def test_audio_preview_binds_source_version_and_duplicate_start(local):
    client,app,p=local;service=app.state.audio_export;root=service.registry.workspace(p).root
    service.speech=type('SpeechFixture',(),{'status':lambda self:{'available':True,'voices':[{'id':'fixture','name':'Fixture'}]}})()
    service.render=lambda *args:(_ for _ in ()).throw(RuntimeError('MOCK intentionally does not synthesize'))
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-Preview-') as output_dir:
        request=AudioRequest(directory=output_dir,voice='fixture',drafts=True,confirm=True)
        with pytest.raises(ConsoleError) as missing:service.start(p,request)
        assert missing.value.code=='AUDIO_PREVIEW_EXPIRED'
        preview=service.preview(p,request);bound=request.model_copy(update={'preview_id':preview['preview_id']})
        source=root/'chapters/story/draft.txt';source.write_text(source.read_text(encoding='utf8')+'追加内容。',encoding='utf8')
        with pytest.raises(ConsoleError) as changed:service.start(p,bound)
        assert changed.value.code=='AUDIO_SOURCE_CHANGED' and not service.list(p)
        preview=service.preview(p,request);bound=request.model_copy(update={'preview_id':preview['preview_id']})
        job=service.start(p,bound);service.threads[p,job['id']].join(5)
        replay=service.start(p,bound);assert replay['id']==job['id'] and len(service.list(p))==1


def test_real_local_sapi_through_application_audio_routes(local):
    import os
    if os.name!='nt':pytest.skip('Windows SAPI is not available on this platform')
    client,app,p=local;url='/api/projects/'+p+'/audio-export'
    cap=client.get(url);assert cap.status_code==200,cap.text
    capabilities=cap.json()['capabilities']
    if not capabilities['available'] or not capabilities['voices']:pytest.skip('No installed local SAPI voice')
    voice=next((v for v in capabilities['voices'] if v.get('chinese')),capabilities['voices'][0])
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-RealSAPI-') as output_dir:
        request={'voice':voice['id'],'rate':0,'directory':output_dir,'drafts':True,'confirm':False}
        preview=client.post(url+'/preview',json=request);assert preview.status_code==200,preview.text
        started=client.post(url,json={**request,'confirm':True,'preview_id':preview.json()['preview_id']});assert started.status_code==200,started.text
        job=started.json();app.state.audio_export.threads[p,job['id']].join(10)
        response=client.get(url+'/'+job['id']);assert response.status_code==200,response.text
        completed=response.json();assert completed['status']=='SUCCEEDED',completed
        files=list(Path(output_dir).rglob('*.wav'));assert len(files)==1
        with wave.open(str(files[0]),'rb') as result:assert result.getnframes()>0 and result.getframerate()==22050
        assert len(completed['completed'])==1

def test_map_corrupt_record_and_self_link_are_explicit(local):
    client,app,p=local;service=app.state.world_maps
    entity=client.post('/api/projects/'+p+'/bible/entities',json={'entity':{'name':'A test port','category':'location','status':'DRAFT'}}).json()
    identifier=uid('map');etag=service.get(p)['etag']
    with pytest.raises(ConsoleError) as error:
        service.save(p,MapSave(etag=etag,maps=[{'id':identifier,'name':'Map','pins':[{'id':uid('pin'),'entity_id':entity['id'],'x':1,'y':1,'child_map':identifier}]}]))
    assert error.value.code=='MAP_SELF_LINK'
    path=service.path(p);path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{broken fixture',encoding='utf-8')
    before=path.read_bytes()
    response=client.get('/api/projects/'+p+'/world-maps')
    assert response.status_code==422 and response.json()['code']=='MAP_DAMAGED'
    assert path.read_bytes()==before


def test_audio_history_damage_isolated_and_empty_scope_rejected(local,monkeypatch):
    client,app,p=local;service=app.state.audio_export
    folder=service.job_dir(p);folder.mkdir(parents=True,exist_ok=True)
    broken=folder/(uid('audio')+'.json');broken.write_text('{bad JSON fixture',encoding='utf-8')
    malformed=folder/(uid('audio')+'.json');malformed.write_text(json.dumps({'status':'SUCCEEDED'}),encoding='utf-8')
    response=client.get('/api/projects/'+p+'/audio-export')
    assert response.status_code==200 and response.json()['jobs']==[]
    assert len(response.json()['warnings'])==2 and broken.is_file() and malformed.is_file()
    monkeypatch.setattr(service.books,'assemble',lambda *args:({'title':'Empty'},[],[],{}))
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-Empty-') as directory:
        with pytest.raises(ConsoleError) as error:service.preview(p,AudioRequest(directory=directory,voice='fixture'))
        assert error.value.code=='AUDIO_EMPTY_SCOPE'


def test_audio_resume_preserves_user_modified_wav_and_streams_hash(local,monkeypatch):
    from app.audio_export import file_digest
    client,app,p=local;service=app.state.audio_export
    service.speech=type('SpeechFixture',(),{'status':lambda self:{'available':True,'voices':[{'id':'fixture','name':'Fixture'}]}})()
    calls=[]
    def render(text,path,voice,rate,cancel):
        calls.append(text)
        with wave.open(str(path),'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(22050);output.writeframes(b'\x01\x00'*2205)
        return {'duration_seconds':.1,'bytes':path.stat().st_size,'sha256':file_digest(path)}
    service.render=render
    with tempfile.TemporaryDirectory(prefix='Novel-Audio-Preserve-') as directory:
        b=AudioRequest(directory=directory,voice='fixture',drafts=True)
        preview=service.preview(p,b);job=service.start(p,b.model_copy(update={'confirm':True,'preview_id':preview['preview_id']}))
        service.threads[p,job['id']].join(5);done=service.row(p,job['id']);assert done['status']=='SUCCEEDED'
        output=next(Path(directory).rglob('*.wav'));output.write_bytes(b'USER_EDITED_AUDIO_FIXTURE')
        service.jobs[p,job['id']]['status']='FAILED'
        original_read=Path.read_bytes
        def read_bytes(path):
            if path.suffix=='.wav':raise AssertionError('WAV hashing must stream, not read whole file')
            return original_read(path)
        monkeypatch.setattr(Path,'read_bytes',read_bytes)
        service.resume(p,job['id']);service.threads[p,job['id']].join(5)
        after=service.row(p,job['id']);assert after['status']=='SUCCEEDED',after
        with output.open('rb') as stream:assert stream.read()==b'USER_EDITED_AUDIO_FIXTURE'
        files=list(Path(directory).rglob('*.wav'));assert len(files)==2 and len(calls)==2
        receipt=next(iter(after['completed'].values()));assert receipt['filename'].endswith('-2.wav')
        assert file_digest(Path(after['output_directory'])/receipt['filename'])==receipt['sha256']


def test_audio_estimate_uses_only_same_project_voice_rate_and_not_scope_binding(local):
    client,app,p=local;service=app.state.audio_export
    from app.library.storage import write
    identifier=uid('audio');chapter='public-sample'
    receipt={'id':identifier,'project_id':p,'status':'SUCCEEDED','created_at':'2026-10-25T00:00:00Z','title':'Sample',
        'request':AudioRequest(directory=str(Path(tempfile.gettempdir()).resolve()),voice='same',rate=0).model_dump(),
        'chapters':[{'id':chapter,'title':'Public sample','characters':1000,'revision':'sample'}],
        'completed':{chapter:{'duration_seconds':100,'bytes':4410044,'sha256':'sample','filename':'sample.wav','revision':'sample'}}}
    write(service.job_dir(p)/(identifier+'.json'),receipt)
    b=AudioRequest(directory=str(Path(tempfile.gettempdir()).resolve()),voice='same',rate=0,drafts=True)
    preview=service.preview(p,b)
    assert preview['estimate_basis']=='PRIOR_LOCAL_AUDIO_SAME_VOICE_RATE' and preview['estimate_sample_characters']==1000
    assert preview['estimated_seconds']==round(sum(row['characters'] for row in preview['chapters'])/10)
    assert service.preview(p,b.model_copy(update={'rate':1}))['estimated_seconds'] is None
    assert service.preview(p,b.model_copy(update={'voice':'different'}))['estimated_seconds'] is None
    service.speech=type('SpeechFixture',(),{'status':lambda self:{'available':True,'voices':[{'id':'same','name':'Fixture'}]}})()
    launched=[];service.launch=lambda p,row:launched.append(row['id'])
    # Newly available calibration changes only the estimate, not the already confirmed text.
    receipt['completed'][chapter]['duration_seconds']=120;write(service.job_dir(p)/(identifier+'.json'),receipt)
    job=service.start(p,b.model_copy(update={'confirm':True,'preview_id':preview['preview_id']}))
    assert job['status']=='QUEUED' and launched==[job['id']]
    service.jobs[p,job['id']]['status']='CANCELLED'

def test_derived_cancellations_bypass_only_mutation_lease_not_session_security(local):
    from app.tasks.lease import acquire,release
    client,app,p=local;service=app.state.audio_export
    identifier=uid('audio');row={'id':identifier,'project_id':p,'status':'RUNNING','chapters':[],'completed':{},'request':{},'title':'Cancellation fixture'}
    service.jobs[p,identifier]=row;service.cancels[p,identifier]=threading.Event()
    token='a'*32;url='/api/projects/'+p
    lock=acquire(app.state.registry.engine,'studio-data.lock')
    try:
        denied=client.post(url+'/book/print-preview/'+token+'/cancel',headers={'X-Novel-Request':''})
        assert denied.status_code==403 and denied.json()['code']=='SESSION_INVALID'
        denied=client.post(url+'/audio-export/'+identifier+'/cancel',headers={'Origin':'https://untrusted.invalid'})
        assert denied.status_code==403 and not service.cancels[p,identifier].is_set()
        response=client.post(url+'/book/print-preview/'+token+'/cancel')
        assert response.status_code==200 and response.json()['status']=='CANCELLED',response.text
        response=client.post(url+'/audio-export/'+identifier+'/cancel')
        assert response.status_code==200 and response.json()['status']=='CANCELLING',response.text
        assert service.cancels[p,identifier].is_set()
        # Ordinary author metadata writes keep the original OS mutation lease.
        assert client.put(url+'/world-maps',json={'etag':'','maps':[]}).status_code==409
    finally:
        release(lock);service.jobs[p,identifier]['status']='CANCELLED'
