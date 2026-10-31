"""Real isolated application lifecycle; injected close errors, no AI/native GUI."""
import asyncio
import hashlib
import inspect
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from app.config import Settings
from app.errors import ConsoleError
from app.main import create_app

ENGINE = Path(__file__).resolve().parents[3]


@pytest.fixture
def resources(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    shutil.copytree(ENGINE / 'desktop/preview-template', workspace)
    first = next((workspace / 'projects').glob('novel_*'))
    second = workspace / 'projects' / ('novel_' + 'a' * 32)
    shutil.copytree(first, second)
    meta = yaml.safe_load((second / 'project.yaml').read_text('utf8'))
    meta.update(id=second.name, title='Synthetic lifecycle second project')
    (second / 'project.yaml').write_text(yaml.safe_dump(meta, allow_unicode=True), 'utf8')
    for name, value in {'NOVEL_STUDIO_DATA': tmp_path / 'data', 'NOVEL_STUDIO_HOME': tmp_path / 'home', 'CODEX_HOME': tmp_path / 'empty-codex', 'NOVEL_DEMO': '1'}.items():
        monkeypatch.setenv(name, str(value))
    before = {p.relative_to(workspace): hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
    app = create_app(Settings(workspace=workspace))
    trace, failures, originals, scopes = [], {}, [], []

    def track(owner, name, label):
        original = getattr(owner, name)
        originals.append((label, original))
        if inspect.iscoroutinefunction(original):
            async def close():
                trace.append(label)
                await original()
                if label in failures:
                    raise failures[label]
        else:
            def close():
                trace.append(label)
                original()
                if label in failures:
                    raise failures[label]
        monkeypatch.setattr(owner, name, close)

    state = app.state
    for obj, label in [(state.images, 'images'), (state.data_center, 'backups'), (state.references, 'references'), (state.automation, 'automation'), (state.assistant, 'assistant'), (state.audio_export, 'audio'), (state.book_center.prints, 'print'), (state.speech, 'speech'), (state.manager, 'manager')]:
        track(obj, 'close', label)

    def open_scopes():
        assert not scopes, 'Create scoped managers once, after startup'
        for index, project in enumerate([first.name, second.name], 1):
            manager = state.studio_tools.manager(project)
            scopes.append(manager)
            track(manager, 'close', 'scope' + str(index))

    r = SimpleNamespace(app=app, trace=trace, failures=failures, scopes=scopes, open_scopes=open_scopes)
    yield r
    # Even on the unfixed baseline, clean up only this fixture's unattempted
    # resources after recording the failure. This is not counted as app cleanup.
    async def fallback_cleanup():
        for label, original in originals:
            if label not in trace:
                value = original()
                if inspect.isawaitable(value):
                    await value
    asyncio.run(fallback_cleanup())
    assert not state.images.thread or not state.images.thread.is_alive()
    assert not state.data_center.thread or not state.data_center.thread.is_alive()
    assert all((workspace / name).is_file() and hashlib.sha256((workspace / name).read_bytes()).hexdigest() == digest for name, digest in before.items())


EXPECTED = ['images', 'backups', 'references', 'automation', 'assistant', 'audio', 'print', 'speech', 'manager', 'scope1', 'scope2']


def test_normal_shutdown_closes_real_services_in_existing_order(resources):
    r = resources
    async def run():
        async with r.app.router.lifespan_context(r.app):
            r.open_scopes()
    asyncio.run(run())
    assert r.trace == EXPECTED
    assert r.app.state.manager._closed and all(m._closed for m in r.scopes)
    assert r.app.state.images.stop.is_set() and r.app.state.data_center.stop.is_set()


@pytest.mark.parametrize('failed', ['images', 'references', 'manager', 'scope1'])
def test_one_close_failure_does_not_skip_other_owned_resources(resources, failed):
    r = resources
    error = RuntimeError('INJECTED_CLOSE_' + failed)
    r.failures[failed] = error
    async def run():
        async with r.app.router.lifespan_context(r.app):
            r.open_scopes()
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(run())
    assert caught.value is error
    assert r.trace == EXPECTED
    assert r.app.state.manager._closed and all(m._closed for m in r.scopes)
    assert r.app.state.automation.closed


def test_partial_startup_failure_still_closes_owned_resources(resources, monkeypatch):
    r = resources
    error = RuntimeError('INJECTED_BACKUP_START_FAILURE')
    def fail_start():
        raise error
    monkeypatch.setattr(r.app.state.data_center, 'start', fail_start)
    async def run():
        async with r.app.router.lifespan_context(r.app):
            pytest.fail('Startup failure must not yield a ready app')
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(run())
    assert caught.value is error
    assert r.trace == EXPECTED[:-2]
    assert r.app.state.manager._closed and r.app.state.automation.closed


def test_body_and_multiple_cleanup_errors_remain_visible(resources):
    r = resources
    body_error = RuntimeError('INJECTED_LIFESPAN_BODY_FAILURE')
    r.failures.update(references=RuntimeError('INJECTED_REFERENCE_CLOSE'), scope1=RuntimeError('INJECTED_SCOPE_CLOSE'))
    async def run():
        async with r.app.router.lifespan_context(r.app):
            r.open_scopes()
            raise body_error
    with pytest.raises(ExceptionGroup) as caught:
        asyncio.run(run())
    assert r.trace == EXPECTED
    assert caught.value.exceptions == (body_error, r.failures['references'], r.failures['scope1'])
    assert all(m._closed for m in r.scopes)


def test_lifespan_cancellation_still_closes_real_resources(resources):
    r = resources
    async def run():
        async with r.app.router.lifespan_context(r.app):
            r.open_scopes()
            asyncio.current_task().cancel()
            await asyncio.sleep(0)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run())
    assert r.trace == EXPECTED
    assert r.app.state.manager._closed and all(m._closed for m in r.scopes)


def test_all_known_manager_admission_stops_before_first_service_close(resources, monkeypatch):
    r = resources
    original = r.app.state.images.close
    def first_close():
        assert r.app.state.manager._closed and all(m._closed for m in r.scopes), 'Admission must close before waiting for service threads'
        with pytest.raises(ConsoleError) as caught:
            r.app.state.studio_tools.manager(next(iter(r.app.state.registry.rows)))
        assert getattr(caught.value, 'status', None) == 503
        original()
    monkeypatch.setattr(r.app.state.images, 'close', first_close)
    async def run():
        async with r.app.router.lifespan_context(r.app):
            r.open_scopes()
    asyncio.run(run())
    assert r.trace == EXPECTED


def test_draft_and_reference_admission_share_application_shutdown(resources, monkeypatch):
    from app.projects.models import Idea
    from app.tasks.manager import TaskManager
    from app.tasks.router import TaskRouter
    r = resources
    reference = TaskManager(r.app.state.workspace, TaskRouter(r.app.state.workspace))
    r.app.state.references.managers['synthetic-local-scope'] = reference
    draft_list = next(route.endpoint for route in r.app.routes if getattr(route, 'path', '') == '/api/drafts/{scope_id}/tasks')
    original = r.app.state.images.close
    def first_close():
        assert reference._closed
        original()
    monkeypatch.setattr(r.app.state.images, 'close', first_close)
    async def run():
        async with r.app.router.lifespan_context(r.app):
            draft = r.app.state.drafts.create(Idea(title='Synthetic lifecycle draft'))
            assert await draft_list(scope_id=draft['id']) == []
        with pytest.raises(ConsoleError) as caught:
            await draft_list(scope_id=draft['id'])
        assert caught.value.status == 503
    asyncio.run(run())
    assert reference._closed and r.trace == EXPECTED[:-2]
