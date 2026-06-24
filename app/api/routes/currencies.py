from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import DbSession
from app.repositories import currencies as currencies_repo
from app.services.currency import _SIGNS

router = APIRouter(tags=["currencies"])


class CurrencyRead(BaseModel):
    code: str
    sign: str
    position: str
    separator: str
    decimals: int
    exchange_rate: float


@router.get("/currencies", response_model=list[CurrencyRead])
async def list_currencies(db: DbSession) -> list[CurrencyRead]:
    """Configured display currencies (legacy MultiCurrency::getCurrencies)."""
    rows = await currencies_repo.list_all(db)
    return [
        CurrencyRead(
            code=r.currency,
            sign=_SIGNS.get(r.currency.upper(), r.currency),
            position=r.currency_position,
            separator=r.currency_separator,
            decimals=r.currency_decimal or 0,
            exchange_rate=r.exchange_rate or 1.0,
        )
        for r in rows
    ]
