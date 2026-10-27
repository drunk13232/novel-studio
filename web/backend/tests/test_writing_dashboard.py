"""Local deterministic save-delta aggregation; no AI or real user projects."""
import copy
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import writing_metrics as wm
from app.library.storage import write


TODAY=date(2026,10,24)


def event(day,han,source='MANUAL',hour=12,**extra):
    return {'id':f'{day}-{hour}-{han}-{source}','at':f'{day}T{hour:02}:00:00+08:00',
            'path':'chapters/chapter-1/draft.txt','han':han,'characters':han,'source':source,
            'method':'NET_SAVE_DIFF',**extra}


@pytest.fixture
def metrics(tmp_path,monkeypatch):
    monkeypatch.setattr(wm,'_today',lambda:TODAY)
    root=tmp_path/'projects'/'isolated';root.mkdir(parents=True)
    manifest={'writing':{'target_characters':1000}}
    registry=SimpleNamespace(root=root.parent,engine=tmp_path,
                             workspace=lambda p:SimpleNamespace(root=root),get=lambda p:manifest)
    catalog={'writing':manifest['writing'],'chapters':[
        {'id':'one','title':'测试章','number':1,'volume':'v1','status':'DRAFT',
         'draft':'chapters/chapter-1/draft.txt','final':None,'han':300,'characters':350}],
         'volumes':[{'id':'v1','title':'测试卷'}]}
    service=wm.Metrics(SimpleNamespace(registry=registry,catalog=lambda p,**options:catalog))
    return service,root,catalog


def put_state(service,events,**values):
    state={'started_at':'2026-01-01T00:00:00+00:00','snapshots':{},'events':events,'goals':{},'notes':{}}
    state.update(values);write(service.path('isolated'),state)
    return state


def test_empty_project_summary_and_progress_are_read_only(metrics):
    service,root,catalog=metrics;catalog['chapters']=[];catalog['volumes']=[]
    before=list(root.rglob('*'));value=service.summary('isolated');mini=service.progress('isolated')
    assert value['today']==value['week']==value['month']==value['total_han']==0
    assert len(value['calendar']['days'])==365 and len(value['hourly'])==24
    assert value['streaks']=={'current':0,'longest':0,'best_day':None,'writing_days':0,'as_of':None}
    assert value['pace']['status']=='NO_PACE' and value['pace']['estimated_date'] is None
    assert value['sources']['manual_share'] is None and not mini['has_saved_events']
    assert list(root.rglob('*'))==before and not service.path('isolated').exists()


def test_real_save_deltas_delete_and_duplicate_do_not_inflate(metrics):
    service,root,_=metrics;path='chapters/chapter-1/draft.txt'
    service.saved(root,path,'','# 第一章\n天地玄黄','MANUAL')
    service.saved(root,path,'# 第一章\n天地玄黄','# 第一章\n天地玄黄','MANUAL')
    service.saved(root,path,'# 第一章\n天地玄黄','# 第一章\n天地','MANUAL')
    service.saved(root,path,'# 第一章\n天地','# 第一章\n天地宇宙','AI_ACCEPT')
    events=service.state('isolated')['events']
    assert [e['han'] for e in events]==[4,-2,2]
    assert all(e['method']=='NET_SAVE_DIFF' for e in events)
    snapshot=service.path('isolated').read_bytes();service.summary('isolated')
    assert service.path('isolated').read_bytes()==snapshot


def test_external_edit_saved_back_to_previous_snapshot_still_records_real_diff(metrics):
    service,root,_=metrics;path='chapters/chapter-1/draft.txt'
    service.saved(root,path,'','天地玄黄','MANUAL')
    # A disk editor shortened the manuscript. Saving back must count the actual +2,
    # even though the resulting hash matches the previous in-app snapshot.
    service.saved(root,path,'天地','天地玄黄','MANUAL')
    assert [e['han'] for e in service.state('isolated')['events']]==[4,2]


@pytest.mark.parametrize('path',['chapters/chapter-1/manual-candidate-1.txt','chapters/chapter-1/manual-candidate-1.md',
                                'chapters/story/manual-candidate-1.txt','chapters/story/manual-candidate-1.md'])
def test_revision_copy_is_not_counted_but_author_save_records_only_delta(metrics,monkeypatch,path):
    from app.library.storage import write_bytes
    from app.projects.service import NovelWorkspace
    service,root,_=metrics;monkeypatch.setattr(wm,'observer',service.saved)
    original='天地玄黄';write_bytes(root/path,original.encode('utf8'))
    # The existing revision/candidate creation path writes a copy without notify_saved.
    assert not service.path('isolated').exists()
    workspace=NovelWorkspace(root);doc=workspace.content(path)
    result=workspace.save(path,original+'宇宙',doc['etag'])
    assert result['content']=='天地玄黄宇宙'
    assert [(e['path'],e['han'],e['source']) for e in service.state('isolated')['events']]==[(path,2,'MANUAL')]
    workspace.save(path,result['content'],result['etag'])
    assert len(service.state('isolated')['events'])==1


@pytest.mark.parametrize('day',['',None,'2026-02-30','2026-2-03','not-a-date'])
def test_invalid_daily_note_dates_return_422_without_writing(metrics,day):
    from app.errors import ConsoleError
    service,_,_=metrics
    with pytest.raises(ConsoleError) as failure:service.note('isolated',day,'不应写入')
    assert failure.value.status==422 and not service.path('isolated').exists()


def test_timezone_hourly_sources_and_legacy_estimates(metrics):
    service,_,_=metrics
    rows=[event('2026-10-24',12,hour=9),event('2026-10-24',-4,hour=9),
          event('2026-10-24',3,'AI_ACCEPT',hour=10),event('2026-10-24',5,'AI_ACCEPTED',hour=11),
          event('2026-10-24',-1,'RESTORE',hour=12),event('2026-10-24',2,'OTHER',hour=13),
          event('2026-10-24',100,method='OBSERVED_EXTERNAL_ESTIMATE'),
          event('2026-10-23',7,at='2026-10-23T17:00:00Z')]
    put_state(service,rows)
    value=service.summary('isolated')
    assert value['today']==24 and value['hourly'][1]['han']==7 and value['hourly'][9]['han']==8
    assert value['sources']['manual']=={'net_han':15,'added_han':19,'deleted_han':4,'save_count':3}
    assert value['sources']['ai']['net_han']==8 and value['sources']['restore']['net_han']==-1
    assert value['sources']['unknown']['net_han']==2
    assert value['sources']['manual_share']==pytest.approx(19/27)
    assert value['sources']['ai_share']==pytest.approx(8/27)
    assert value['quality']['excluded_estimates']==1 and value['quality']['recorded_saves']==7


def test_heatmap_notes_zero_and_negative_days(metrics):
    service,_,_=metrics
    put_state(service,[event('2026-10-21',400),event('2026-10-22',-30),event('2026-10-23',0)],
              notes={'2026-10-22':'修掉重复段落。','2024-01-01':'保留旧日记'})
    value=service.summary('isolated');days={d['date']:d for d in value['calendar']['days']}
    assert days['2026-10-22']['level']==-1 and days['2026-10-22']['note']=='修掉重复段落。'
    assert days['2026-10-23']['level']==0 and days['2026-10-21']['level']==1
    assert days['2026-10-24']['han']==0 and value['notes']['2024-01-01']=='保留旧日记'
    assert all('events' not in row for row in days.values())


def test_streaks_use_daily_net_not_positive_individual_saves(metrics):
    service,_,_=metrics
    rows=[event('2026-10-18',4),event('2026-10-19',5),event('2026-10-20',6),
          event('2026-10-21',30),event('2026-10-21',-31),event('2026-10-22',7),event('2026-10-23',8)]
    put_state(service,rows);value=service.summary('isolated')['streaks']
    assert value['current']==2 and value['longest']==3 and value['writing_days']==5
    assert value['best_day']=={'date':'2026-10-23','han':8} and value['as_of']=='2026-10-23'
    put_state(service,[*rows,event('2026-10-24',-1)])
    assert service.summary('isolated')['streaks']['current']==0
    put_state(service,[*rows,event('2026-10-24',10)])
    assert service.summary('isolated')['streaks']['current']==3


def test_forecast_uses_seven_calendar_days_and_book_target_fallback(metrics):
    service,_,_=metrics
    put_state(service,[event('2026-10-18',350),event('2026-10-24',-70)])
    value=service.summary('isolated')
    assert value['pace']['daily_average']==40 and value['pace']['remaining']==700
    assert value['pace']['days_remaining']==18 and value['pace']['estimated_date']=='2026-11-11'
    put_state(service,[event('2026-10-18',350),event('2026-10-24',-70)],goals={'book':500})
    assert service.summary('isolated')['pace']['estimated_date']=='2026-10-29'
    put_state(service,[event('2026-10-18',-350)])
    assert service.summary('isolated')['pace']['status']=='NO_PACE'
    assert service.summary('isolated')['pace']['estimated_date'] is None


def test_last_week_is_previous_monday_through_sunday(metrics):
    service,_,_=metrics
    put_state(service,[event('2026-10-11',99),event('2026-10-12',20),event('2026-10-13',-3),
                       event('2026-10-18',30),event('2026-10-19',200)])
    value=service.summary('isolated')['last_week']
    assert value=={'start':'2026-10-12','end':'2026-10-18','han':47,'writing_days':2,
                   'best_day':{'date':'2026-10-18','han':30},'save_count':3}


def test_goals_are_correct_and_clamped_without_overwriting_events(metrics):
    service,_,_=metrics
    put_state(service,[event('2026-10-24',50),event('2026-10-23',-20)],
              goals={'daily':25,'weekly':100,'volume':600,'volume_id':'v1','book':1000})
    value=service.summary('isolated')['goal_progress']
    assert value['daily']=={'current':50,'target':25,'ratio':1,'exceeded':True}
    assert value['weekly']['current']==30 and value['weekly']['ratio']==0.3
    assert value['volume']['current']==300 and value['volume']['ratio']==0.5
    assert value['book']['current']==300 and value['book']['ratio']==0.3


def test_old_events_invalid_and_future_data_do_not_crash_or_fabricate(metrics):
    service,_,_=metrics
    old=event('2026-10-24',5);old.pop('method')
    put_state(service,[old,event('2026-10-24',6,at='2026-10-24T01:00:00'),
                       event('2026-10-25',100),{'han':99},None,event('2026-10-24',True),
                       event('2026-10-24',99,method=['script']),event('2026-10-24',2,source=['unknown'])])
    before=service.path('isolated').read_bytes();value=service.summary('isolated')
    assert value['today']==13 and value['quality']['legacy_methodless_saves']==1
    assert value['quality']['excluded_invalid_events']==4 and value['quality']['excluded_future_events']==1
    assert service.path('isolated').read_bytes()==before


def test_last_written_compares_instants_instead_of_iso_string_order(metrics):
    service,_,_=metrics
    put_state(service,[event('2026-10-24',1,at='2026-10-24T02:00:00+08:00'),
                       event('2026-10-23',2,at='2026-10-23T20:00:00+00:00')])
    assert service.summary('isolated')['last_written']=='2026-10-24T04:00:00+08:00'


def test_compact_progress_never_uses_catalog_or_manuscripts(metrics):
    service,_,_=metrics
    put_state(service,[event('2026-10-23',3),event('2026-10-24',5)],goals={'daily':200})
    service.books.catalog=lambda p:(_ for _ in ()).throw(AssertionError('No catalog allowed'))
    value=service.progress('isolated')
    assert value['today']==5 and value['daily_goal']==200 and value['current_streak']==2
    assert value['manual_today']==5 and value['ai_today']==0 and value['has_saved_events']
    pure={'events':[event('2026-10-24',9)],'goals':{'daily':50}}
    before=copy.deepcopy(pure);assert wm.compact_progress(pure,'isolated',TODAY)['today']==9
    assert pure==before


def test_progress_route_is_get_and_project_scoped(metrics):
    service,_,_=metrics;put_state(service,[event('2026-10-24',9)])
    app=FastAPI();app.include_router(wm.experience_routes(service,None));client=TestClient(app)
    response=client.get('/api/projects/isolated/experience/writing-progress')
    assert response.status_code==200 and response.json()['project_id']=='isolated'
    assert response.json()['today']==9


def test_statistics_catalog_does_not_probe_pandoc_or_load_assets(tmp_path):
    from app.book_center import BookCenter
    root=tmp_path/'isolated';folder=root/'chapters/chapter-1';folder.mkdir(parents=True)
    (folder/'draft.txt').write_text('# 第一章\n'+('字'*100),'utf8')
    (folder/'final.txt').write_text('# 第一章\n天地玄黄','utf8')
    workspace=SimpleNamespace(root=root,content=lambda path:{'content':(root/path).read_text('utf8')})
    manifest={'title':'隔离测试','writing':{'form':'novel'}}
    registry=SimpleNamespace(workspace=lambda p:workspace,get=lambda p:manifest)
    planning=SimpleNamespace(rows=lambda p,kind:[] if kind=='volume' else [
        {'id':'one','number':1,'title':'测试章','volume':'','status':'DRAFT','order':1}])
    assets=SimpleNamespace(list=lambda p:(_ for _ in ()).throw(AssertionError('No assets allowed')))
    books=BookCenter(registry,planning,assets,tmp_path/'config')
    books.capabilities=lambda:(_ for _ in ()).throw(AssertionError('No external program probe allowed'))
    value=books.catalog('isolated',include_auxiliary=False)
    assert value['chapters'][0]['han']==4 and value['chapters'][0]['status']=='FINAL'
    assert len(value['chapters'])==1 and value['assets']==[] and value['capabilities']=={}
    # Default export callers retain the auxiliary response and Final preference.
    assets.list=lambda p:[{'id':'public-test-asset'}];books.capabilities=lambda:{'epub_available':False}
    full=books.catalog('isolated')
    assert full['assets']==[{'id':'public-test-asset'}] and full['capabilities']=={'epub_available':False}
    assert full['chapters']==value['chapters']
