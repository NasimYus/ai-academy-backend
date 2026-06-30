from httpx import AsyncClient

from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_my_quiz_results_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/panel/quizzes/my-results")).status_code == 401


async def test_open_quizzes_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/panel/quizzes/opens")).status_code == 401


async def test_my_comments_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/panel/my-comments")).status_code == 401


async def test_panel_lists_empty_for_fresh_student(client: AsyncClient):
    token, _ = await register_verified_user(client, email="panel-lists@aiacademy.tj")
    for path in ("/panel/quizzes/my-results", "/panel/quizzes/opens", "/panel/my-comments"):
        r = await client.get(f"/api/v1{path}", headers=_auth(token))
        assert r.status_code == 200, path
        assert r.json() == [], path
