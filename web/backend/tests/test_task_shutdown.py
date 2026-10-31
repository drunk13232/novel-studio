"""Actual TaskManager with bounded local runners; injected adapters are not AI."""
import asyncio
from pathlib import Path
import uuid
import pytest
from app.errors import ConsoleError
from app.models.requests import TaskRequest
from app.tasks.manager import TaskManager, Task, now
from app.tasks.router import TaskRouter
from app.workspace.service import WorkspaceService


def new_manager(tmp_path):
    root = tmp_path / 'workspace'
    root.mkdir()
    ws = WorkspaceService(root)
    return TaskManager(ws, TaskRouter(ws))


def request():
    return TaskRequest(type='custom_prompt', prompt='LOCAL_ONLY_TASK_SHUTDOWN_TEST')


class LocalAdapter:
    def __init__(self, loop, released, interrupt_error=None, close_error=None):
        self.loop, self.released = loop, released
        self.interrupt_error, self.close_error = interrupt_error, close_error
        self.interrupt_calls = self.close_calls = 0

    def interrupt(self):
        self.interrupt_calls += 1
        if self.interrupt_error:
            raise self.interrupt_error
        self.loop.call_soon_threadsafe(self.released.set)

    def close(self):
        self.close_calls += 1
        self.loop.call_soon_threadsafe(self.released.set)
        if self.close_error:
            raise self.close_error


def add_owned_tasks(manager, interrupt_error=None, close_error=None):
    loop = asyncio.get_running_loop()
    gates = [asyncio.Event(), asyncio.Event()]
    rows = []
    for index in range(3):
        task = Task(uuid.uuid4().hex, request(), 'local-only', status='RUNNING' if index < 2 else 'QUEUED')
        task.workspace = manager.workspace.root
        if index < 2:
            task.adapter = LocalAdapter(loop, gates[index], interrupt_error if index == 0 else None, close_error if index == 0 else None)
        async def run(t=task, gate=gates[index if index < 2 else 0]):
            await gate.wait()
            t.status = 'CANCELLED' if t.cancel_requested else 'SUCCEEDED'
            t.finished_at = now()
        task.runner = asyncio.create_task(run())
        manager.tasks[task.id] = task
        rows.append(task)
    return rows, gates


async def fixture_cleanup(rows, gates):
    for gate in gates:
        gate.set()
    await asyncio.gather(*(t.runner for t in rows), return_exceptions=True)


def test_normal_close_cancels_active_and_queued_owned_tasks(tmp_path):
    async def run():
        manager = new_manager(tmp_path)
        rows, gates = add_owned_tasks(manager)
        try:
            await asyncio.wait_for(manager.close(), 3)
            assert manager._closed and all(t.cancel_requested for t in rows)
            assert all(t.status == 'CANCELLED' and t.runner.done() for t in rows)
            assert [t.adapter.interrupt_calls for t in rows[:2]] == [1, 1]
            assert [t.adapter.close_calls for t in rows[:2]] == [0, 0]
        finally:
            await fixture_cleanup(rows, gates)
    asyncio.run(run())


@pytest.mark.parametrize('close_also_fails', [False, True])
def test_interrupt_error_still_closes_only_owner_and_cancels_other_tasks(tmp_path, close_also_fails):
    async def run():
        manager = new_manager(tmp_path)
        interrupt_error = RuntimeError('INJECTED_LOCAL_INTERRUPT_FAILURE')
        close_error = RuntimeError('INJECTED_LOCAL_CLOSE_FAILURE') if close_also_fails else None
        rows, gates = add_owned_tasks(manager, interrupt_error, close_error)
        try:
            with pytest.raises(ExceptionGroup if close_also_fails else RuntimeError) as caught:
                await asyncio.wait_for(manager.close(), 3)
            assert all(t.cancel_requested for t in rows), 'A failed stop must not skip later owners'
            assert all(t.runner.done() for t in rows)
            assert rows[0].adapter.close_calls == 1
            assert rows[1].adapter.close_calls == 0
            if close_also_fails:
                assert caught.value.exceptions == (interrupt_error, close_error)
            else:
                assert caught.value is interrupt_error
        finally:
            await fixture_cleanup(rows, gates)
    asyncio.run(run())


def test_prepared_entry_rejects_closed_manager_without_creating_or_running_work(tmp_path):
    async def run():
        manager = new_manager(tmp_path)
        await manager.close()
        calls = []
        def local_execute(*args):
            calls.append('unexpected execution')
            return {'status': 'completed', 'output': 'local only'}
        try:
            with pytest.raises(ConsoleError) as caught:
                manager.prepared(request(), 'LOCAL_ONLY', True, 'local-only', execute=local_execute)
            assert caught.value.status == 503
            assert manager.tasks == {} and manager.store.rows(manager.workspace.root) == []
            assert calls == []
        finally:
            await manager.close()
    asyncio.run(run())


def test_unhandled_owned_runner_error_is_not_silently_discarded(tmp_path):
    async def run():
        manager = new_manager(tmp_path)
        failure = RuntimeError('INJECTED_LOCAL_RUNNER_FAILURE')
        task = Task(uuid.uuid4().hex, request(), 'local-only', status='FAILED', finished_at=now())
        task.workspace = manager.workspace.root
        async def failed_runner():
            raise failure
        task.runner = asyncio.create_task(failed_runner())
        manager.tasks[task.id] = task
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError) as caught:
            await manager.close()
        assert caught.value is failure and task.runner.done()
    asyncio.run(run())

def test_queued_execute_does_not_start_after_shutdown_admission_closes(tmp_path):
    async def run():
        manager = new_manager(tmp_path)
        calls = []
        def local_execute(*args):
            calls.append('unexpected execution after admission closed')
            return {'status': 'completed', 'output': 'local only'}
        task = manager.prepared(request(), 'LOCAL_ONLY', True, 'local-only', execute=local_execute)
        manager._closed = True
        try:
            await asyncio.wait_for(task.runner, 3)
            assert calls == []
            assert task.status == 'CANCELLED' and task.cancel_requested
        finally:
            await manager.close()
    asyncio.run(run())


def test_expected_cancelled_runner_does_not_turn_shutdown_into_failure(tmp_path):
    async def run():
        manager = new_manager(tmp_path)
        task = Task(uuid.uuid4().hex, request(), 'local-only', status='CANCELLED', finished_at=now())
        task.workspace = manager.workspace.root
        task.runner = asyncio.create_task(asyncio.sleep(10))
        task.runner.cancel()
        manager.tasks[task.id] = task
        await asyncio.sleep(0)
        await manager.close()
        assert task.runner.cancelled() and manager._closed
    asyncio.run(run())


def test_close_waits_for_owned_result_receipt_before_returning(tmp_path):
    async def run():
        manager = new_manager(tmp_path)
        stopped, receipt = asyncio.Event(), asyncio.Event()
        task = Task(uuid.uuid4().hex, request(), 'local-only', status='RUNNING')
        task.workspace = manager.workspace.root
        task.adapter = LocalAdapter(asyncio.get_running_loop(), stopped)
        output = tmp_path / 'local-owned-result.txt'
        async def runner():
            await stopped.wait()
            await receipt.wait()
            output.write_bytes(b'LOCAL_ONLY_OWNED_RESULT')
            task.status = 'CANCELLED'; task.finished_at = now()
        task.runner = asyncio.create_task(runner()); manager.tasks[task.id] = task
        closing = asyncio.create_task(manager.close())
        try:
            await asyncio.wait_for(stopped.wait(), 3)
            await asyncio.sleep(0)
            assert not closing.done() and not output.exists()
            receipt.set()
            await asyncio.wait_for(closing, 3)
            assert task.runner.done() and output.read_bytes() == b'LOCAL_ONLY_OWNED_RESULT'
        finally:
            stopped.set(); receipt.set()
            await asyncio.gather(closing, task.runner, return_exceptions=True)
    asyncio.run(run())


def test_actual_run_drains_fixed_local_worker_after_interrupt_failure(tmp_path):
    import threading
    class FixedWorker:
        def __init__(self, failure=None):
            self.failure = failure
            self.entered = threading.Event()
            self.stopped = threading.Event()
            self.start_calls = self.close_calls = 0
        def start_task(self, prompt, emit, **kwargs):
            self.start_calls += 1; self.entered.set()
            if not self.stopped.wait(6):
                raise TimeoutError('LOCAL_WORKER_GATE')
            return {'status': 'interrupted', 'output': ''}
        def interrupt(self):
            if self.failure:
                raise self.failure
            self.stopped.set()
        def close(self):
            self.close_calls += 1; self.stopped.set()
    async def run():
        manager = new_manager(tmp_path)
        failure = RuntimeError('INJECTED_FIXED_WORKER_INTERRUPT')
        adapters = [FixedWorker(failure), FixedWorker()]
        first = manager.prepared(request(), 'LOCAL_ONLY', True, 'local-first', adapter=adapters[0])
        try:
            assert await asyncio.to_thread(adapters[0].entered.wait, 3)
            queued = manager.prepared(request(), 'LOCAL_ONLY', True, 'local-queued', adapter=adapters[1])
            with pytest.raises(RuntimeError) as caught:
                await asyncio.wait_for(manager.close(), 4)
            assert caught.value is failure
            assert first.runner.done() and queued.runner.done()
            assert first.status == 'INTERRUPTED' and queued.status == 'CANCELLED'
            assert [a.start_calls for a in adapters] == [1, 0]
            assert [a.close_calls for a in adapters] == [1, 0]
            assert first.finished_at and queued.finished_at
        finally:
            for adapter in adapters:
                adapter.stopped.set()
            await manager.close()
    asyncio.run(run())
