"""Regression checks for confirmed organizer defects; synthetic isolated projects only."""
import copy,json,asyncio
import pytest
from types import SimpleNamespace
from test_writing_assist import service
from app.errors import ConsoleError
from test_data_organization import setup,draft,apply,definition,capture
from app.library.data_organization import Create,Review,Definition,Source,Run

def test_sorting_unknown_field_must_not_call_it_a_missing_record(service):
    s,p,_=setup(service);d=definition();d.records[0].values[0].value_json='null';d.records[0].values[0].basis='UNKNOWN'
    r=draft(s,p,d);apply(s,p,r);v=s.table(p,r['id'],'numbers',sort='population')
    assert v['total']==1 and v['rows'][0]['fields']['population'] is None
    assert v['missing_records']==[], 'A real entity with an unknown value is not a removed entity'

def test_default_name_sort_must_keep_removed_record_warning(service):
    s,p,root=setup(service);r=draft(s,p);a=apply(s,p,r);identifier=a['entities'][0]['id']
    (root/'bible/entities'/(identifier+'.json')).unlink() # Only this fixture's newly created test entity.
    v=s.table(p,r['id'],'numbers',sort='name')
    assert v['total']==0
    assert [e['id'] for e in v['missing_records']]==[identifier], 'Default UI sorting must not erase missing-entity evidence'

def test_successful_retry_clears_previous_failure(service,monkeypatch):
    s,p,_=setup(service);r=draft(s,p);box=capture(s,p,monkeypatch)
    s.run(p,r['id'],Run(etag=r['etag'],confirm_send=True));failed=SimpleNamespace(status='FAILED',error='Previous malformed result')
    monkeypatch.setattr(s.studio.manager(p),'get',lambda id:failed)
    r=s.refresh(p,r['id']);assert r['status']=='ERROR'
    s.run(p,r['id'],Run(etag=r['etag'],confirm_send=True));box['complete'](definition().model_dump_json());r=s.get(p,r['id'])
    assert r['status']=='READY'
    assert not r.get('error'), 'A successful editable proposal must not show the previous failed attempt as a current error'

def test_comparison_repeated_reference_has_one_row_per_entity(service):
    s,p,_=setup(service);cat=s.bible.category(p,{'id':'audit_reference','name':'Audit template','fields':[{'id':'n','name':'N','type':'number'}]})
    e=s.bible.save(p,{'name':'Synthetic original','category':cat['id'],'fields':{'n':12}})
    r=s.create(p,Create(goal='Audit repeated references',sources=[Source(kind='entity',id=e['id'])]))
    d=Definition(templates=[{'key':'base','name':'Audit','existing_id':cat['id']}],records=[{'key':'one','name':'First label','template_key':'base','existing_id':e['id']},{'key':'two','name':'Second label','template_key':'base','existing_id':e['id']}])
    r=s.review(p,r['id'],Review(etag=r['etag'],definition=d));apply(s,p,r);v=s.table(p,r['id'],'base',sort='name')
    assert len({row['id'] for row in v['rows']})==v['total'], 'Repeated references must be rejected or deduplicated in comparison rows'


def test_structure_reuse_does_not_carry_values_sources_consent_or_task(service):
    s,p,_=setup(service);r=draft(s,p,text='OLD_SELECTED_INPUT');apply(s,p,r);r=s.get(p,r['id']);r['ai']={'observed_model':'MOCK_FIXTURE'};r['context']={'old_context':'DO_NOT_CARRY'};r=s.save(p,r)
    old=s.get(p,r['id']);c=s.create(p,Create(goal='New goal',text='NEW_SELECTED_INPUT',structure_from={'id':old['id'],'etag':old['etag']}))
    assert c['id']!=old['id'] and c['status']=='DRAFT' and c['definition']['templates']==old['definition']['templates'] and c['definition']['views']==old['definition']['views']
    assert c['definition']['records']==[] and c['receipt'] is None and c['task_id'] is None and c['token']==''
    assert c['definition']['name']=='New goal' and 'OLD_SELECTED_INPUT' not in json.dumps(c) and 'DO_NOT_CARRY' not in json.dumps(c) and not c.get('ai')
    assert len(c['sources'])==1 and c['sources'][0]['text']=='NEW_SELECTED_INPUT' and s.get(p,old['id'])==old
    count=s.index(p)['total']
    with pytest.raises(ConsoleError):s.create(p,Create(goal='Stale clone',structure_from={'id':old['id'],'etag':'0'*64}))
    assert s.index(p)['total']==count

def test_history_pages_and_search_include_earlier_plans(service):
    s,p,_=setup(service)
    for i in range(53):s.create(p,Create(goal=('Earlier needle' if i==0 else 'Other plan')+' '+str(i)))
    pages=[s.index(p,offset=i,limit=20) for i in [0,20,40]]
    assert all(v['total']==53 for v in pages) and [len(v['plans']) for v in pages]==[20,20,13]
    ids=[row['id'] for page in pages for row in page['plans']];assert len(ids)==len(set(ids))==53
    result=s.index(p,query='EARLIER NEEDLE');assert result['total']==1 and result['plans'][0]['goal']=='Earlier needle 0'
    assert not s.index(p,query='NO_MATCH')['plans']

def test_structure_reuse_refreshes_selected_templates_without_original_values(service):
    s,p,_=setup(service);cat=s.bible.category(p,{'id':'reuse_audit','name':'Existing template','fields':[{'id':'n','name':'N','type':'number'}]});e=s.bible.save(p,{'name':'Existing entity','category':cat['id'],'fields':{'n':42}})
    r=s.create(p,Create(goal='Old reference',sources=[Source(kind='entity',id=e['id'])]));r=s.review(p,r['id'],Review(etag=r['etag'],definition=Definition(templates=[{'key':'same','name':'Existing','existing_id':cat['id']}],records=[{'key':'old','name':'Original','template_key':'same','existing_id':e['id']}])));apply(s,p,r);r=s.get(p,r['id'])
    c=s.create(p,Create(goal='Reuse schema only',structure_from={'id':r['id'],'etag':r['etag']}));assert cat['id'] in c['reused_templates'];assert c['sources']==[] and c['definition']['records']==[]
    x=s.get(p,r['id']);x['status']='RUNNING';x=s.save(p,x)
    from app.errors import ConsoleError
    with pytest.raises(ConsoleError):s.create(p,Create(goal='Running clone',structure_from={'id':x['id'],'etag':x['etag']}))


from test_creative_maps_audio import local

def test_http_history_bounds_and_structure_copy_survive_restore(local):
    from pathlib import Path
    client,app,p=local;s=app.state.data_organization;base='/api/projects/'+p+'/data-organization'
    r=s.create(p,Create(goal='Original HTTP template'));r=s.review(p,r['id'],Review(etag=r['etag'],definition=definition()));apply(s,p,r);r=s.get(p,r['id'])
    response=client.post(base+'/plans',json={'goal':'HTTP structure reuse','structure_from':{'id':r['id'],'etag':r['etag']}});assert response.status_code==200,response.text
    c=response.json();assert c['sources']==[] and c['definition']['records']==[]
    for params in [{'offset':-1},{'limit':101},{'q':'x'*201}]:assert client.get(base,params=params).status_code==422
    result=client.get(base,params={'q':'HTTP STRUCTURE','limit':20}).json();assert result['total']==1 and result['plans'][0]['id']==c['id']
    token=client.headers.pop('X-Novel-Request');assert client.post(base+'/plans',json={'goal':'Unauthorized clone','structure_from':{'id':r['id'],'etag':r['etag']}}).status_code==403;client.headers['X-Novel-Request']=token
    backup=app.state.data_center.backup(p,note='ISOLATED_STRUCTURE_REUSE');staged=app.state.data_center.stage(Path(backup['path']).read_bytes());other=app.state.data_center.restore(staged['token'],expected_hash=staged['sha256'])['project_id']
    restored=s.get(other,c['id']);assert restored['definition']==c['definition'] and restored['structure_from']==c['structure_from'];assert s.get(other,r['id'])['status']=='APPLIED'
