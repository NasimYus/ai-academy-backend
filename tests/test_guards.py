from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import require_level, require_role


async def _allows(dep, role: str) -> bool:
    try:
        await dep(SimpleNamespace(role_name=role))
        return True
    except HTTPException:
        return False


# Admins are allowed at every access level (legacy admin panel shares the
# instructor/teacher controllers and has full access).
@pytest.mark.parametrize(
    "role,allowed",
    [("user", True), ("teacher", True), ("organization", True), ("admin", True)],
)
async def test_require_level_user(role, allowed):
    assert await _allows(require_level("user"), role) is allowed


@pytest.mark.parametrize(
    "role,allowed",
    [("user", False), ("teacher", True), ("organization", True), ("admin", True)],
)
async def test_require_level_teacher(role, allowed):
    assert await _allows(require_level("teacher"), role) is allowed


@pytest.mark.parametrize(
    "role,allowed",
    [("organization", True), ("teacher", False), ("user", False), ("admin", True)],
)
async def test_require_level_organization(role, allowed):
    assert await _allows(require_level("organization"), role) is allowed


async def test_require_role_exact():
    assert await _allows(require_role("admin"), "admin") is True
    assert await _allows(require_role("admin"), "user") is False
