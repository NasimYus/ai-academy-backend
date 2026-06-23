from fastapi import APIRouter

from app.api.deps import DbSession
from app.repositories import categories as categories_repo
from app.schemas.category import (
    CategoryList,
    CategoryRead,
    SubCategoryRead,
    TrendCategoryList,
    TrendCategoryRead,
)

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=CategoryList)
async def list_categories(db: DbSession) -> CategoryList:
    tops = await categories_repo.list_top_level(db)
    children = await categories_repo.children_by_parent(db)
    colors = await categories_repo.color_by_category(db)

    # NOTE(2.2): webinars_count stays 0 until Course gains a category_id link.
    categories = [
        CategoryRead(
            id=top.id,
            title=top.title,
            color=colors.get(top.id),
            icon=top.icon,
            sub_categories=[
                SubCategoryRead(id=sub.id, title=sub.title, icon=sub.icon, webinars_count=0)
                for sub in children.get(top.id, [])
            ],
            webinars_count=0,
        )
        for top in tops
    ]
    return CategoryList(count=len(categories), categories=categories)


@router.get("/trend-categories", response_model=TrendCategoryList)
async def list_trend_categories(db: DbSession) -> TrendCategoryList:
    rows = await categories_repo.list_trend(db)
    categories = [
        TrendCategoryRead(id=cat.id, title=cat.title, color=tc.color, icon=tc.icon or cat.icon)
        for tc, cat in rows
    ]
    return TrendCategoryList(count=len(categories), categories=categories)
