import asyncio

from app.core.config import settings
from app.services import tasks


async def test_inline_runs_immediately():
    ran = []

    async def work():
        ran.append(1)

    # default backend is "inline"
    assert settings.task_backend == "inline"
    await tasks.enqueue(work())
    assert ran == [1]  # already executed when enqueue returned


async def test_asyncio_runs_after_yield(monkeypatch):
    ran = []

    async def work():
        ran.append(1)

    monkeypatch.setattr(settings, "task_backend", "asyncio")
    await tasks.enqueue(work())
    # scheduled, not yet run
    assert ran == []
    await asyncio.sleep(0)  # let the loop run the task
    assert ran == [1]


async def test_background_failure_is_swallowed(monkeypatch):
    async def boom():
        raise RuntimeError("nope")

    monkeypatch.setattr(settings, "task_backend", "asyncio")
    # must not raise into the caller
    await tasks.enqueue(boom())
    await asyncio.sleep(0)
