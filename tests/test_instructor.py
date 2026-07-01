from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.role import Role
from app.models.user import User
from tests.conftest import register_verified_user


async def _teacher(client: AsyncClient, email: str = "teacher@aiacademy.tj") -> tuple[str, int]:
    token, uid = await register_verified_user(client, email=email)
    async with AsyncSessionLocal() as db:
        user = await db.get(User, uid)
        user.role_name = Role.TEACHER
        user.role_id = 4
        await db.commit()
    return token, uid


async def _category(title: str = "Programming") -> int:
    async with AsyncSessionLocal() as db:
        cat = Category(title=title, slug=title.lower(), order=1)
        db.add(cat)
        await db.commit()
        return cat.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload(category_id: int, **over) -> dict:
    base = {
        "type": "course",
        "title": "Intro to Python",
        "thumbnail": "/media/t.png",
        "image_cover": "/media/c.png",
        "description": "Learn Python",
        "category_id": category_id,
        "duration": 120,
        "price": 100,
        "rules": True,
    }
    base.update(over)
    return base


async def test_create_course_pending(client: AsyncClient):
    token, uid = await _teacher(client)
    cat = await _category()
    r = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(token))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["slug"] == "intro-to-python"
    assert body["description"] == "Learn Python"


async def test_create_draft_first_minimal(client: AsyncClient):
    """Wizard step 1 persists a draft with only type+title (category/images later)."""
    token, _ = await _teacher(client)
    r = await client.post(
        "/api/v1/panel/webinar",
        json={"type": "course", "title": "Draft Course", "locale": "ru"},
        headers=_auth(token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "is_draft"
    assert body["category_id"] is None
    assert body["locale"] == "ru"


async def test_webinar_draft_without_start_date_ok(client: AsyncClient):
    """Wizard step 1: a webinar draft is created without a start_date (that's step 2)."""
    token, _ = await _teacher(client)
    r = await client.post(
        "/api/v1/panel/webinar",
        json={"type": "webinar", "title": "Live draft", "draft": True},
        headers=_auth(token),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "is_draft"


async def test_upload_course_media(client: AsyncClient):
    token, _ = await _teacher(client)
    r = await client.post(
        "/api/v1/panel/webinar/media",
        files={"file": ("thumb.png", b"\x89PNG\r\n", "image/png")},
        data={"kind": "thumbnail"},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.json()["path"].startswith("/media/courses/")


async def test_upload_course_media_invalid_kind(client: AsyncClient):
    token, _ = await _teacher(client)
    r = await client.post(
        "/api/v1/panel/webinar/media",
        files={"file": ("x.png", b"x", "image/png")},
        data={"kind": "bogus"},
        headers=_auth(token),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_media_kind"


async def test_chapter_crud(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    created = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(token))
    cid = created.json()["id"]

    # create two chapters
    c1 = await client.post(
        f"/api/v1/panel/webinar/{cid}/chapters", json={"title": "Раздел 1"}, headers=_auth(token)
    )
    c2 = await client.post(
        f"/api/v1/panel/webinar/{cid}/chapters", json={"title": "Раздел 2"}, headers=_auth(token)
    )
    assert c1.status_code == 201
    ch1, ch2 = c1.json()["id"], c2.json()["id"]
    assert c1.json()["order"] == 0 and c2.json()["order"] == 1

    # list content
    content = await client.get(f"/api/v1/panel/webinar/{cid}/content", headers=_auth(token))
    assert [c["title"] for c in content.json()["chapters"]] == ["Раздел 1", "Раздел 2"]

    # rename
    rn = await client.put(
        f"/api/v1/panel/chapters/{ch1}", json={"title": "Введение"}, headers=_auth(token)
    )
    assert rn.json()["title"] == "Введение"

    # reorder
    ro = await client.put(
        f"/api/v1/panel/webinar/{cid}/chapters/order",
        json={"ordered_ids": [ch2, ch1]},
        headers=_auth(token),
    )
    assert ro.status_code == 204
    content = await client.get(f"/api/v1/panel/webinar/{cid}/content", headers=_auth(token))
    assert [c["id"] for c in content.json()["chapters"]] == [ch2, ch1]

    # delete
    dl = await client.delete(f"/api/v1/panel/chapters/{ch1}", headers=_auth(token))
    assert dl.status_code == 204
    content = await client.get(f"/api/v1/panel/webinar/{cid}/content", headers=_auth(token))
    assert [c["id"] for c in content.json()["chapters"]] == [ch2]


async def test_submit_for_review(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    created = await client.post(
        "/api/v1/panel/webinar", json=_payload(cat, draft=True, rules=False), headers=_auth(token)
    )
    cid = created.json()["id"]
    assert created.json()["status"] == "is_draft"

    # rules not accepted -> 422
    no_rules = await client.post(
        f"/api/v1/panel/webinar/{cid}/submit", json={"rules": False}, headers=_auth(token)
    )
    assert no_rules.status_code == 422
    assert no_rules.json()["detail"] == "rules_required"

    # accepted -> pending + message stored
    ok = await client.post(
        f"/api/v1/panel/webinar/{cid}/submit",
        json={"rules": True, "message_for_reviewer": "Прошу проверить"},
        headers=_auth(token),
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "pending"
    assert ok.json()["message_for_reviewer"] == "Прошу проверить"


async def test_submit_requires_category(client: AsyncClient):
    token, _ = await _teacher(client)
    created = await client.post(
        "/api/v1/panel/webinar",
        json={"type": "course", "title": "No cat", "draft": True},
        headers=_auth(token),
    )
    cid = created.json()["id"]
    r = await client.post(
        f"/api/v1/panel/webinar/{cid}/submit", json={"rules": True}, headers=_auth(token)
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "category_required"


async def test_content_item_crud(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    created = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(token))
    cid = created.json()["id"]
    ch = await client.post(
        f"/api/v1/panel/webinar/{cid}/chapters", json={"title": "Гл. 1"}, headers=_auth(token)
    )
    chid = ch.json()["id"]

    # add a session + a text lesson
    s = await client.post(
        f"/api/v1/panel/chapters/{chid}/items/session",
        json={"title": "Вводная сессия", "duration": 45, "link": "https://meet"},
        headers=_auth(token),
    )
    assert s.status_code == 201
    assert s.json()["type"] == "session" and s.json()["duration"] == 45
    sid = s.json()["id"]

    tl = await client.post(
        f"/api/v1/panel/chapters/{chid}/items/text_lesson",
        json={"title": "Теория", "content": "<p>hi</p>", "accessibility": "free"},
        headers=_auth(token),
    )
    assert tl.status_code == 201

    # content lists both items under the chapter
    content = await client.get(f"/api/v1/panel/webinar/{cid}/content", headers=_auth(token))
    chapter = content.json()["chapters"][0]
    assert chapter["items_count"] == 2
    titles = {i["title"] for i in chapter["items"]}
    assert titles == {"Вводная сессия", "Теория"}

    # update the session
    up = await client.put(
        f"/api/v1/panel/content/session/{sid}",
        json={"title": "Обновлённая", "duration": 60},
        headers=_auth(token),
    )
    assert up.json()["title"] == "Обновлённая" and up.json()["duration"] == 60

    # delete it
    dl = await client.delete(f"/api/v1/panel/content/session/{sid}", headers=_auth(token))
    assert dl.status_code == 204
    content = await client.get(f"/api/v1/panel/webinar/{cid}/content", headers=_auth(token))
    assert content.json()["chapters"][0]["items_count"] == 1


async def test_content_item_invalid_type(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    created = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(token))
    cid = created.json()["id"]
    ch = await client.post(
        f"/api/v1/panel/webinar/{cid}/chapters", json={"title": "c"}, headers=_auth(token)
    )
    r = await client.post(
        f"/api/v1/panel/chapters/{ch.json()['id']}/items/bogus",
        json={"title": "x"},
        headers=_auth(token),
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_item_type"


async def test_chapter_scoped_to_owner(client: AsyncClient):
    owner, _ = await _teacher(client, email="owner2@aiacademy.tj")
    cat = await _category()
    created = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(owner))
    cid = created.json()["id"]
    ch = await client.post(
        f"/api/v1/panel/webinar/{cid}/chapters", json={"title": "X"}, headers=_auth(owner)
    )
    chid = ch.json()["id"]

    other, _ = await _teacher(client, email="other2@aiacademy.tj")
    r = await client.put(
        f"/api/v1/panel/chapters/{chid}", json={"title": "hack"}, headers=_auth(other)
    )
    assert r.status_code == 404


async def test_create_as_draft_when_rules_not_accepted(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    r = await client.post(
        "/api/v1/panel/webinar", json=_payload(cat, rules=False), headers=_auth(token)
    )
    assert r.status_code == 201
    assert r.json()["status"] == "is_draft"


async def test_create_requires_teacher(client: AsyncClient):
    token, _ = await register_verified_user(client, email="plain@aiacademy.tj")  # role 'user'
    cat = await _category()
    r = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(token))
    assert r.status_code == 403


async def test_create_unknown_category(client: AsyncClient):
    token, _ = await _teacher(client)
    r = await client.post("/api/v1/panel/webinar", json=_payload(999), headers=_auth(token))
    assert r.status_code == 422
    assert r.json()["detail"] == "category_not_found"


async def test_webinar_requires_start_date(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    r = await client.post(
        "/api/v1/panel/webinar", json=_payload(cat, type="webinar"), headers=_auth(token)
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "start_date_required"


async def test_list_edit_update_delete(client: AsyncClient):
    token, _ = await _teacher(client)
    cat = await _category()
    created = await client.post("/api/v1/panel/webinar", json=_payload(cat), headers=_auth(token))
    course_id = created.json()["id"]

    # listed in my classes
    listed = await client.get("/api/v1/panel/classes", headers=_auth(token))
    assert listed.status_code == 200
    assert course_id in [c["id"] for c in listed.json()]

    # edit (owner)
    edit = await client.get(f"/api/v1/panel/webinar/{course_id}/edit", headers=_auth(token))
    assert edit.status_code == 200

    # update title + price
    upd = await client.put(
        f"/api/v1/panel/webinar/{course_id}",
        json={"title": "Renamed", "price": 250},
        headers=_auth(token),
    )
    assert upd.status_code == 200
    assert upd.json()["title"] == "Renamed"
    assert upd.json()["price"] == 250.0
    assert upd.json()["slug"] == "intro-to-python"  # slug stays

    # delete
    deleted = await client.delete(f"/api/v1/panel/webinar/{course_id}", headers=_auth(token))
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/panel/webinar/{course_id}/edit", headers=_auth(token))
    assert gone.status_code == 404


async def test_cannot_edit_others_course(client: AsyncClient):
    owner_token, _ = await _teacher(client, email="owner@aiacademy.tj")
    cat = await _category()
    created = await client.post(
        "/api/v1/panel/webinar", json=_payload(cat), headers=_auth(owner_token)
    )
    course_id = created.json()["id"]

    other_token, _ = await _teacher(client, email="other@aiacademy.tj")
    r = await client.get(f"/api/v1/panel/webinar/{course_id}/edit", headers=_auth(other_token))
    assert r.status_code == 404
