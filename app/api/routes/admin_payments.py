from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminUser, DbSession
from app.models.payment import PaymentChannel, PaymentChannelStatus
from app.repositories import payments as payments_repo
from app.schemas.admin_payment import (
    AdminPaymentChannelCreate,
    AdminPaymentChannelRead,
    AdminPaymentChannelUpdate,
)
from app.schemas.common import error_responses
from app.services.payment_channels import (
    credential_items_for,
    is_supported,
    show_test_mode_toggle_for,
)

router = APIRouter(prefix="/admin/payment-channels", tags=["admin-payments"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def _read(channel: PaymentChannel) -> AdminPaymentChannelRead:
    return AdminPaymentChannelRead(
        id=channel.id,
        title=channel.title,
        class_name=channel.class_name,
        image=channel.image,
        status=channel.status,
        test_mode=channel.test_mode,
        credentials=channel.credentials,
        currencies=channel.currencies,
        created_at=channel.created_at,
        credential_items=credential_items_for(channel.class_name),
        supported=is_supported(channel.class_name),
        show_test_mode_toggle=show_test_mode_toggle_for(channel.class_name),
    )


@router.get("", response_model=list[AdminPaymentChannelRead], responses=_ADMIN_ERRORS)
async def list_channels(admin: AdminUser, db: DbSession) -> list[AdminPaymentChannelRead]:
    """All gateways regardless of status, newest first (legacy index)."""
    channels = await payments_repo.list_all(db)
    return [_read(c) for c in channels]


@router.post(
    "",
    response_model=AdminPaymentChannelRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ADMIN_ERRORS,
)
async def create_channel(
    payload: AdminPaymentChannelCreate, admin: AdminUser, db: DbSession
) -> AdminPaymentChannelRead:
    """Register a gateway. NOTE: legacy seeds channels on install; we let admin
    add one by `class_name` (use a registered driver for it to work)."""
    channel = PaymentChannel(
        title=payload.title,
        class_name=payload.class_name,
        status=payload.status,
        test_mode=payload.test_mode,
        image=payload.image,
        credentials=payload.credentials,
        currencies=payload.currencies,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return _read(channel)


@router.get(
    "/{channel_id}",
    response_model=AdminPaymentChannelRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def get_channel(channel_id: int, admin: AdminUser, db: DbSession) -> AdminPaymentChannelRead:
    """A gateway + its credential contract (legacy edit)."""
    channel = await payments_repo.get_by_id(db, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return _read(channel)


@router.put(
    "/{channel_id}",
    response_model=AdminPaymentChannelRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def update_channel(
    channel_id: int, payload: AdminPaymentChannelUpdate, admin: AdminUser, db: DbSession
) -> AdminPaymentChannelRead:
    """Update title/image/status/credentials/currencies (legacy update)."""
    channel = await payments_repo.get_by_id(db, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    # Legacy overwrites title/image/credentials/currencies on every save; status
    # and test_mode keep their value unless explicitly provided.
    channel.title = payload.title
    channel.image = payload.image
    channel.credentials = payload.credentials
    channel.currencies = payload.currencies
    if payload.status is not None:
        channel.status = payload.status
    if payload.test_mode is not None:
        channel.test_mode = payload.test_mode
    await db.commit()
    await db.refresh(channel)
    return _read(channel)


@router.post(
    "/{channel_id}/toggle-status",
    response_model=AdminPaymentChannelRead,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def toggle_status(
    channel_id: int, admin: AdminUser, db: DbSession
) -> AdminPaymentChannelRead:
    """Flip active/inactive (legacy toggleStatus)."""
    channel = await payments_repo.get_by_id(db, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    channel.status = (
        PaymentChannelStatus.inactive
        if channel.status == PaymentChannelStatus.active
        else PaymentChannelStatus.active
    )
    await db.commit()
    await db.refresh(channel)
    return _read(channel)
