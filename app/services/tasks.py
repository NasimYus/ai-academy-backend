"""Background task queue (F.2) with pluggable backends.

- `inline` (default; dev/tests): awaits the coroutine immediately — deterministic.
- `asyncio`: schedules it on the running loop (fire-and-forget) so the request
  returns without waiting on slow work (e.g. SMTP).

A durable, multi-process queue (arq/Celery + Redis, with retries and
persistence) can replace the `asyncio` backend behind this same `enqueue`
interface for production.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from app.core.config import settings

logger = logging.getLogger("app.tasks")

# Hold references to in-flight tasks so they are not garbage-collected.
_pending: set[asyncio.Task] = set()


async def _run(coro: Coroutine[Any, Any, Any]) -> None:
    try:
        await coro
    except Exception:  # background work must never crash the caller
        logger.exception("background task failed")


async def enqueue(coro: Coroutine[Any, Any, Any]) -> None:
    """Run `coro` now (inline) or schedule it on the loop (asyncio)."""
    if settings.task_backend == "asyncio":
        task = asyncio.create_task(_run(coro))
        _pending.add(task)
        task.add_done_callback(_pending.discard)
    else:
        await _run(coro)
