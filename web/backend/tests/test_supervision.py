import asyncio
import json
from pathlib import Path
import pytest
from app.errors import ConsoleError
from app.tasks.manager import TaskManager
from app.tasks.router import TaskRouter
from app.models.requests import TaskRequest
from app.workspace.service import WorkspaceService


def test_actual_startup_failure_is_terminal(tmp_path,monkeypatch):
    monkeypatch.setenv('NOVEL_CODEX_BIN',str(tmp_path/'not-installed.exe'))
    async def check():
        (tmp_path/'AGENTS.md').write_text('Isolated read-only fixture; no real author data.',encoding='utf8')
        ws=WorkspaceService(tmp_path)
        manager=TaskManager(ws,TaskRouter(ws))
        task=manager.start(TaskRequest(type='custom_prompt',prompt='read only',options={'read_only':True}))
        assert task.status=='QUEUED'
        await task.runner
        # Preserve the terminal lifecycle/error contract without tying it to one
        # Chinese wording of the same missing-runtime failure.
        assert task.status=='FAILED' and task.finished_at
        assert 'NOVEL_CODEX_BIN' in task.error
        log=''.join([line async for line in manager.events(task.id,0)])
        assert 'task_completed' in log and 'FAILED' in log
        await manager.close()
    asyncio.run(check())


def test_queued_cancel_never_launches_codex(tmp_path):
    async def check():
        ws=WorkspaceService(tmp_path); manager=TaskManager(ws,TaskRouter(ws))
        await manager._serial.acquire()
        task=manager.start(TaskRequest(type='custom_prompt',prompt='read'))
        await manager.cancel(task.id)
        manager._serial.release()
        await task.runner
        assert task.status=='CANCELLED' and task.adapter is None
        await manager.close()
    asyncio.run(check())


def test_pipeline_commit_excluded(tmp_path):
    (tmp_path/'.agents/skills/novel-chapter-pipeline').mkdir(parents=True)
    (tmp_path/'.agents/skills/novel-chapter-pipeline/SKILL.md').write_text('skill')
    (tmp_path/'chapters/001').mkdir(parents=True)
    (tmp_path/'chapters/001/plan.md').write_text('plan')
    # The mixed-role pipeline has been intentionally disabled since V0.6.
    with pytest.raises(ConsoleError) as failure:
        TaskRouter(WorkspaceService(tmp_path)).build(TaskRequest(type='chapter_pipeline',chapter=1,options={'confirm_pipeline':True}))
    assert failure.value.status==409 and '已关闭' in str(failure.value) and 'State Commit' in str(failure.value)
