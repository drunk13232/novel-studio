import copy,json
from pathlib import Path
import pytest
from app.world_logic.models import validate
from app.world_logic.engine import run
from app.world_logic.service import public_definition
RES=Path(__file__).resolve().parents[1]/'app/world_logic/resources/templates'
def example(name):
 d=json.loads((RES/(name+'.json')).read_text('utf8'))
 for a in d['assumptions']:a['accepted']=True
 return validate(d)
def timed():
 d=example('event-order');ids=[]
 for edge in d['dependencies']:
  for id in [edge['before'],edge['after']]:
   if id not in ids:ids.append(id)
 d['events']=[{'id':id,'name':id,'clock':'gregorian','time':f'2041-04-17T08:{i*10:02}:00+08:00','narrative_order':len(ids)-i} for i,id in enumerate(ids)]
 return validate(d)
def test_feedback_is_not_a_strict_order_conflict():
 d=example('event-order')
 for e in d['dependencies']:e['kind']='causal'
 d['dependencies'].append({'id':'feedback','before':'meeting','after':'departure','kind':'causal','meaning':'明确反馈','source_ids':[]})
 r=run(d);assert r['status']=='PASS' and r['dependency_graph']['causal_feedback_present']
def test_real_story_order_ignores_narrative_order():
 r=run(timed());assert r['status']=='PASS' and all(x['status']=='PASS' for x in r['dependency_graph']['time_results'])
def test_missing_offset_does_not_invent_an_instant():
 d=timed();d['events'][0]['time']='2041-04-17';assert run(d)['status']=='INCONCLUSIVE'
def test_explicit_timezone_comparison():
 d=timed();d['events'][1]['time']='2041-04-17T00:10:00+00:00';assert run(d)['status']=='PASS'
def test_availability_before_acquisition_fails():
 d=timed();d['dependencies'][0]['kind']='availability';d['events'][0]['time']='2041-04-17T08:30:00+08:00'
 r=run(d);assert r['status']=='FAIL' and r['dependency_graph']['time_results'][0]['status']=='FAIL'
def test_fictional_coordinates_are_explicit():
 d=timed()
 for i,e in enumerate(d['events']):e.update(clock='fictional_era',coordinate=i,time='')
 assert run(d)['status']=='PASS'
 d['events'][-1]['clock']='another_era';assert run(d)['status']=='INCONCLUSIVE'
def test_unknown_exception_cannot_pass():
 d=example('event-order');d['inputs'].append({'id':'teleport','name':'传送','kind':'boolean','value':None,'unit':'dimensionless'});d['dependencies'][0]['condition']='not teleport'
 assert run(d)['status']=='INCONCLUSIVE'
def test_declared_fictional_exception_is_used():
 d=timed();d['inputs'].append({'id':'teleport','name':'传送','kind':'boolean','value':True,'unit':'dimensionless'});d['dependencies'][0]['condition']='not teleport';d['events'][0]['time']='2041-04-17T08:50:00+08:00'
 assert run(d)['status']=='PASS'
def test_schedule_capacity_changes_real_result():
 d=example('finite-schedule');before=copy.deepcopy(d);r=run(d);assert r['status']=='FAIL' and r['outputs'][0]['value']==7 and d==before
 d['inputs'][0]['value']=2;r=run(d);assert r['status']=='PASS' and r['outputs'][0]['value']==4 and r['solver_result']['status']=='OPTIMAL'
def test_unknown_schedule_parameter_stays_unknown():
 d=example('finite-schedule');d['inputs'][0]['value']=None;assert run(d)['status']=='INCONCLUSIVE'
def test_schedule_does_not_silently_round_ticks():
 d=example('finite-schedule');d['inputs'][1]['value']=1.5;assert run(d)['status']!='PASS'
def test_declared_magic_balance_and_gravity():
 assert run(example('magic-consumption'))['outputs'][0]['value']==20
 r=run(example('author-gravity'));assert abs(r['outputs'][0]['value']-10**.5)<1e-10 and r['outputs'][1]['value']==100
@pytest.mark.parametrize('bad',["__import__('os')",'duration_A.__class__','lambda: 1'])
def test_schedule_import_cannot_execute_code(bad):
 d=example('finite-schedule');d['schedule']['operations'][0]['duration']=bad
 with pytest.raises(Exception):validate(d)
def test_default_sharing_removes_new_private_metadata():
 d=timed();d['events'][0]['name']='PRIVATE_EVENT_SENTINEL';d['events'][0]['clock']='PRIVATE_CLOCK_SENTINEL';e=public_definition(d);assert 'PRIVATE_' not in json.dumps(e);validate(e)
 d=example('finite-schedule');d['schedule']['operations'][0]['name']='PRIVATE_OPERATION_SENTINEL';d['schedule']['resources'][0]['name']='PRIVATE_RESOURCE_SENTINEL';e=public_definition(d);assert 'PRIVATE_' not in json.dumps(e);validate(e)
