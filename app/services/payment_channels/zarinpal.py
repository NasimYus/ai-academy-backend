from app.models.order import Order
from app.services.payment_channels.base import PaymentDriver


class ZarinpalChannel(PaymentDriver):
    """Zarinpal gateway (legacy Drivers/Zarinpal). Live mode needs `merchant_id`
    and a server-to-server authority request (wired per-deployment); test mode
    redirects to the local callback. Verify mirrors Zarinpal's `Status=OK`."""

    class_name = "Zarinpal"
    credential_items = ["merchant_id"]

    # Zarinpal hosted-payment page (authority appended per request).
    START_PAY = "https://www.zarinpal.com/pg/StartPay/"

    def payment_request(self, order: Order) -> str:
        if self.test_mode:
            return self.callback_url(order)
        # Live: requires the merchant_id + an authority token from Zarinpal's
        # request API (per-deployment HTTP). NOTE(gateway): authority fetch wired
        # at deploy time; we validate credentials and hand back the start page.
        self.require_credentials()
        return f"{self.START_PAY}{self.credential('merchant_id')}"

    def verify(self, params: dict) -> bool:
        return params.get("Status") in ("OK", "success")
