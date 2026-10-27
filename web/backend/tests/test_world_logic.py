import copy, json
from pathlib import Path
import pytest
from app.world_logic.engine import run
from app.world_logic.models import validate
from app.world_logic.service import parse
RESOURCES=Path(__file__).resolve().parents[1]/'app/world_logic/resources/templates'
def example(name):
    d=json.loads((RESOURCES/(name+'.json')).read_text('utf8'))
    for a in d['assumptions']:a['accepted']=True
    return d

def test_unsat_core_and_sat_are_distinct():
    d=example('custom-constraint');r=run(d)
    assert r['status']=='PASS' and r['solver_result']['status']=='SAT'
    d['constraints'].append({'id':'opposite','name':'反向条件','expression':'energy < cost','meaning':'与最低能耗冲突','source_ids':[]})
    r=run(d);assert r['status']=='FAIL' and r['solver_result']['status']=='UNSAT'
    assert {'magic_cost','opposite'}<={x['id'] for x in r['solver_result']['unsat_core']}

def test_unknown_and_bad_units_never_pass():
    d=example('travel');d['inputs'][0]['value']=None;assert run(d)['status']=='INCONCLUSIVE'
    d=example('travel');d['outputs'][0]['expression']='distance + available';assert run(d)['status']=='FAIL'

def test_explicit_dependency_cycle():
    d=example('event-order');d['dependencies'].append({'id':'cycle','before':'meeting','after':'departure','meaning':'依赖环','source_ids':[]})
    r=run(d);assert r['status']=='FAIL' and len(r['dependency_graph']['conflicting_dependencies'])==3

def test_author_gravity_not_earth_constant():
    r=run(example('physics-units'));assert [v['value'] for v in r['outputs']]==[32,160]

def test_sweep_preserves_baseline():
    d=example('resources');old=copy.deepcopy(d);r=run(d)
    assert d==old and len(r['sensitivity']['samples'])==8
    assert any(x['status']=='FAIL' for x in r['sensitivity']['samples'])

@pytest.mark.parametrize('expression',['__import__(1)','distance.__class__','2 ** 999999','[x for x in distance]','not distance'])
def test_import_cannot_execute_code(expression):
    d=example('travel');d['outputs'][0]['expression']=expression
    if expression=='not distance':assert run(d)['status']!='PASS'
    else:
        with pytest.raises(Exception):validate(d)

@pytest.mark.parametrize('text',['!!python/object/apply:os.system [echo attack]','a: &a [*a]'])
def test_yaml_code_and_aliases_are_rejected(text):
    with pytest.raises(Exception):parse(text)


def test_unselected_sources_never_enter_ai_context():
    from app.world_logic.service import bounded_experiment_context
    d=example('travel');d['source_references']=[{'id':'hidden_source','type':'entity','target_id':'entity_hidden','name':'作者秘密','basis':'AUTHOR_CONFIRMED','sha256':'','excerpt':'PRIVATE_SOURCE_SENTINEL'}]
    d['inputs'][0]['source_ids']=['hidden_source'];old=copy.deepcopy(d)
    context=bounded_experiment_context(d,[])
    assert 'PRIVATE_SOURCE_SENTINEL' not in json.dumps(context)
    assert not context['inputs'][0]['source_ids'] and d==old

def test_default_template_export_removes_private_names_and_values():
    from app.world_logic.service import public_definition
    d=example('travel');d['name']='PRIVATE_NAME_SENTINEL';d['inputs'][0]['name']='PRIVATE_CHARACTER_SENTINEL';d['inputs'][0]['note']='PRIVATE_NOTE_SENTINEL'
    exported=public_definition(d)
    assert 'PRIVATE_' not in json.dumps(exported)
    assert all(v['value'] is None for v in exported['inputs'])
    validate(exported)
