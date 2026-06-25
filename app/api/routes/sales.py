from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_level
from app.models.user import User
from app.repositories import sales as sales_repo
from app.schemas.common import error_responses
from app.schemas.sale import SaleRead, SellerSales

router = APIRouter(prefix="/panel/sales", tags=["sales"])

TeacherUser = Annotated[User, Depends(require_level("teacher"))]


@router.get(
    "",
    response_model=SellerSales,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def my_sales(current_user: TeacherUser, db: DbSession) -> SellerSales:
    """An instructor's sales (revenue) — paid items where they are the seller
    (legacy AccountingController sales list)."""
    rows = await sales_repo.seller_sales(db, current_user.id)
    income = await sales_repo.seller_income(db, current_user.id)
    return SellerSales(
        count=len(rows),
        total_income=income,
        sales=[SaleRead.model_validate(r, from_attributes=True) for r in rows],
    )
