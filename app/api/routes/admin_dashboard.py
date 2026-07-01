from fastapi import APIRouter, status

from app.api.deps import AdminUser, DbSession
from app.schemas.admin_dashboard import AdminDashboard
from app.schemas.common import error_responses
from app.services import admin_dashboard as service

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get(
    "/dashboard",
    response_model=AdminDashboard,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
)
async def admin_dashboard(admin: AdminUser, db: DbSession) -> AdminDashboard:
    """Admin general dashboard aggregates (legacy Admin\\DashboardController)."""
    return await service.build(db)
