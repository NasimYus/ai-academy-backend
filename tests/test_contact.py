from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.contact import Contact

_MSG = {
    "name": "Иван",
    "email": "ivan@example.com",
    "phone": "+992 99 555 00 32",
    "subject": "Вопрос по курсу",
    "message": "Здравствуйте! Подскажите по записи на курс.",
}


async def test_submit_contact_stores_message(client: AsyncClient):
    r = await client.post("/api/v1/contact", json=_MSG)
    assert r.status_code == 201, r.text
    assert r.json()["message"] == "sent"

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        rows = (await db.execute(select(Contact))).scalars().all()
    assert len(rows) == 1
    assert rows[0].subject == "Вопрос по курсу"
    assert rows[0].email == "ivan@example.com"


async def test_submit_contact_no_auth_required(client: AsyncClient):
    # public endpoint — works without a token
    r = await client.post("/api/v1/contact", json={**_MSG, "phone": None})
    assert r.status_code == 201


async def test_submit_contact_validation(client: AsyncClient):
    r = await client.post(
        "/api/v1/contact",
        json={"name": "x", "email": "not-an-email", "subject": "", "message": ""},
    )
    assert r.status_code == 422
