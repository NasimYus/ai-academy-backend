"""Payment gateway driver base — faithful port of legacy `PaymentChannels/`.

Each driver wraps a configured `PaymentChannel` and implements the legacy
`IChannel` contract: build a redirect for `payment_request(order)` and validate
the gateway callback in `verify(params)`. Per-gateway merchant credentials live
on `PaymentChannel.credentials` (JSON); `credential_items` lists the required
keys (legacy `getCredentialItems()`), so admin/UI knows what to collect.

Real gateways need live merchant accounts + external HTTP, so out of the box
drivers run in *test mode* (driver `test_mode` or the channel's `test_mode`):
they redirect to the local callback and verify by the returned status, which is
exactly how the legacy `test_mode` path behaves.
"""

from __future__ import annotations

from app.models.order import Order
from app.models.payment import PaymentChannel


class MissingCredentials(Exception):
    """A live gateway is missing one of its required credential keys."""


class PaymentDriver:
    # Subclasses set these (legacy class_name + getCredentialItems()).
    class_name: str = "Base"
    credential_items: list[str] = []

    def __init__(self, channel: PaymentChannel) -> None:
        self.channel = channel
        self.credentials: dict = channel.credentials or {}

    @property
    def test_mode(self) -> bool:
        return self.channel.test_mode

    def credential(self, key: str) -> str | None:
        return self.credentials.get(key)

    def require_credentials(self) -> None:
        """Ensure every declared credential is present (live mode only)."""
        missing = [k for k in self.credential_items if not self.credentials.get(k)]
        if missing:
            raise MissingCredentials(", ".join(missing))

    def callback_url(self, order: Order) -> str:
        """Where the gateway returns the user; the SPA then POSTs /payments/verify."""
        return (
            f"/payment/callback?order_id={order.id}"
            f"&gateway={self.class_name}&channel_id={self.channel.id}"
        )

    def payment_request(self, order: Order) -> str:
        """Return the URL to send the user to in order to pay."""
        raise NotImplementedError

    def verify(self, params: dict) -> bool:
        """True if the gateway callback indicates a successful payment."""
        raise NotImplementedError
