"""Multi-currency display (F.5) — parity of legacy MultiCurrency helpers.

Prices are stored in the default currency; `convert` applies a currency's
exchange rate and `fmt` renders it with the right sign/position/decimals.
Server-side money (cart/orders) stays in the base currency — conversion here is
presentation only.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.currency import Currency
from app.repositories import currencies as currencies_repo

# Common ISO code → symbol (fallback: the code itself). Legacy currencySign().
_SIGNS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "RUB": "₽",
    "TJS": "SM",
    "KZT": "₸",
    "UAH": "₴",
}


@dataclass
class CurrencyItem:
    code: str
    position: str = "left"
    separator: str = "dot"
    decimals: int = 0
    exchange_rate: float = 1.0

    @property
    def sign(self) -> str:
        return _SIGNS.get(self.code.upper(), self.code)


def _item(row: Currency) -> CurrencyItem:
    return CurrencyItem(
        code=row.currency,
        position=row.currency_position,
        separator=row.currency_separator,
        decimals=row.currency_decimal or 0,
        exchange_rate=row.exchange_rate or 1.0,
    )


def default_item() -> CurrencyItem:
    return CurrencyItem(code=settings.default_currency)


async def resolve(db: AsyncSession, code: str | None) -> CurrencyItem:
    """Pick the currency to display in: requested code if active, else default."""
    if code:
        row = await currencies_repo.get_by_code(db, code.upper())
        if row is not None:
            return _item(row)
    row = await currencies_repo.get_by_code(db, settings.default_currency)
    return _item(row) if row is not None else default_item()


def convert(price: float, item: CurrencyItem) -> float:
    return price * item.exchange_rate if item.exchange_rate else price


def fmt(price: float, item: CurrencyItem) -> str | None:
    """Format a base price in the target currency (legacy addCurrencyToPrice)."""
    if not price or price <= 0:
        return None
    amount = convert(price, item)
    thousands = "," if item.separator == "comma" else " "
    number = f"{amount:,.{item.decimals}f}".replace(",", " ")  # group with NBSP
    if thousands == ",":
        number = number.replace(" ", ",")
    sign = item.sign
    if item.position == "left":
        return f"{sign}{number}"
    if item.position == "left_with_space":
        return f"{sign} {number}"
    if item.position == "right_with_space":
        return f"{number} {sign}"
    return f"{number}{sign}"
