"""Isolated annual event aggregation and ritual metadata; no real author data."""
import copy,json
from datetime import date
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import writing_metrics as wm
from app.errors import ConsoleError
from app.library.storage import write

@pytest.fixture
def service(tmp_path,monkeypatch):
    monkeypatch.setattr(wm,'_today',lambda:date(2026,10,25))
    # Freeze save timestamps too: otherwise today's real clock looks like a future event.
    monkeypatch.setattr(wm,'now',lambda:'2026-10-25T04:00:00Z')
    root=tmp_path/'projects'/'isolated';root.mkdir(parents=True)
    def workspace(p):
        if p!='isolated':raise ConsoleError('No such project',404)
        return SimpleNamespace(root=root)
    registry=SimpleNamespace(root=root.parent,workspace=workspace,get=lambda p:{'writing':{'form':'novel'}})
    catalog={'chapters':[{'id':'one','number':1,'title':'第一章','volume':'v1'},
                         {'id':'two','number':2,'title':'第二章','volume':'v2'}],
             'volumes':[{'id':'v1','title':'第一卷'},{'id':'v2','title':'第二卷'}]}
    def books(p,**options):
        assert options=={'include_auxiliary':False,'include_text_counts':False}
        return catalog
    return wm.Metrics(SimpleNamespace(registry=registry,catalog=books)),root,catalog

def event(at,han,source='MANUAL',path='chapters/chapter-1/draft.txt',**extra):
    return {'id':at+str(han),'at':at,'han':han,'characters':han,'source':source,'path':path,'method':'NET_SAVE_DIFF',**extra}

def store(service,events,**extra):
    state={'events':events,'snapshots':{},'notes':{},'goals':{},**extra};write(service.path('isolated'),state);return state

def test_empty_annual_and_ritual_open_do_not_create_files(service):
    metrics,root,_=service;before=list(root.rglob('*'))
    report=metrics.annual('isolated',2026);ritual=metrics.ritual('isolated')
    assert not report['has_saved_events'] and report['totals']['net_han']==0
    assert len(report['calendar'])==298 and len(report['months'])==12 and len(report['hourly'])==24
    assert report['streaks']['best_day'] is None and report['peak_hour'] is None
    assert report['most_edited']==[] and report['volumes']==[]
    assert ritual['settings']['enabled'] is False and ritual['settings']['skip_remembered'] is False
    assert len(ritual['settings']['steps'])==3
    assert list(root.rglob('*'))==before

def test_year_boundaries_timezone_sources_and_historical_estimates(service):
    metrics,_,_=service
    rows=[event('2024-12-31T15:59:59Z',1),event('2024-12-31T16:00:00Z',7),
          event('2025-01-02T12:00:00+08:00',-2),event('2025-01-02T13:00:00+08:00',4,'AI_ACCEPT'),
          event('2025-02-01T13:00:00+08:00',6,'RESTORE'),event('2025-02-01T13:00:00+08:00',-1,'OTHER'),
          event('2025-12-31T15:59:59Z',3),event('2025-12-31T16:00:00Z',100),
          event('2025-06-01T00:00:00Z',999,method='OBSERVED_EXTERNAL_ESTIMATE'),
          event('2025-06-02T00:00:00Z',999,method='OTHER'),event('invalid',999),
          event('2027-01-01T00:00:00Z',999)]
    store(metrics,rows);before=metrics.path('isolated').read_bytes();report=metrics.annual('isolated',2025)
    assert report['totals']=={'net_han':17,'manual_han':8,'ai_han':4,'restore_han':6,'unknown_han':-1,'save_count':6}
    assert report['hourly'][0]['han']==7 and report['hourly'][23]['han']==3
    assert report['streaks']['longest']==2 and report['streaks']['writing_days']==4
    assert report['streak_scope']=='WITHIN_SELECTED_YEAR'
    assert report['sources']['manual']['added_han']==10 and report['sources']['manual']['deleted_han']==2
    assert report['sources']['restore']['added_han']==6 and report['sources']['unknown']['net_han']==-1
    assert report['quality']['historical_exclusions']['excluded_estimates']==1
    assert report['quality']['historical_exclusions']['excluded_invalid_events']==2
    assert report['quality']['historical_exclusions']['excluded_future_events']==1
    assert len(report['calendar'])==365 and report['available_years']==[2026,2025,2024]
    assert metrics.path('isolated').read_bytes()==before

def test_leap_year_negative_net_and_zero_do_not_invent_writing_days(service):
    metrics,_,_=service
    store(metrics,[event('2024-02-28T12:00:00+08:00',5),event('2024-02-29T12:00:00+08:00',-8),event('2024-02-29T13:00:00+08:00',8),event('2024-03-01T12:00:00+08:00',-1)])
    report=metrics.annual('isolated',2024)
    assert len(report['calendar'])==366 and report['streaks']['writing_days']==1
    assert report['streaks']['longest']==1 and report['streaks']['best_day']=={'date':'2024-02-28','han':5}
    assert report['totals']['net_han']==4

def test_current_catalog_mapping_is_not_historical_completion_or_cross_project(service):
    metrics,_,_=service
    store(metrics,[event('2025-02-01T12:00:00+08:00',4),event('2025-02-01T13:00:00+08:00',2,path='chapters/chapter-1/manual-copy.md'),
                   event('2025-02-02T12:00:00+08:00',8,path='chapters/chapter-2/draft.txt'),
                   event('2025-02-03T12:00:00+08:00',3,path='chapters/chapter-999/draft.txt')])
    report=metrics.annual('isolated',2025)
    assert report['most_edited'][0]['id']=='one' and report['most_edited'][0]['save_count']==2
    assert report['edited_chapters']==2 and len(report['volumes'])==2
    assert report['volumes'][0]['net_han']==6 and report['unassigned']=={'save_count':1,'net_han':3}
    assert 'completed' not in json.dumps(report) and 'chapters/' not in json.dumps(report)
    metrics.registry.get=lambda p:{'writing':{'form':'anthology'}}
    metrics.books.catalog=lambda *a,**k:pytest.fail('An anthology annual report must not scan other books')
    assert metrics.annual('isolated',2025)['unassigned']['save_count']==4

@pytest.mark.parametrize('year',[0,1899,2027,9999])
def test_invalid_year(service,year):
    with pytest.raises(ConsoleError) as caught:service[0].annual('isolated',year)
    assert caught.value.status==422

def test_ritual_crud_order_restart_and_etag_do_not_rewrite_event_store(service):
    metrics,root,_=service
    store(metrics,[event('2026-10-25T12:00:00+08:00',4)],goals={'daily':300,'weekly':1500},notes={'2026-10-25':'原日记'})
    initial=metrics.ritual('isolated');before=metrics.path('isolated').read_bytes()
    prefs=initial['settings'];prefs['enabled']=True;prefs['steps']=[prefs['steps'][2],{'id':'custom-1','kind':'checklist','phase':'start','title':'看一眼上一段','enabled':True},prefs['steps'][0]]
    updated=metrics.save_ritual('isolated',wm.RitualUpdate(etag=initial['etag'],settings=prefs))
    assert updated['etag']!=initial['etag'] and updated['goals']['weekly']==1500 and updated['note']=='原日记'
    assert [item['id'] for item in updated['settings']['steps']]==['reflection','custom-1','daily-goal']
    restarted=wm.Metrics(metrics.books)
    assert restarted.ritual('isolated')['settings']==prefs
    assert metrics.path('isolated').read_bytes()==before
    with pytest.raises(ConsoleError) as caught:metrics.save_ritual('isolated',wm.RitualUpdate(etag=initial['etag'],settings=prefs))
    assert caught.value.status==409
    assert metrics.path('isolated').read_bytes()==before
    with pytest.raises(ConsoleError):metrics.ritual('other')

def test_ritual_reflection_appends_to_existing_journal_without_events(service):
    metrics,_,_=service
    state=store(metrics,[event('2026-10-25T12:00:00+08:00',4)],notes={'2026-10-25':'已有日记'})
    result=metrics.ritual_reflection('isolated',wm.RitualReflection(day='2026-10-25',expected_note='已有日记',text='今天理顺了一场对白。'))
    assert result['note']=='已有日记\n今天理顺了一场对白。'
    current=metrics.state('isolated');assert current['events']==state['events']
    assert current['notes']['2026-10-25']==result['note']
    with pytest.raises(ConsoleError) as caught:metrics.ritual_reflection('isolated',wm.RitualReflection(day='2026-10-25',expected_note='已有日记',text='迟到提交'))
    assert caught.value.status==409 and metrics.state('isolated')['notes']['2026-10-25']==result['note']
    with pytest.raises(ConsoleError):metrics.ritual_reflection('isolated',wm.RitualReflection(day='2026-02-30',text='无效日期'))
    with pytest.raises(ConsoleError):metrics.ritual_reflection('isolated',wm.RitualReflection(day='2026-10-25',expected_note=result['note'],text='   '))

@pytest.mark.parametrize('steps',[[{'id':'same','kind':'checklist'},{'id':'same','kind':'goal'}],[{'id':'a','kind':'shell'}],[{'id':'../bad'}]])
def test_ritual_declarative_schema_rejects_unsafe_and_duplicate_steps(steps):
    with pytest.raises(ValueError):wm.RitualPreferences(steps=steps)

def test_version_switch_updates_snapshot_without_polluting_saved_deltas(service):
    metrics,root,_=service;path='chapters/chapter-1/draft.txt'
    metrics.saved(root,path,'','春风','MANUAL');before=copy.deepcopy(metrics.state('isolated')['events'])
    metrics.saved(root,path,'春风','春风吹过山谷','VERSION_SWITCH')
    state=metrics.state('isolated')
    assert state['events']==before and state['snapshots'][path]['han']==6
    assert metrics.progress('isolated')['today']==2
    metrics.saved(root,path,'春风吹过山谷','春风吹过山谷里','MANUAL')
    assert metrics.progress('isolated')['today']==3

def test_new_routes_work_in_existing_router_only(service):
    metrics,_,_=service;app=FastAPI();app.include_router(wm.experience_routes(metrics,None))
    with TestClient(app) as client:
        assert client.get('/api/projects/isolated/experience/annual?year=2025').status_code==200
        assert client.get('/api/projects/isolated/experience/annual?year=bad').status_code==422
        initial=client.get('/api/projects/isolated/experience/ritual').json()
        response=client.put('/api/projects/isolated/experience/ritual',json={'etag':initial['etag'],'settings':{**initial['settings'],'enabled':True}})
        assert response.status_code==200 and response.json()['settings']['enabled']
        assert client.put('/api/projects/isolated/experience/ritual/reflection',json={'day':'2026-10-25','text':'完成一段。','expected_note':''}).status_code==200


def test_real_application_local_mutations_and_restart(tmp_path,monkeypatch):
    import shutil
    from pathlib import Path
    from app.config import Settings
    from app.main import create_app
    engine=Path(__file__).resolve().parents[3]
    shutil.copytree(engine/'engine',tmp_path/'engine');shutil.copytree(engine/'templates',tmp_path/'templates')
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'app-data'))
    observer=wm.observer
    try:
        app=create_app(Settings(workspace=tmp_path));app.state.testing=True
        with TestClient(app) as client:
            client.headers['X-Novel-Request']=client.get('/api/session').json()['request_token']
            draft=client.post('/api/drafts',json={'input':{'title':'隔离仪式测试','premise':'仅作本地功能测试','writing':{'form':'short'}}}).json()
            response=client.post('/api/projects',json={'draft_id':draft['id'],'version':draft['version'],'confirm':True});assert response.status_code==201,response.text
            project=response.json()['id'];base=f'/api/projects/{project}/experience'
            initial=client.get(base+'/ritual').json();assert not initial['settings']['enabled']
            saved=client.put(base+'/ritual',json={'etag':initial['etag'],'settings':{**initial['settings'],'enabled':True}})
            assert saved.status_code==200,saved.text
            result=client.put(base+'/ritual/reflection',json={'day':initial['date'],'text':'今天完成了一个想法。','expected_note':''})
            assert result.status_code==200,result.text
            year=int(initial['date'][:4]);annual=client.get(base+f'/annual?year={year}')
            assert annual.status_code==200,annual.text
            assert annual.json()['totals']['save_count']==0 and annual.json()['most_edited']==[]
            state=app.state.registry.workspace(project).root/'metadata/studio/writing.json';before=state.read_bytes()
        restarted=create_app(Settings(workspace=tmp_path));restarted.state.testing=True
        with TestClient(restarted) as client:
            data=client.get(base+'/ritual').json()
            assert data['settings']['enabled'] and data['note']=='今天完成了一个想法。'
            assert client.get(base+f'/annual?year={year}').status_code==200
            assert state.read_bytes()==before
    finally:wm.observer=observer


def test_ritual_goal_updates_only_daily_and_refuses_a_stale_daily_value(service):
    metrics,_,_=service
    state=store(metrics,[event('2026-10-25T12:00:00+08:00',4)],goals={'daily':100,'weekly':700,'volume':2000,'book':9000,'volume_id':'v1','legacy_note':'preserve'})
    result=metrics.ritual_daily_goal('isolated',wm.RitualDailyGoal(daily=600,expected_daily=100))
    assert result['saved'] and result['goals']=={**state['goals'],'daily':600}
    updated=metrics.state('isolated');assert updated['events']==state['events'] and updated['snapshots']==state['snapshots']
    before=metrics.path('isolated').read_bytes()
    with pytest.raises(ConsoleError) as caught:metrics.ritual_daily_goal('isolated',wm.RitualDailyGoal(daily=800,expected_daily=100))
    assert caught.value.code=='RITUAL_GOAL_CHANGED' and caught.value.status==409
    assert metrics.path('isolated').read_bytes()==before

@pytest.mark.parametrize('daily,expected',[(-1,0),(1000001,0),(1,-1),(1,1000001)])
def test_ritual_goal_schema_rejects_invalid_bounds(daily,expected):
    with pytest.raises(ValueError):wm.RitualDailyGoal(daily=daily,expected_daily=expected)
