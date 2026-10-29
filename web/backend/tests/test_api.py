from pathlib import Path
import os
import subprocess
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.workspace.service import WorkspaceService
from app.models.requests import TaskRequest
from app.codex.adapter import CodexAdapter, CodexUnavailable, codex_binary, redact
from pydantic import ValidationError


@pytest.fixture
def client(tmp_path):
    for name in ['state', 'docs', 'chapters', 'settings', 'outlines']: (tmp_path / name).mkdir()
    (tmp_path / 'docs/test.md').write_bytes(b'\xef\xbb\xbf# test\r\nbody\r\n')
    (tmp_path / 'state/current-story-state.yaml').write_text('project: {}\npov: {}\nlocation: {}\n', encoding='utf-8')
    app = create_app(Settings(workspace=tmp_path)); app.state.testing = True
    # No lifespan: API boundary tests do not invoke models or impersonate real E2E.
    test = TestClient(app)
    test.headers['X-Novel-Request'] = test.get('/api/session').json()['request_token']
    return test


@pytest.mark.parametrize('path', ['../auth.json','docs/../../auth.json','C:/Windows/a.txt','docs\\test.md','state/.secret.json','.git/config','web/backend/app/main.py','docs/a.exe','docs//test.md','docs/./test.md','docs/a:ads.txt','docs/vendor/sepia/README.md','docs/web-validation/runtime/protocol/a.json'])
def test_traversal(client, path):
    assert client.get('/api/files/content', params={'path': path}).status_code == 403


def test_edit_preserves_bytes_and_conflicts(client):
    original = client.get('/api/files/content', params={'path': 'docs/test.md'}).json()
    assert original['bom'] and original['line_ending'] == 'CRLF'
    body = {'path': original['path'], 'content': original['content']+'new\r\n', 'etag': original['etag']}
    saved = client.put('/api/files/content', json=body)
    assert saved.status_code == 200
    assert saved.json()['bom'] and saved.json()['line_ending'] == 'CRLF'
    assert client.put('/api/files/content', json=body).status_code == 409


def test_invalid_yaml(client):
    file = client.get('/api/files/content', params={'path': 'state/current-story-state.yaml'}).json()
    assert client.put('/api/files/content', json={'path':file['path'],'etag':file['etag'],'content':'project: [broken'}).status_code == 422


def test_origins_and_csrf(client):
    assert client.get('/api/status',headers={'Origin':'https://evil.example'}).status_code == 403
    assert client.get('/api/status',headers={'Host':'evil.example'}).status_code == 403
    assert client.post('/api/tasks',json={'type':'custom_prompt','prompt':'read'},headers={'X-Novel-Request':'wrong'}).status_code == 403
    assert client.options('/api/tasks',headers={'Origin':'https://evil.example'}).status_code == 403


def test_invalid_tasks_and_no_shell(client):
    for body in [{'type':'shell','prompt':'x'}, {'type':'custom_prompt','prompt':'x','cwd':'C:/'},
                 {'type':'custom_prompt','prompt':'x','options':{'command':'whoami'}},
                 {'type':'state_commit'}, {'type':'chapter_pipeline','chapter':1}]:
        assert client.post('/api/tasks',json=body).status_code == 422


def test_missing_codex(client):
    result = client.post('/api/tasks',json={'type':'custom_prompt','prompt':'Read state'})
    assert result.status_code == 503


def test_symlink(tmp_path):
    (tmp_path/'docs').mkdir(); outside=tmp_path.parent/'outside-web-test.txt'; outside.write_text('outside')
    link=tmp_path/'docs/link.txt'
    try: link.symlink_to(outside)
    except OSError: pytest.skip('Windows symlink privilege unavailable; junction is tested separately')
    with pytest.raises(Exception): WorkspaceService(tmp_path).content('docs/link.txt')
    outside.unlink()


@pytest.mark.skipif(os.name != 'nt', reason='Windows junction test')
def test_windows_junction(tmp_path):
    (tmp_path/'docs').mkdir(); (tmp_path/'outside').mkdir()
    (tmp_path/'outside/secret.txt').write_text('must not read')
    link=tmp_path/'docs/escape'
    env={**os.environ,'NOVEL_TEST_LINK':str(link),'NOVEL_TEST_TARGET':str(tmp_path/'outside')}
    result=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
        'New-Item -ItemType Junction -Path $env:NOVEL_TEST_LINK -Target $env:NOVEL_TEST_TARGET | Out-Null'],env=env,capture_output=True)
    assert result.returncode==0, 'Cannot create junction test fixture'
    try:
        assert link.is_junction()
        with pytest.raises(Exception,match='symlink/junction'): WorkspaceService(tmp_path).content('docs/escape/secret.txt')
        assert not WorkspaceService(tmp_path).list_files()
    finally:
        # unlink junction itself; never recursively delete its target.
        os.rmdir(link)


def test_redaction():
    assert 'sk-' not in redact('Bearer sk-abcdefghijklmnopqrstuvwxyz')
    assert 'supersecret' not in redact('access_token="supersecret"')


def test_actual_missing_binary(tmp_path,monkeypatch):
    monkeypatch.setenv('NOVEL_CODEX_BIN',str(tmp_path/'missing.exe'))
    # An invalid explicit override must fail closed rather than fall back to the
    # installed SDK binary. Match the actionable setting, not a translated phrase.
    with pytest.raises(CodexUnavailable):
        codex_binary()
    def unexpected_client(*args,**kwargs):
        raise AssertionError('Missing explicit runtime must not initialize the SDK')
    monkeypatch.setattr(CodexAdapter,'_new_client',unexpected_client)
    result=CodexAdapter(tmp_path).health()
    assert result['codex'] is False and 'NOVEL_CODEX_BIN' in result['reason']


def test_status_damaged_shape(client):
    client.app.state.workspace.root.joinpath('state/current-story-state.yaml').write_text('project: []\npov: x\n',encoding='utf-8')
    assert client.get('/api/status').status_code == 422


def test_flat_and_nested_chapters(client):
    root=client.app.state.workspace.root
    (root/'chapters/001.md').write_text('# First\n',encoding='utf-8')
    (root/'chapters/002').mkdir()
    (root/'chapters/002/plan.md').write_text('# Plan',encoding='utf-8')
    (root/'chapters/002/draft.md').write_text('# Second',encoding='utf-8')
    rows=client.get('/api/chapters').json()
    assert rows[0]['final']=='chapters/001.md' and rows[1]['plan']=='chapters/002/plan.md'


def test_commit_authorization_cannot_attach_to_other_task():
    with pytest.raises(ValidationError): TaskRequest(type='custom_prompt',prompt='test',options={'confirm_state_commit':True})
