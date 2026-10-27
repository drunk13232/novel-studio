"""Combined shipping HTTP routes, isolated files and no external service calls."""
import shutil
from pathlib import Path
from app import writing_metrics
from test_writing_dashboard_api import local_client, get_json

ENGINE=Path(__file__).resolve().parents[3]

def test_focus_replace_undo_and_clue_metadata_through_real_routes(tmp_path,monkeypatch):
    shutil.copytree(ENGINE/'engine',tmp_path/'engine')
    shutil.copytree(ENGINE/'templates',tmp_path/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'isolated-data'))
    previous=writing_metrics.observer
    client=None
    try:
        client,app,_=local_client(tmp_path)
        draft=client.post('/api/drafts',json={'input':{'title':'Isolated daily tools','premise':'Fictional local checks only.','writing':{'form':'short'}}})
        assert draft.status_code==201,draft.text
        d=draft.json()
        created=client.post('/api/projects',json={'draft_id':d['id'],'version':d['version'],'confirm':True})
        assert created.status_code==201,created.text
        project=created.json()['id'];base=f'/api/projects/{project}';path='chapters/story/draft.txt'
        root=app.state.registry.workspace(project).root
        protected={str(p.relative_to(root)):p.read_bytes() for folder in ['settings','characters','state','knowledge'] for p in (root/folder).rglob('*') if p.is_file()}
        start=get_json(client,base+'/experience/focus-boundary')
        doc=get_json(client,base+'/files/content',params={'path':path})
        def save(text):
            nonlocal doc
            response=client.put(base+'/files/content',json={'path':path,'content':text,'etag':doc['etag']})
            assert response.status_code==200,response.text
            doc=response.json()
        save('春风春风。')
        end=get_json(client,base+'/experience/focus-boundary')
        save('春风春风。山谷')
        summary=client.post(base+'/experience/focus-summary',json={'cursor':start['cursor'],'end_cursor':end['cursor']})
        assert summary.status_code==200,summary.text
        assert summary.json()['net_han']==4 and summary.json()['save_count']==1
        catalog=get_json(client,base+'/workbench/replace/catalog')
        assert any(c['path']==path for c in catalog['chapters'])
        response=client.post(base+'/workbench/replace/search',json={'query':'春风','replacement':'秋雨','scope':'book'})
        assert response.status_code==200,response.text
        preview=response.json();assert preview['total_hits']==2
        apply={'preview_id':preview['id'],'all_remaining':True,'expected_count':2,'confirm':False}
        denied=client.post(base+'/workbench/replace/apply-selection',json=apply)
        assert denied.status_code==409,denied.text
        assert get_json(client,base+'/files/content',params={'path':path})['content']=='春风春风。山谷'
        apply['confirm']=True
        receipt=client.post(base+'/workbench/replace/apply-selection',json=apply)
        assert receipt.status_code==200,receipt.text
        result=receipt.json();assert result['status']=='APPLIED' and result['replaced']==2
        assert get_json(client,base+'/files/content',params={'path':path})['content']=='秋雨秋雨。山谷'
        undone=client.post(base+'/workbench/replace/batches/'+result['batch']['id']+'/undo',json={'confirm':True})
        assert undone.status_code==200,undone.text
        assert undone.json()['status']=='UNDONE'
        assert get_json(client,base+'/files/content',params={'path':path})['content']=='春风春风。山谷'
        assert client.post(base+'/workbench/replace/batches/'+result['batch']['id']+'/undo',json={'confirm':True}).status_code==409
        board=get_json(client,base+'/workbench/clue-board')
        assert board['clues']==[]
        changed=client.put(base+'/workbench/clue-board',json={'etag':board['etag'],'threshold':25})
        assert changed.status_code==200,changed.text
        assert changed.json()['threshold']==25
        invalid=client.put(base+'/workbench/clue-board',json={'etag':changed.json()['etag'],'clue_id':'not-in-this-project','tracking_status':'recovered'})
        assert invalid.status_code in {404,422},invalid.text
        assert all((root/name).read_bytes()==content for name,content in protected.items())
        assert (root/'metadata/studio/clue-board.json').exists()
    finally:
        if client:client.close()
        writing_metrics.observer=previous


def test_batch_tracking_and_restored_previews_through_real_routes(tmp_path, monkeypatch):
    """Real route/auth/registry wiring; no UI transport or solver mocks."""
    import yaml
    shutil.copytree(ENGINE/'engine',tmp_path/'engine')
    shutil.copytree(ENGINE/'templates',tmp_path/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'isolated-data'))
    previous=writing_metrics.observer
    client=None
    try:
        client,app,_=local_client(tmp_path)
        response=client.post('/api/drafts',json={'input':{'title':'Isolated tool controls','premise':'Public fictional fixture only.','writing':{'form':'short'}}})
        assert response.status_code==201,response.text
        d=response.json()
        response=client.post('/api/projects',json={'draft_id':d['id'],'version':d['version'],'confirm':True})
        assert response.status_code==201,response.text
        project=response.json()['id'];base=f'/api/projects/{project}'
        root=app.state.registry.workspace(project).root
        source=root/'state/foreshadowing.yaml'
        source.write_text(yaml.safe_dump({'foreshadowing':{'fixture_a':{'title':'Fictional key','status':'OPEN','introduced_chapter':None},'fixture_b':{'title':'Fictional bell','status':'OPEN','introduced_chapter':None}}}),encoding='utf8')
        protected={str(p.relative_to(root)):p.read_bytes() for folder in ['settings','characters','state','knowledge','chapters'] for p in (root/folder).rglob('*') if p.is_file()}
        board=get_json(client,base+'/workbench/clue-board')
        assert {c['id'] for c in board['clues']}=={'fixture_a','fixture_b'}
        body={'etag':board['etag'],'confirm':False,'updates':[{'clue_id':'fixture_a','note':'Author note A'},{'clue_id':'fixture_b','tracking_status':'partial','note':'Author note B'}]}
        before={str(p.relative_to(root)):p.read_bytes() for folder in ['metadata/studio','history/revisions'] for p in (root/folder).rglob('*') if p.is_file()}
        denied=client.post(base+'/workbench/clue-board/batch',json=body)
        assert denied.status_code==422,denied.text  # Schema rejects missing author approval before dispatch.
        invalid={**body,'confirm':True,'updates':[body['updates'][0],{'clue_id':'foreign-project-clue','note':'Must not write'}]}
        denied=client.post(base+'/workbench/clue-board/batch',json=invalid)
        assert denied.status_code in {404,422},denied.text
        assert {str(p.relative_to(root)):p.read_bytes() for folder in ['metadata/studio','history/revisions'] for p in (root/folder).rglob('*') if p.is_file()}==before
        body['confirm']=True
        response=client.post(base+'/workbench/clue-board/batch',json=body)
        assert response.status_code==200,response.text
        result=response.json()
        assert result['batch_summary']=={'updated':2,'clue_ids':['fixture_a','fixture_b']}
        assert next(c for c in result['clues'] if c['id']=='fixture_a')['note']=='Author note A'
        assert next(c for c in result['clues'] if c['id']=='fixture_b')['tracking_status']=='partial'
        assert next(c for c in result['clues'] if c['id']=='fixture_b')['evidenced_status']=='planned'
        assert all((root/name).read_bytes()==content for name,content in protected.items())
        assert client.post(base+'/workbench/clue-board/batch',json=body).status_code==409
        # Restoring an existing preview is a bounded read with source validation.
        path='chapters/story/draft.txt'
        doc=get_json(client,base+'/files/content',params={'path':path})
        response=client.put(base+'/files/content',json={'path':path,'content':'春风。','etag':doc['etag']})
        assert response.status_code==200,response.text
        doc=response.json()
        response=client.post(base+'/workbench/replace/search',json={'query':'春风','replacement':'秋雨','scope':'book'})
        assert response.status_code==200,response.text
        preview=response.json();assert preview['total_hits']==1
        route=base+'/workbench/replace/previews/'+preview['id']
        restored=get_json(client,route,params={'revalidate':True})
        assert restored['validation']['status']=='VALID' and restored['can_apply']
        response=client.put(base+'/files/content',json={'path':path,'content':'春风已经变化。','etag':doc['etag']})
        assert response.status_code==200,response.text
        before={str(p.relative_to(root)):p.read_bytes() for folder in ['chapters','metadata/studio/replacement'] for p in (root/folder).rglob('*') if p.is_file()}
        stale=get_json(client,route,params={'revalidate':True})
        assert stale['validation']['status']=='STALE' and stale['validation']['reason']=='DOCUMENT_CHANGED' and not stale['can_apply']
        assert get_json(client,base+'/files/content',params={'path':path})['content']=='春风已经变化。'
        assert {str(p.relative_to(root)):p.read_bytes() for folder in ['chapters','metadata/studio/replacement'] for p in (root/folder).rglob('*') if p.is_file()}==before
    finally:
        if client:client.close()
        writing_metrics.observer=previous
