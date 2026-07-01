from fastapi import APIRouter, status

from app.api.deps import AdminUser, DbSession
from app.schemas.admin_marketing import AdminMarketing
from app.schemas.common import error_responses
from app.services import admin_marketing as service

router = APIRouter(prefix="/admin", tags=["admin-marketing"])


@router.get(
    "/marketing",
    response_model=AdminMarketing,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def admin_marketing(admin: AdminUser, db: DbSession) -> AdminMarketing:
    """Admin marketing dashboard aggregates (legacy Admin\\DashboardController@marketing)."""
    return await service.build(db)
