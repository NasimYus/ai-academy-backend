"""Driver registry — faithful port of legacy `ChannelManager::makeChannel`.

Resolve a `PaymentChannel` to its driver by `class_name`. Add a gateway by
implementing a `PaymentDriver` subclass and registering it here (mirrors the
legacy `PaymentChannels/Drivers/<Name>/Channel.php` convention). Unknown drivers
fall back to the Sandbox so a misconfigured channel never hard-fails checkout.
"""

from app.models.payment import PaymentChannel
from app.services.payment_channels.base import PaymentDriver
from app.services.payment_channels.sandbox import SandboxChannel
from app.services.payment_channels.zarinpal import ZarinpalChannel

_DRIVERS: dict[str, type[PaymentDriver]] = {
    SandboxChannel.class_name: SandboxChannel,
    ZarinpalChannel.class_name: ZarinpalChannel,
}


def make_channel(channel: PaymentChannel) -> PaymentDriver:
    driver_cls = _DRIVERS.get(channel.class_name, SandboxChannel)
    return driver_cls(channel)


def credential_items_for(class_name: str) -> list[str]:
    """The credential keys a gateway needs (legacy getCredentialItems())."""
    driver_cls = _DRIVERS.get(class_name)
    return list(driver_cls.credential_items) if driver_cls else []


def is_supported(class_name: str) -> bool:
    return class_name in _DRIVERS


def show_test_mode_toggle_for(class_name: str) -> bool:
    """Whether the admin UI should offer a test-mode toggle (legacy
    getShowTestModeToggle())."""
    driver_cls = _DRIVERS.get(class_name)
    return driver_cls.show_test_mode_toggle if driver_cls else True


def known_drivers() -> list[str]:
    """All registered gateway driver class_names."""
    return list(_DRIVERS.keys())
