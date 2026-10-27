"""Real local plugin lifecycle and WASI enforcement. No remote AI calls."""
import hashlib,io,json,time,zipfile
from pathlib import Path
import pytest
from test_python_control import client,finish
from app.extensions.examples import package

def rebuild(raw,change=None,extra=None):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:data={n:z.read(n) for n in z.namelist()}
    manifest=json.loads(data['manifest.json'])
    if change:change(manifest,data)
    manifest['files']={n:hashlib.sha256(v).hexdigest() for n,v in data.items() if n!='manifest.json'}
    data['manifest.json']=json.dumps(manifest,ensure_ascii=False).encode()
    if extra:data.update(extra)
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in data.items():z.writestr(n,v)
    return b.getvalue()

def preview(c,raw):return c.post('/api/plugins/preview',files={'file':('local.zip',raw,'application/zip')})
def install(c,raw):
    response=preview(c,raw);assert response.status_code==200,response.text
    value=response.json()
    result=c.post('/api/plugins/install',json={'token':value['token'],'expected_revision':value['previous_revision']})
    assert result.status_code==200,result.text
    return result.json()
def enable(c,row):
    response=c.put('/api/plugins/'+row['manifest']['id']+'/enabled',json={'revision':row['revision'],'enabled':True})
    assert response.status_code==200,response.text
    return response.json()
def launch(c,p,row,command):
    response=c.post('/api/plugins/'+row['manifest']['id']+'/commands/'+command+'/run',json={'revision':row['revision'],'persona':'yoshino','instruction':'Isolated plugin test','context':{'project':p,'page':'write'}})
    assert response.status_code==202,response.text
    return response.json()

@pytest.mark.parametrize('name',['writing-shortcuts','chapter-summary','integration-entries'])
def test_examples_preview_install_enable_export_schema(client,name):
    c,app,p,_=client;row=install(c,package(name))
    assert row['enabled'] is False
    assert c.post('/api/plugins/'+row['manifest']['id']+'/commands/'+row['manifest']['commands'][0]['id']+'/preview',json={'revision':row['revision']}).status_code==409
    enable(c,row)
    import jsonschema
    jsonschema.Draft202012Validator(c.get('/api/plugins/schema').json()).validate(row['manifest'])
    result=c.get('/api/plugins/'+row['manifest']['id']+'/export');assert result.status_code==200
    exported=preview(c,result.content);assert exported.status_code==200
    from app.extensions.service import PluginHub
    reopened=PluginHub(app,app.state.plugins.root.parent)
    assert reopened.list()[0]['enabled'] is True
    assert reopened.list()[0]['manifest']==row['manifest']

def test_plugin_runs_genuine_python_through_existing_actions(client):
    c,app,p,engine=client;row=enable(c,install(c,package('chapter-summary')))
    before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('chapters','characters','state','bible') for f in (engine/'projects'/p/folder).rglob('*') if f.is_file()}
    run=finish(c,launch(c,p,row,'summarize'))
    assert run['task']['status']=='SUCCEEDED',run
    assert 'get_active_project' in [v['tool'] for v in run['steps']]
    assert 'list_chapters' in [v['tool'] for v in run['steps']]
    parsed=json.loads(run['output']);assert parsed['project']['id']==p
    assert parsed['chapters']['total']==2
    assert before=={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in before}

def test_configuration_is_non_sensitive_and_resolved_at_execution(client):
    c,app,p,_=client;row=enable(c,install(c,package('writing-shortcuts')));id=row['manifest']['id']
    assert c.put('/api/plugins/'+id+'/config',json={'revision':row['revision'],'values':{'font_size':'oops','chapter':1}}).status_code==422
    assert c.put('/api/plugins/'+id+'/config',json={'revision':row['revision'],'values':{'font_size':22,'chapter':1}}).status_code==200
    plan=c.post('/api/plugins/'+id+'/commands/font/preview',json={'revision':row['revision']}).json()
    assert '22' in plan['code'] and '${font_size}' not in plan['code']
    bad=rebuild(package('writing-shortcuts'),lambda m,d:m['settings'].append({'id':'api_key','label':'Key','default':'value'}))
    assert preview(c,bad).status_code==422

def test_untrusted_python_cannot_call_undeclared_action(client):
    c,app,p,_=client
    def change(m,d):d['scripts/summary.py']=b'from novel_studio_api import Studio\nStudio.connect().notes.create("should never appear")\n'
    row=enable(c,install(c,rebuild(package('chapter-summary'),change)))
    run=finish(c,launch(c,p,row,'summarize'))
    assert run['task']['status']=='FAILED'
    assert '不在此插件已声明' in run['output']
    assert not app.state.workbench.entries(p)['notes']

def test_disable_invalidates_fixed_pending_confirmation(client):
    c,app,p,_=client
    def change(m,d):
        m['actions']=['create_inspiration_note']
        d['scripts/summary.py']=b'from novel_studio_api import Studio\nStudio.connect().notes.create("pending plugin note")\n'
    row=enable(c,install(c,rebuild(package('chapter-summary'),change)))
    task=launch(c,p,row,'summarize');run=finish(c,task);assert run['pending']['kind']=='confirm'
    token=run['pending']['token']
    assert c.put('/api/plugins/'+row['manifest']['id']+'/enabled',json={'revision':row['revision'],'enabled':False}).status_code==200
    response=c.post('/api/assistant/sessions/'+task['id']+'/reply',json={'token':token,'approved':True,'context':{'project':p}})
    assert response.status_code==409
    assert not app.state.workbench.entries(p)['notes']

def test_disable_cancels_owned_worker_without_late_output(client):
    c,app,p,_=client
    def change(m,d):d['scripts/summary.py']=b'import time\nprint("started",flush=True)\ntime.sleep(30)\nprint("late output")\n'
    row=enable(c,install(c,rebuild(package('chapter-summary'),change)))
    task=launch(c,p,row,'summarize')
    until=time.monotonic()+15
    while time.monotonic()<until:
        if 'started' in c.get('/api/assistant/sessions/'+task['id']).json()['output']:break
        time.sleep(.1)
    c.put('/api/plugins/'+row['manifest']['id']+'/enabled',json={'revision':row['revision'],'enabled':False})
    run=finish(c,task)
    assert run['task']['status'] in {'CANCELLED','INTERRUPTED','FAILED'}
    assert 'late output' not in run['output']

def test_tampered_file_and_undeclared_binary_or_path_are_rejected(client):
    c,app,p,_=client;row=install(c,package('chapter-summary'))
    root=app.state.plugins.folder(row['manifest']['id'],row['revision'])
    (root/'scripts/summary.py').write_text('print("tampered")',encoding='utf-8')
    assert c.put('/api/plugins/'+row['manifest']['id']+'/enabled',json={'revision':row['revision'],'enabled':True}).status_code==422
    for name in ['../outside.py','C:/outside.py','a\\outside.py','tools/run.exe','a//same.py','CON.txt']:
        assert preview(c,rebuild(package('chapter-summary'),extra={name:b'no execution'})).status_code==422,name
    assert preview(c,rebuild(package('chapter-summary'),lambda m,d:m['actions'].append('run_python_plan'))).status_code==422

def test_update_is_reviewed_disabled_and_previous_version_preserved(client):
    c,app,p,_=client;first=enable(c,install(c,package('chapter-summary')))
    second=install(c,rebuild(package('chapter-summary'),lambda m,d:m.update(version='1.0.1')))
    assert second['enabled'] is False
    assert app.state.plugins.folder(first['manifest']['id'],first['revision']).is_dir()
    assert c.put('/api/plugins/'+first['manifest']['id']+'/enabled',json={'revision':first['revision'],'enabled':True}).status_code==409
    result=c.post('/api/plugins/'+second['manifest']['id']+'/uninstall',json={'revision':second['revision']})
    assert result.status_code==200 and result.json()['recoverable'] is True
    assert c.get('/api/plugins').json()['plugins']==[]
    assert install(c,package('chapter-summary'))['enabled'] is False

def test_corrupt_registry_only_isolates_plugins(client):
    c,app,p,_=client
    from app.extensions.service import PluginHub
    path=app.state.plugins.path;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('not-json',encoding='utf-8')
    broken=PluginHub(app,path.parent.parent)
    assert broken.blocked and not broken.list()
    assert c.get('/api/projects/'+p+'/studio').status_code==200
