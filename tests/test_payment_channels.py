import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.services.payment_channels import (
    MissingCredentials,
    credential_items_for,
    is_supported,
    make_channel,
)
from app.services.payment_channels.sandbox import SandboxChannel
from app.services.payment_channels.zarinpal import ZarinpalChannel
from tests.conftest import register_verified_user


async def _seed_channel(**kw) -> int:
    async with AsyncSessionLocal() as db:
        ch = PaymentChannel(status=PaymentChannelStatus.active, **kw)
        db.add(ch)
        await db.commit()
        return ch.id


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- unit: registry + drivers ---


def test_registry_resolves_by_class_name():
    sandbox = make_channel(PaymentChannel(title="S", class_name="Sandbox"))
    assert isinstance(sandbox, SandboxChannel)
    zarin = make_channel(PaymentChannel(title="Z", class_name="Zarinpal"))
    assert isinstance(zarin, ZarinpalChannel)


def test_unknown_driver_falls_back_to_sandbox():
    driver = make_channel(PaymentChannel(title="X", class_name="Stripe"))
    assert isinstance(driver, SandboxChannel)
    assert is_supported("Stripe") is False
    assert credential_items_for("Stripe") == []


def test_zarinpal_credential_items():
    assert credential_items_for("Zarinpal") == ["merchant_id"]


def test_sandbox_request_and_verify():
    ch = PaymentChannel(id=7, title="S", class_name="Sandbox", test_mode=True)
    driver = make_channel(ch)
    url = driver.payment_request(_FakeOrder(42))
    assert "order_id=42" in url and "gateway=Sandbox" in url
    assert driver.verify({"status": "success"}) is True
    assert driver.verify({"status": "failed"}) is False


def test_zarinpal_test_mode_redirects_local():
    ch = PaymentChannel(id=3, title="Z", class_name="Zarinpal", test_mode=True)
    driver = make_channel(ch)
    assert "/payment/callback" in driver.payment_request(_FakeOrder(9))
    assert driver.verify({"Status": "OK"}) is True
    assert driver.verify({"Status": "NOK"}) is False


def test_zarinpal_live_requires_credentials():
    ch = PaymentChannel(id=4, title="Z", class_name="Zarinpal", test_mode=False, credentials={})
    with pytest.raises(MissingCredentials):
        make_channel(ch).payment_request(_FakeOrder(1))

    ok = PaymentChannel(
        id=5, title="Z", class_name="Zarinpal", test_mode=False, credentials={"merchant_id": "m1"}
    )
    assert make_channel(ok).payment_request(_FakeOrder(1)).endswith("m1")


class _FakeOrder:
    def __init__(self, oid: int) -> None:
        self.id = oid


# --- API: channels expose the credential contract ---


async def test_channels_endpoint_exposes_credentials(client: AsyncClient):
    token, _ = await register_verified_user(client)
    await _seed_channel(title="Zarinpal", class_name="Zarinpal", image="/media/z.png")
    await _seed_channel(title="Stripe", class_name="Stripe")  # no driver registered

    r = await client.get("/api/v1/payments/channels", headers=_auth(token))
    assert r.status_code == 200
    by_name = {c["class_name"]: c for c in r.json()}
    assert by_name["Zarinpal"]["credential_items"] == ["merchant_id"]
    assert by_name["Zarinpal"]["supported"] is True
    assert by_name["Zarinpal"]["image"] == "/media/z.png"
    assert by_name["Stripe"]["supported"] is False
    assert by_name["Stripe"]["credential_items"] == []
