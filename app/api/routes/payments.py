from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.order import OrderStatus
from app.repositories import orders as orders_repo
from app.repositories import payments as payments_repo
from app.schemas.common import error_responses
from app.schemas.order import OrderRead
from app.schemas.payment import (
    PaymentChannelRead,
    PaymentRequestInput,
    PaymentRequestResult,
    PaymentVerifyInput,
)
from app.services import payments as payment_service
from app.services.order_presenter import order_read

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get(
    "/channels",
    response_model=list[PaymentChannelRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def list_channels(current_user: CurrentUser, db: DbSession) -> list[PaymentChannelRead]:
    """Active payment gateways the user can pay with."""
    channels = await payments_repo.list_active(db)
    return [PaymentChannelRead(id=c.id, title=c.title, class_name=c.class_name) for c in channels]


@router.post(
    "/request",
    response_model=PaymentRequestResult,
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def payment_request(
    payload: PaymentRequestInput, current_user: CurrentUser, db: DbSession
) -> PaymentRequestResult:
    """Begin paying a pending order via a gateway (legacy PaymentsController@paymentRequest)."""
    order = await orders_repo.get_owned(db, payload.order_id, current_user.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not_pending")

    channel = await payments_repo.get_active(db, payload.gateway_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="disabled_gateway")

    redirect_url = await payment_service.start(db, order, channel)
    return PaymentRequestResult(
        order_id=order.id,
        gateway=channel.class_name,
        status=order.status.value,
        redirect_url=redirect_url,
    )


@router.post(
    "/verify/{gateway}",
    response_model=OrderRead,
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def payment_verify(
    gateway: str, payload: PaymentVerifyInput, current_user: CurrentUser, db: DbSession
) -> OrderRead:
    """Gateway callback/return: settle a `paying` order (legacy PaymentController@paymentVerify)."""
    order = await orders_repo.get_owned(db, payload.order_id, current_user.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status != OrderStatus.paying:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="not_paying")

    if payload.status == "success":
        await payment_service.complete(db, order)
    else:
        await payment_service.fail(db, order)

    order = await orders_repo.reload(db, order.id)
    return order_read(order)
