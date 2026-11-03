"""Real isolated HTTP and Data Center checks; no user data or remote inference."""
from pathlib import Path
from test_creative_maps_audio import local
from test_data_organization import definition

def test_http_scope_confirmation_and_real_backup_restore(local):
    client,app,p=local;s=app.state.data_organization;base='/api/projects/'+p+'/data-organization'
    token=client.headers.pop('X-Novel-Request')
    assert client.post(base+'/plans',json={'goal':'未授权写入'}).status_code==403
    client.headers['X-Novel-Request']=token
    assert client.post(base+'/plans',json={'goal':'隔离检查','script':'bad'}).status_code==422
    r=client.post(base+'/plans',json={'goal':'只整理本地合成数据'});assert r.status_code==200,r.text
    row=r.json();r=client.put(base+'/plans/'+row['id'],json={'etag':row['etag'],'definition':definition().model_dump()});assert r.status_code==200,r.text
    row=r.json();preview=client.get(base+'/plans/'+row['id']+'/preview').json()
    assert client.post(base+'/plans/'+row['id']+'/apply',json={'etag':row['etag'],'preview_sha256':preview['preview_sha256'],'confirm':False}).status_code==422
    applied=client.post(base+'/plans/'+row['id']+'/apply',json={'etag':row['etag'],'preview_sha256':preview['preview_sha256'],'confirm':True});assert applied.status_code==200,applied.text
    entities=applied.json()['entities'];root=app.state.registry.workspace(p).root;body=(root/'chapters/story/draft.txt').read_bytes()
    backup=app.state.data_center.backup(p,images=True,note='ISOLATED_ORGANIZATION_CHECK')
    staged=app.state.data_center.stage(Path(backup['path']).read_bytes());other=app.state.data_center.restore(staged['token'],expected_hash=staged['sha256'])['project_id']
    assert other!=p
    copy=s.get(other,row['id']);assert copy['definition']==row['definition'] and copy['status']=='APPLIED'
    table=s.table(other,row['id'],'numbers');assert table['rows'][0]['fields']['population']==5000000
    assert s.bible.get(other,entities[0]['id'])['status']=='PENDING'
    assert client.get('/api/projects/'+other+'/data-organization/plans/'+row['id']).status_code==200
    assert client.get('/api/projects/novel_'+'f'*32+'/data-organization/plans/'+row['id']).status_code==404
    assert (app.state.registry.workspace(other).root/'chapters/story/draft.txt').read_bytes()==body and (root/'chapters/story/draft.txt').read_bytes()==body
