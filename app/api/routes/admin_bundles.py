from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import AdminUser, DbSession
from app.models.user import User
from app.repositories import bundles as bundles_repo
from app.schemas.bundle import BundleManageList, BundleManageRow
from app.schemas.common import error_responses

router = APIRouter(prefix="/admin/bundles", tags=["admin-bundles"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@router.get("", response_model=BundleManageList, responses=_ADMIN_ERRORS)
async def list_bundles(admin: AdminUser, db: DbSession) -> BundleManageList:
    """All course bundles for the admin list (legacy Admin\\BundleController@index)."""
    bundles = await bundles_repo.list_all(db)
    counts = await bundles_repo.webinar_counts(db, [b.id for b in bundles])
    teacher_ids = {b.teacher_id for b in bundles if b.teacher_id}
    names: dict[int, str | None] = {}
    if teacher_ids:
        rows = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(teacher_ids))
        )
        names = {uid: name for uid, name in rows.all()}
    return BundleManageList(
        total=len(bundles),
        bundles=[
            BundleManageRow(
                id=b.id,
                title=b.title,
                status=b.status,
                teacher_id=b.teacher_id,
                teacher_name=names.get(b.teacher_id),
                category=b.category.title if b.category else None,
                price=b.price,
                webinars_count=counts.get(b.id, 0),
                created_at=b.created_at,
            )
            for b in bundles
        ],
    )
