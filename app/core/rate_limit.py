"""Lightweight in-memory rate limiting for sensitive endpoints.

A sliding-window counter keyed by (client IP, path). Active only when
`settings.debug` is False (so local dev + the test-suite are unaffected). For a
multi-process deployment swap the in-memory store for Redis behind the same
`rate_limit(...)` dependency.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import settings

_store: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def rate_limit(
    max_requests: int, window_seconds: int = 60
) -> Callable[..., Coroutine[Any, Any, None]]:
    """FastAPI dependency: allow at most `max_requests` per `window_seconds`
    per client IP + path, else 429. No-op in debug."""

    async def dependency(request: Request) -> None:
        if settings.debug:
            return
        client = request.client.host if request.client else "unknown"
        key = (client, request.url.path)
        now = time.monotonic()
        bucket = _store[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_requests",
            )
        bucket.append(now)

    return dependency
