from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models.accounting import AccountingType, AccountingTypeAccount
from app.repositories import accounting as accounting_repo
from app.schemas.accounting import (
    AccountBalance,
    AccountingRead,
    OfflinePaymentCreate,
    OfflinePaymentRead,
)
from app.schemas.common import error_responses

router = APIRouter(prefix="/panel/financial", tags=["financial"])


@router.get(
    "/account",
    response_model=AccountBalance,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def account_balance(current_user: CurrentUser, db: DbSession) -> AccountBalance:
    """The student's wallet balance (legacy getAccountingCharge)."""
    return AccountBalance(charge=await accounting_repo.charge_for_user(db, current_user.id))


@router.get(
    "/accounting",
    response_model=list[AccountingRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def financial_report(
    current_user: CurrentUser,
    db: DbSession,
    type: Annotated[AccountingType | None, Query()] = None,
    type_account: Annotated[AccountingTypeAccount | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[AccountingRead]:
    """Financial report — the student's ledger rows (legacy financial summary)."""
    rows = await accounting_repo.list_for_user(
        db,
        current_user.id,
        type_=type,
        type_account=type_account,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        AccountingRead(
            id=r.id,
            amount=float(r.amount),
            type=r.type.value,
            type_account=r.type_account.value,
            description=r.description,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get(
    "/offline-payments",
    response_model=list[OfflinePaymentRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def offline_payments(current_user: CurrentUser, db: DbSession) -> list[OfflinePaymentRead]:
    """The student's offline top-up requests (legacy offline payments history)."""
    rows = await accounting_repo.list_offline_for_user(db, current_user.id)
    return [
        OfflinePaymentRead(
            id=r.id,
            bank=r.bank,
            reference_number=r.reference_number,
            amount=float(r.amount),
            status=r.status.value,
            attachment=r.attachment,
            pay_date=r.pay_date,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post(
    "/offline-payments",
    response_model=OfflinePaymentRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def create_offline_payment(
    payload: OfflinePaymentCreate, current_user: CurrentUser, db: DbSession
) -> OfflinePaymentRead:
    """Submit an offline (bank-transfer) top-up request — created `waiting`;
    admin approval (→ wallet credit) is deferred (legacy charge → offline)."""
    payment = await accounting_repo.create_offline(
        db,
        user_id=current_user.id,
        amount=payload.amount,
        bank=payload.bank,
        reference_number=payload.reference_number,
        pay_date=payload.pay_date,
    )
    return OfflinePaymentRead(
        id=payment.id,
        bank=payment.bank,
        reference_number=payment.reference_number,
        amount=float(payment.amount),
        status=payment.status.value,
        attachment=payment.attachment,
        pay_date=payment.pay_date,
        created_at=payment.created_at,
    )
