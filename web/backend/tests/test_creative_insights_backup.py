"""Actual app/Data Center backup round trip for A/B metadata. No model is called."""
import json
from test_creative_maps_audio import local
from app.library.storage import uid,write,digest


def test_curve_and_reader_profiles_survive_real_full_backup_restore(local):
    client,app,p=local;prefix='/api/projects/'+p+'/creative-insights';root=app.state.registry.workspace(p).root
    path='chapters/story/draft.txt';doc=client.get('/api/projects/'+p+'/files/content',params={'path':path}).json()
    saved=client.put('/api/projects/'+p+'/files/content',json={'path':path,'content':'😀小舟听见枪声，危险与恐惧逼近。她仍然抱着希望。','etag':doc['etag']});assert saved.status_code==200
    original=(root/path).read_bytes();profiles=[]
    for name in ['细读型画像','悬疑偏好画像']:
        current=client.get(prefix+'/readers').json()
        response=client.put(prefix+'/readers/personas',json={'etag':current['etag'],'persona':{'name':name,'age_group':'成人（作者假设）','preferences':'关注人物选择','abandonment_triggers':'证据不足的转折','payment_willingness':'仅为假设'}})
        assert response.status_code==200;profiles=response.json()['profiles']
    response=client.post(prefix+'/curve/analyze',json={'whole_book':True});assert response.status_code==200,response.text
    curve=response.json();chapter=curve['chapters'][0];point=curve['points'][0];assert point['evidence'] and point['source_current']
    response=client.put(prefix+'/curve/override',json={'etag':curve['etag'],'chapter_id':chapter['id'],'tension':8.4,'note':'作者的本地判断，不改变正文'})
    assert response.status_code==200 and response.json()['points'][0]['override_current']
    reviews=app.state.creative_insights.readers.reviews;identifier=uid('review');revision=digest(original)
    # Explicitly synthetic completed historical report tests storage/remapping only.
    write(reviews.path(p,identifier),{'id':identifier,'project_id':p,'mode':'reader','source_path':path,'source_revision':revision,'created_at':'2026-10-25T00:00:00Z','reader_persona':profiles[0],'sources':[{'path':path,'revision':revision}], 'ai_metadata':{'backend':'MOCK_BACKUP_FIXTURE_NOT_REAL_AI'},'anchors':[],'reader_reactions':[],'report':{'verdict':'INCONCLUSIVE','summary':'Insufficient evidence.','issues':[]},'canon_changed':False})
    backup=app.state.data_center.backup(p,images=True,note='ISOLATED_AB_METADATA_CHECK')
    staged=app.state.data_center.stage(__import__('pathlib').Path(backup['path']).read_bytes())
    restored=app.state.data_center.restore(staged['token'],expected_hash=staged['sha256']);other=restored['project_id'];other_prefix='/api/projects/'+other+'/creative-insights'
    assert other!=p
    assert client.get(other_prefix+'/readers').json()['profiles']==profiles
    new_curve=client.post(other_prefix+'/curve/analyze',json={'whole_book':True}).json();new_point=new_curve['points'][0]
    assert new_point['tension']==8.4 and new_point['override_current'] and new_point['override']['note']=='作者的本地判断，不改变正文'
    report=reviews.get(other,identifier);assert report['project_id']==other and report['reader_persona']['id']==profiles[0]['id'] and report['source_current']
    assert report['ai_metadata']['backend']=='MOCK_BACKUP_FIXTURE_NOT_REAL_AI'
    assert (app.state.registry.workspace(other).root/path).read_bytes()==original and (root/path).read_bytes()==original
    restored_files=app.state.registry.workspace(other).root
    assert (restored_files/'metadata/studio/narrative-curve.json').is_file() and (restored_files/'metadata/studio/reader-personas.json').is_file()
