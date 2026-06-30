from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.accounting import Accounting, AccountingType, AccountingTypeAccount
from tests.conftest import register_verified_user


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_financial_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/panel/financial/account")).status_code == 401
    assert (await client.get("/api/v1/panel/financial/accounting")).status_code == 401
    assert (await client.get("/api/v1/panel/financial/offline-payments")).status_code == 401


async def test_fresh_student_has_zero_balance_and_empty_report(client: AsyncClient):
    token, _ = await register_verified_user(client, email="fin-empty@aiacademy.tj")
    assert (await client.get("/api/v1/panel/financial/account", headers=_auth(token))).json() == {
        "charge": 0.0
    }
    assert (
        await client.get("/api/v1/panel/financial/accounting", headers=_auth(token))
    ).json() == []


async def test_balance_sums_asset_ledger(client: AsyncClient):
    token, uid = await register_verified_user(client, email="fin-bal@aiacademy.tj")
    async with AsyncSessionLocal() as db:
        db.add_all(
            [
                Accounting(
                    user_id=uid,
                    amount=350,
                    type=AccountingType.addiction,
                    type_account=AccountingTypeAccount.asset,
                    description="Пополнение",
                ),
                Accounting(
                    user_id=uid,
                    amount=50,
                    type=AccountingType.deduction,
                    type_account=AccountingTypeAccount.asset,
                    description="Покупка",
                ),
            ]
        )
        await db.commit()

    balance = (await client.get("/api/v1/panel/financial/account", headers=_auth(token))).json()
    assert balance["charge"] == 300.0
    report = (await client.get("/api/v1/panel/financial/accounting", headers=_auth(token))).json()
    assert len(report) == 2


async def test_create_offline_payment_request(client: AsyncClient):
    token, _ = await register_verified_user(client, email="fin-offline@aiacademy.tj")
    r = await client.post(
        "/api/v1/panel/financial/offline-payments",
        headers=_auth(token),
        json={"amount": 350, "bank": "Alif Mobi", "reference_number": "807070789"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "waiting"

    history = (
        await client.get("/api/v1/panel/financial/offline-payments", headers=_auth(token))
    ).json()
    assert len(history) == 1
    assert history[0]["bank"] == "Alif Mobi"
