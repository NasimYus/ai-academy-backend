from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminUser, DbSession
from app.models.category import Category
from app.repositories import categories as categories_repo
from app.schemas.admin_category import AdminCategoryRead, CategoryCreate, CategoryUpdate
from app.schemas.common import error_responses

router = APIRouter(prefix="/admin/categories", tags=["admin-categories"])

_ADMIN_ERRORS = error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
_NOT_FOUND = error_responses(
    status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
)


def _read(c: Category) -> AdminCategoryRead:
    return AdminCategoryRead(
        id=c.id,
        parent_id=c.parent_id,
        title=c.title,
        slug=c.slug,
        icon=c.icon,
        order=c.order,
        enable=c.enable,
    )


@router.get("", response_model=list[AdminCategoryRead], responses=_ADMIN_ERRORS)
async def list_categories(_admin: AdminUser, db: DbSession) -> list[AdminCategoryRead]:
    """All categories (incl. sub-categories + disabled) for admin management."""
    return [_read(c) for c in await categories_repo.list_all(db)]


@router.post(
    "",
    response_model=AdminCategoryRead,
    status_code=status.HTTP_201_CREATED,
    responses=_ADMIN_ERRORS,
)
async def create_category(
    payload: CategoryCreate, _admin: AdminUser, db: DbSession
) -> AdminCategoryRead:
    data = payload.model_dump()
    data["slug"] = await categories_repo.unique_slug(db, payload.title)
    category = await categories_repo.create(db, data)
    return _read(category)


@router.put("/{category_id}", response_model=AdminCategoryRead, responses=_NOT_FOUND)
async def update_category(
    category_id: int, payload: CategoryUpdate, _admin: AdminUser, db: DbSession
) -> AdminCategoryRead:
    category = await categories_repo.get(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    changes = payload.model_dump(exclude_unset=True)
    category = await categories_repo.update(db, category, changes)
    return _read(category)


@router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_NOT_FOUND
)
async def delete_category(category_id: int, _admin: AdminUser, db: DbSession) -> None:
    category = await categories_repo.get(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    await categories_repo.delete(db, category)
