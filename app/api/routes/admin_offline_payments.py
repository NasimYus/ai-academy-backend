from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUser, DbSession
from app.models.accounting import OfflinePayment, OfflinePaymentStatus
from app.repositories import accounting as accounting_repo
from app.schemas.admin_offline_payment import AdminOfflinePaymentRead
from app.schemas.common import error_responses

router = APIRouter(prefix="/admin/offline-payments", tags=["admin-offline-payments"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
_NOT_FOUND = error_responses(
    status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
)
_ACTION_ERRORS = error_responses(
    status.HTTP_401_UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
    status.HTTP_422_UNPROCESSABLE_CONTENT,
)


def _read(payment: OfflinePayment, name: str | None, email: str | None) -> AdminOfflinePaymentRead:
    return AdminOfflinePaymentRead(
        id=payment.id,
        user_id=payment.user_id,
        user_name=name,
        user_email=email,
        bank=payment.bank,
        reference_number=payment.reference_number,
        amount=float(payment.amount),
        status=payment.status.value,
        pay_date=payment.pay_date,
        created_at=payment.created_at,
    )


@router.get("", response_model=list[AdminOfflinePaymentRead], responses=_ADMIN_ERRORS)
async def list_offline_payments(
    _admin: AdminUser,
    db: DbSession,
    status_: Annotated[OfflinePaymentStatus | None, Query(alias="status")] = None,
) -> list[AdminOfflinePaymentRead]:
    """Offline top-up requests for review (defaults to all; filter by status)."""
    rows = await accounting_repo.list_offline_all(db, status_)
    return [_read(payment, name, email) for payment, name, email in rows]


async def _get_or_404(db: DbSession, payment_id: int) -> OfflinePayment:
    payment = await accounting_repo.get_offline(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post(
    "/{payment_id}/approve", response_model=AdminOfflinePaymentRead, responses=_ACTION_ERRORS
)
async def approve_offline_payment(
    payment_id: int, _admin: AdminUser, db: DbSession
) -> AdminOfflinePaymentRead:
    """Approve a top-up → credits the user's wallet (legacy approved → charge wallet)."""
    payment = await _get_or_404(db, payment_id)
    if payment.status != OfflinePaymentStatus.waiting:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_waiting")
    payment = await accounting_repo.approve_offline(db, payment)
    return _read(payment, None, None)


@router.post(
    "/{payment_id}/reject", response_model=AdminOfflinePaymentRead, responses=_ACTION_ERRORS
)
async def reject_offline_payment(
    payment_id: int, _admin: AdminUser, db: DbSession
) -> AdminOfflinePaymentRead:
    payment = await _get_or_404(db, payment_id)
    if payment.status != OfflinePaymentStatus.waiting:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_waiting")
    payment = await accounting_repo.reject_offline(db, payment)
    return _read(payment, None, None)
