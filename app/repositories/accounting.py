from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import (
    Accounting,
    AccountingType,
    AccountingTypeAccount,
    OfflinePayment,
    OfflinePaymentStatus,
)


async def charge_for_user(db: AsyncSession, user_id: int) -> float:
    """Wallet balance — legacy `getAccountingCharge`: asset additions minus
    deductions (system/tax excluded), floored at 0."""
    base = (
        select(func.coalesce(func.sum(Accounting.amount), 0))
        .where(
            Accounting.user_id == user_id,
            Accounting.type_account == AccountingTypeAccount.asset,
            Accounting.system.is_(False),
            Accounting.tax.is_(False),
        )
    )
    additions = await db.scalar(base.where(Accounting.type == AccountingType.addiction))
    deductions = await db.scalar(base.where(Accounting.type == AccountingType.deduction))
    charge = float(additions or 0) - float(deductions or 0)
    return charge if charge > 0 else 0


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    type_: AccountingType | None = None,
    type_account: AccountingTypeAccount | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Accounting]:
    """Financial report rows (legacy AccountingSummaryController: non-system,
    non-tax), newest first, with the same optional filters."""
    stmt = select(Accounting).where(
        Accounting.user_id == user_id,
        Accounting.system.is_(False),
        Accounting.tax.is_(False),
    )
    if type_ is not None:
        stmt = stmt.where(Accounting.type == type_)
    if type_account is not None:
        stmt = stmt.where(Accounting.type_account == type_account)
    if search:
        stmt = stmt.where(Accounting.description.ilike(f"%{search}%"))
    if date_from is not None:
        stmt = stmt.where(Accounting.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Accounting.created_at <= date_to)
    result = await db.execute(stmt.order_by(Accounting.created_at.desc(), Accounting.id.desc()))
    return list(result.scalars().all())


async def list_offline_for_user(db: AsyncSession, user_id: int) -> list[OfflinePayment]:
    result = await db.execute(
        select(OfflinePayment)
        .where(OfflinePayment.user_id == user_id)
        .order_by(OfflinePayment.created_at.desc())
    )
    return list(result.scalars().all())


async def create_offline(
    db: AsyncSession,
    *,
    user_id: int,
    amount: float,
    bank: str | None,
    reference_number: str | None,
    pay_date: datetime | None,
) -> OfflinePayment:
    payment = OfflinePayment(
        user_id=user_id,
        amount=amount,
        bank=bank,
        reference_number=reference_number,
        pay_date=pay_date,
        status=OfflinePaymentStatus.waiting,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment
