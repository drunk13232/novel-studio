"""Real isolated Data Center round trip for workflow configuration and checkpoints."""
import asyncio
from pathlib import Path
from test_creative_maps_audio import local
from app.creative.workflows import Definition,Step,Save,RunCreate,Control

def test_workflow_templates_and_completed_checkpoints_survive_full_backup_restore(local):
    client,app,p=local;f=app.state.workflows
    t=f.save(p,Save(definition=Definition(name='Original backup workflow',scope='world',steps=[Step(kind='manual',title='Author input',instruction='Only isolated original fixture data.')])) )
    row=f.create(p,RunCreate(template_id=t['id'],template_etag=t['etag'],goal='Original fixture backup'))
    row=asyncio.run(f.control(p,row['id'],Control(etag=row['etag'],action='run',confirm_send=True)))
    assert row['status']=='COMPLETED'
    interrupted=f.create(p,RunCreate(template_id=t['id'],template_etag=t['etag'],goal='Interrupted restore fixture'))
    interrupted.update(status='RUNNING',active_task='historical_task_only',auto_continue=True,steps={t['definition']['steps'][0]['id']:{'status':'RUNNING'}});f.put(p,interrupted,'runs')
    backup=app.state.data_center.backup(p,images=True,note='ISOLATED_WORKFLOW_CHECK')
    staged=app.state.data_center.stage(Path(backup['path']).read_bytes())
    other=app.state.data_center.restore(staged['token'],expected_hash=staged['sha256'])['project_id']
    assert other!=p
    assert f.template(other,t['id'])['definition']==t['definition']
    restored=f.get(other,row['id']);assert restored['status']=='COMPLETED' and restored['steps']==row['steps']
    assert restored['project_id']==other and f.get(p,row['id'])['project_id']==p

    resumed=f.get(other,interrupted['id']);assert resumed['status']=='PAUSED' and not resumed['active_task'] and not resumed['auto_continue']
    assert resumed['steps'][t['definition']['steps'][0]['id']]['status']=='INTERRUPTED'
