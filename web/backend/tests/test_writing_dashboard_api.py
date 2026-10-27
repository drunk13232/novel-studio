"""Full local HTTP-handler save flow and restart persistence, with no model calls."""
import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app import writing_metrics
from app.config import Settings
from app.main import create_app


ENGINE=Path(__file__).resolve().parents[3]


def local_client(workspace):
    app=create_app(Settings(workspace=workspace));app.state.testing=True
    client=TestClient(app)
    session=client.get('/api/session')
    assert session.status_code==200,session.text
    token=session.json()['request_token'];client.headers['X-Novel-Request']=token
    return client,app,token


def get_json(client,url,**kwargs):
    response=client.get(url,**kwargs)
    assert response.status_code==200,response.text
    return response.json()


def test_short_manuscript_dashboard_shelf_and_restart_persistence(tmp_path,monkeypatch):
    # Copy only the public initialization templates, never any development/user project.
    shutil.copytree(ENGINE/'engine',tmp_path/'engine')
    shutil.copytree(ENGINE/'templates',tmp_path/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'isolated-app-data'))
    old_observer=writing_metrics.observer
    clients=[]
    try:
        client,app,token=local_client(tmp_path);clients.append(client)
        assert app.state.registry.root.resolve().is_relative_to(tmp_path.resolve())
        assert app.state.data_center.settings_path.resolve().is_relative_to(tmp_path.resolve())
        draft=client.post('/api/drafts',json={'input':{'title':'本地码字检查',
            'premise':'仅用于隔离保存检查。','writing':{'form':'short','target_characters':100}}})
        assert draft.status_code==201,draft.text
        value=draft.json()
        created=client.post('/api/projects',json={'draft_id':value['id'],'version':value['version'],'confirm':True})
        assert created.status_code==201,created.text
        project=created.json()['id'];base=f'/api/projects/{project}'
        manuscript='chapters/story/draft.txt'
        stats_file=app.state.registry.workspace(project).root/'metadata/studio/writing.json'
        # A brand-new project can open all dashboard surfaces without fabricating history.
        empty=get_json(client,base+'/experience/statistics')
        assert empty['today']==0 and empty['total_han']==0 and empty['quality']['recorded_saves']==0
        assert not stats_file.exists()
        doc=get_json(client,base+'/files/content',params={'path':manuscript})
        assert doc['content']==''

        def save(text,etag):
            response=client.put(base+'/files/content',json={'path':manuscript,'content':text,'etag':etag})
            assert response.status_code==200,response.text
            return response.json()

        doc=save('春风吹过山谷。',doc['etag'])  # Exactly six Chinese characters.
        doc=save(doc['content'],doc['etag'])  # Repeated save contributes no new event.
        doc=save('春风。',doc['etag'])  # Remove four; observed net contribution is now +2.
        goals={'daily':10,'weekly':30,'volume':0,'book':100,'volume_id':''}
        goal_response=client.put(base+'/experience/goals',json=goals)
        assert goal_response.status_code==200,goal_response.text
        progress=get_json(client,base+'/experience/writing-progress')
        day=progress['date'];note='今天删去四字，保留两字。'
        note_response=client.put(base+'/experience/daily-note',json={'day':day,'text':note})
        assert note_response.status_code==200,note_response.text
        invalid=client.put(base+'/experience/daily-note',json={'day':'','text':'不可保存'})
        assert invalid.status_code==422,invalid.text

        stored=stats_file.read_bytes();events=json.loads(stored)['events']
        assert [event['han'] for event in events]==[6,-4]
        assert all(event['source']=='MANUAL' and event['method']=='NET_SAVE_DIFF' for event in events)

        def check_views(active):
            stats=get_json(active,base+'/experience/statistics')
            compact=get_json(active,base+'/experience/writing-progress')
            shelf=get_json(active,'/api/studio/library')
            row=next(item for item in shelf['projects'] if item['id']==project)
            assert stats['today']==compact['today']==row['writing_progress']['today']==2
            assert stats['total_han']==row['han']==2 and stats['quality']['recorded_saves']==2
            assert stats['goals']==goals and compact['daily_goal']==row['writing_progress']['daily_goal']==10
            assert stats['notes'][day]==note
            assert next(item for item in stats['calendar']['days'] if item['date']==day)['note']==note
            assert stats['sources']['manual']['net_han']==2
            assert stats['sources']['manual']['added_han']==6 and stats['sources']['manual']['deleted_han']==4
            assert stats['sources']['ai']['net_han']==0
            assert stats['streaks']['current']==compact['current_streak']==row['writing_progress']['current_streak']==1
            assert stats_file.read_bytes()==stored  # GET surfaces never rewrite the event store.
            return stats

        first=check_views(client)
        client.close()
        restarted,new_app,new_token=local_client(tmp_path);clients.append(restarted)
        assert new_token!=token  # A new backend instance requires its own local mutation token.
        assert new_app.state.registry.workspace(project).root==app.state.registry.workspace(project).root
        restored=check_views(restarted)
        assert restored['today']==first['today'] and restored['goals']==first['goals']
        assert get_json(restarted,base+'/files/content',params={'path':manuscript})['content']=='春风。'
        assert json.loads(stats_file.read_bytes())['events']==events
    finally:
        for client in clients:client.close()
        writing_metrics.observer=old_observer
