from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession, OptionalUser
from app.models.comment import Comment
from app.models.course import CourseType
from app.repositories import comments as comments_repo
from app.repositories import courses as courses_repo
from app.repositories import reviews as reviews_repo
from app.schemas.common import error_responses
from app.schemas.course import CourseDetail, CourseRateType, CourseRead
from app.schemas.review import CommentRead, ReviewRead
from app.schemas.user import UserBrief
from app.services import access
from app.services.course_presenter import to_brief, to_detail

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseRead])
async def list_courses(
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cat: int | None = Query(None, description="category id"),
    free: bool | None = Query(None),
    course_type: Annotated[CourseType | None, Query(alias="type")] = None,
    upcoming: bool | None = Query(None),
    downloadable: bool | None = Query(None),
    reward: bool | None = Query(None),
    sort: str | None = Query(None, description="newest|oldest|expensive|cheapest"),
) -> list[CourseRead]:
    courses = await courses_repo.list_courses(
        db,
        category=cat,
        free=free,
        course_type=course_type,
        upcoming=upcoming,
        downloadable=downloadable,
        reward=reward,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return [to_brief(c) for c in courses]


@router.get(
    "/{slug}",
    response_model=CourseDetail,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_course(slug: str, db: DbSession, current_user: OptionalUser) -> CourseDetail:
    course = await courses_repo.get_by_slug(db, slug)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    reviews = await reviews_repo.list_for_course(db, course.id)
    agg = await reviews_repo.aggregate_for_course(db, course.id)
    comments = await comments_repo.list_for_course(db, course.id)
    has_access = await access.has_course_access(db, current_user, course)

    return to_detail(course).model_copy(
        update={
            "auth": current_user is not None,
            "auth_has_bought": has_access,
            "rate": agg["rate"],
            "reviews_count": agg["count"],
            "rate_type": CourseRateType(
                content_quality=agg["content_quality"],
                instructor_skills=agg["instructor_skills"],
                purchase_worth=agg["purchase_worth"],
                support_quality=agg["support_quality"],
            ),
            "reviews": [
                ReviewRead(
                    id=r.id,
                    user=UserBrief.model_validate(r.user),
                    content_quality=r.content_quality,
                    instructor_skills=r.instructor_skills,
                    purchase_worth=r.purchase_worth,
                    support_quality=r.support_quality,
                    rates=r.rates,
                    description=r.description,
                    created_at=r.created_at,
                )
                for r in reviews
            ],
            "comments": _comment_tree(comments),
        }
    )


def _comment_tree(comments: list[Comment]) -> list[CommentRead]:
    """Group flat comments into top-level entries with one level of replies."""
    nodes: dict[int, CommentRead] = {}
    for c in comments:
        nodes[c.id] = CommentRead(
            id=c.id,
            user=UserBrief.model_validate(c.user),
            comment=c.comment,
            created_at=c.created_at,
            replies=[],
        )
    roots: list[CommentRead] = []
    for c in comments:
        node = nodes[c.id]
        parent = nodes.get(c.reply_id) if c.reply_id else None
        if parent is not None:
            parent.replies.append(node)
        else:
            roots.append(node)
    return roots
