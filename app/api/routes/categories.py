from fastapi import APIRouter

from app.api.deps import DbSession
from app.repositories import categories as categories_repo
from app.repositories import courses as courses_repo
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
    counts = await courses_repo.counts_by_category(db)

    categories = []
    for top in tops:
        subs = children.get(top.id, [])
        sub_reads = [
            SubCategoryRead(
                id=sub.id, title=sub.title, icon=sub.icon, webinars_count=counts.get(sub.id, 0)
            )
            for sub in subs
        ]
        # Legacy: top count = sum of sub counts when subs exist, else own count.
        top_count = sum(s.webinars_count for s in sub_reads) if subs else counts.get(top.id, 0)
        categories.append(
            CategoryRead(
                id=top.id,
                title=top.title,
                color=colors.get(top.id),
                icon=top.icon,
                sub_categories=sub_reads,
                webinars_count=top_count,
            )
        )
    return CategoryList(count=len(categories), categories=categories)


@router.get("/trend-categories", response_model=TrendCategoryList)
async def list_trend_categories(db: DbSession) -> TrendCategoryList:
    rows = await categories_repo.list_trend(db)
    categories = [
        TrendCategoryRead(id=cat.id, title=cat.title, color=tc.color, icon=tc.icon or cat.icon)
        for tc, cat in rows
    ]
    return TrendCategoryList(count=len(categories), categories=categories)
