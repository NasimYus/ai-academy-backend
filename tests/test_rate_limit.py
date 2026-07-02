import types

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.rate_limit import _store, rate_limit


def _req(host: str = "9.9.9.9", path: str = "/api/v1/auth/login"):
    return types.SimpleNamespace(
        client=types.SimpleNamespace(host=host),
        url=types.SimpleNamespace(path=path),
    )


async def test_rate_limit_noop_in_debug(monkeypatch):
    monkeypatch.setattr(settings, "debug", True)
    _store.clear()
    dep = rate_limit(2)
    for _ in range(5):
        await dep(_req())  # never raises in debug


async def test_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.setattr(settings, "debug", False)
    _store.clear()
    dep = rate_limit(3, window_seconds=60)
    for _ in range(3):
        await dep(_req())  # first 3 allowed
    with pytest.raises(HTTPException) as exc:
        await dep(_req())
    assert exc.value.status_code == 429
    assert exc.value.detail == "too_many_requests"


async def test_rate_limit_is_per_ip(monkeypatch):
    monkeypatch.setattr(settings, "debug", False)
    _store.clear()
    dep = rate_limit(1)
    await dep(_req(host="1.1.1.1"))
    # a different IP has its own bucket
    await dep(_req(host="2.2.2.2"))
    with pytest.raises(HTTPException):
        await dep(_req(host="1.1.1.1"))
