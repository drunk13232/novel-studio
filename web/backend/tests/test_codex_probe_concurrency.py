"""Controlled health probes must not serialize author writes or weaken mutation guards."""
import asyncio
import shutil
import threading
from pathlib import Path
import httpx
from app.config import Settings
from app.codex.adapter import CodexAdapter
from app.tasks.lease import acquire,release


def fixture_app(tmp_path,monkeypatch,health):
    root=Path(__file__).resolve().parents[3]
    workspace=tmp_path/'workspace'
    shutil.copytree(root/'desktop/preview-template',workspace)
    monkeypatch.setenv('NOVEL_WORKSPACE',str(workspace))
    monkeypatch.setenv('NOVEL_STUDIO_HOME',str(tmp_path/'home'))
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'data'))
    monkeypatch.setattr(CodexAdapter,'health',health)
    from app.main import create_app # Only import after every workspace/home/data override is isolated.
    app=create_app(Settings(workspace=workspace))
    writes=[]
    @app.post('/api/test-author-write')
    def mutate():
        writes.append('executed')
        return {'saved':True}
    return app,workspace,writes


def test_probe_wait_does_not_block_author_mutation_and_stays_authenticated(tmp_path,monkeypatch):
    entered=threading.Event();finish=threading.Event()
    def health(self):
        entered.set()
        assert finish.wait(5),'controlled probe was not released'
        return {'codex':False,'reason':'CONTROLLED_LOCAL_PROBE'}
    app,workspace,writes=fixture_app(tmp_path,monkeypatch,health)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1') as client:
            token=(await client.get('/api/session')).json()['request_token'];headers={'X-Novel-Request':token}
            probe=asyncio.create_task(client.post('/api/studio/codex/check',headers=headers))
            try:
                assert await asyncio.wait_for(asyncio.to_thread(entered.wait,3),4)
                saved=await client.post('/api/test-author-write',headers=headers)
                assert saved.status_code==200 and saved.json()['saved'] and writes==['executed']
                assert not probe.done(),'the author write must finish before the held probe'
                duplicate=await client.post('/api/studio/codex/check',headers=headers)
                assert duplicate.status_code==409,'health probes still have their own single-flight guard'
                assert (await client.post('/api/studio/codex/check')).status_code==403
                bad={**headers,'Origin':'https://untrusted.invalid'}
                assert (await client.post('/api/studio/codex/check',headers=bad)).status_code==403
            finally:finish.set()
            completed=await probe
            assert completed.status_code==200 and completed.json()['reason']=='CONTROLLED_LOCAL_PROBE'
    asyncio.run(run())


def test_author_write_lease_still_blocks_writes_but_not_read_only_probe(tmp_path,monkeypatch):
    def health(self):return {'codex':False,'reason':'CONTROLLED_LOCAL_PROBE'}
    app,workspace,writes=fixture_app(tmp_path,monkeypatch,health)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1') as client:
            headers={'X-Novel-Request':(await client.get('/api/session')).json()['request_token']}
            lease=acquire(workspace,'studio-data.lock')
            try:
                rejected=await client.post('/api/test-author-write',headers=headers)
                assert rejected.status_code==409 and writes==[]
                checked=await client.post('/api/studio/codex/check',headers=headers)
                assert checked.status_code==200
            finally:release(lease)
            assert (await client.post('/api/test-author-write',headers=headers)).status_code==200
            assert writes==['executed']
    asyncio.run(run())


def test_failed_probe_can_be_retried_without_stuck_checking_state(tmp_path,monkeypatch):
    attempts=[]
    def health(self):
        attempts.append(1)
        if len(attempts)==1:raise RuntimeError('CONTROLLED_LOCAL_PROBE_FAILURE')
        return {'codex':False,'reason':'CONTROLLED_RECOVERED_PROBE'}
    app,workspace,writes=fixture_app(tmp_path,monkeypatch,health)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://127.0.0.1') as client:
            headers={'X-Novel-Request':(await client.get('/api/session')).json()['request_token']}
            failed=await client.post('/api/studio/codex/check',headers=headers)
            assert failed.status_code==503
            status=(await client.get('/api/health')).json()
            assert status['checking'] is False,'probe failure must release the visible checking state'
            assert status['codex'] is False and 'CONTROLLED_LOCAL_PROBE_FAILURE' in status['reason']
            retried=await client.post('/api/studio/codex/check',headers=headers)
            assert retried.status_code==200 and retried.json()['reason']=='CONTROLLED_RECOVERED_PROBE'
            assert attempts==[1,1] and writes==[]
    asyncio.run(run())


def test_failed_probe_preserves_newer_verified_connection(tmp_path,monkeypatch):
    import time
    entered=threading.Event();finish=threading.Event()
    def health(self):
        entered.set()
        assert finish.wait(5)
        raise RuntimeError('CONTROLLED_OLDER_PROBE_FAILURE')
    app,workspace,writes=fixture_app(tmp_path,monkeypatch,health)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://127.0.0.1') as client:
            headers={'X-Novel-Request':(await client.get('/api/session')).json()['request_token']}
            probe=asyncio.create_task(client.post('/api/studio/codex/check',headers=headers))
            try:
                assert await asyncio.wait_for(asyncio.to_thread(entered.wait,3),4)
                app.state.codex_health.update(codex=True,verified_at=time.monotonic(),reason='CONTROLLED_NEWER_VERIFIED_RESULT')
            finally:finish.set()
            assert (await probe).status_code==503
            current=(await client.get('/api/health')).json()
            assert current['codex'] is True
            assert current['reason']=='CONTROLLED_NEWER_VERIFIED_RESULT' and current['checking'] is False
    asyncio.run(run())
