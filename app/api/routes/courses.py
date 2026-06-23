from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models.comment import Comment
from app.models.content import Accessibility
from app.models.course import CourseType
from app.repositories import comments as comments_repo
from app.repositories import content as content_repo
from app.repositories import courses as courses_repo
from app.repositories import learning as learning_repo
from app.repositories import reviews as reviews_repo
from app.schemas.common import error_responses
from app.schemas.content import ChapterRead, ContentItem, CourseContent
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


def _content_item(obj, item_type: str, has_access: bool, completed: bool = False) -> ContentItem:
    accessible = obj.accessibility == Accessibility.free or has_access
    item = ContentItem(
        id=obj.id,
        type=item_type,
        title=obj.title,
        accessibility=obj.accessibility.value,
        order=obj.order,
        locked=not accessible,
        completed=completed,
    )
    if item_type == "file":
        item.file_type = obj.file_type
        item.volume = obj.volume
        item.description = obj.description
        if accessible:
            item.file = obj.file
    elif item_type == "text_lesson":
        item.image = obj.image
        item.study_time = obj.study_time
        item.summary = obj.summary
        if accessible:
            item.content = obj.content
    elif item_type == "session":
        item.session_date = obj.session_date
        item.duration = obj.duration
        item.description = obj.description
        if accessible:
            item.link = obj.link
    return item


@router.get(
    "/{slug}/content",
    response_model=CourseContent,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def get_course_content(slug: str, db: DbSession, current_user: OptionalUser) -> CourseContent:
    course = await courses_repo.get_by_slug(db, slug)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    has_access = await access.has_course_access(db, current_user, course)
    learned: set[tuple[str, int]] = (
        await learning_repo.learned_keys(db, current_user.id, course.id)
        if current_user is not None
        else set()
    )

    typed = (
        [(f, "file") for f in await content_repo.files_for_course(db, course.id)]
        + [(t, "text_lesson") for t in await content_repo.text_lessons_for_course(db, course.id)]
        + [(s, "session") for s in await content_repo.sessions_for_course(db, course.id)]
    )

    def items_for(chapter_id: int | None) -> list[ContentItem]:
        selected = sorted(
            (o for o in typed if o[0].chapter_id == chapter_id), key=lambda o: o[0].order
        )
        return [
            _content_item(obj, item_type, has_access, (item_type, obj.id) in learned)
            for obj, item_type in selected
        ]

    chapters = await content_repo.chapters_for_course(db, course.id)
    return CourseContent(
        course_id=course.id,
        chapters=[
            ChapterRead(id=c.id, title=c.title, order=c.order, items=items_for(c.id))
            for c in chapters
        ],
        items=items_for(None),
        has_access=has_access,
    )


class LearningToggle(BaseModel):
    item_type: Literal["file", "text_lesson", "session"]
    item_id: int
    learned: bool


@router.post(
    "/{course_id}/learning",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
    ),
)
async def toggle_learning(
    course_id: int, payload: LearningToggle, current_user: CurrentUser, db: DbSession
) -> dict[str, bool | str]:
    """Legacy WebinarController@learningStatus: mark/unmark a content item learned."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not await access.has_course_access(db, current_user, course):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_purchased")
    if not await content_repo.item_belongs_to_course(
        db, payload.item_type, payload.item_id, course.id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    await learning_repo.toggle(
        db,
        user_id=current_user.id,
        course_id=course.id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        learned=payload.learned,
    )
    return {"status": "ok", "learned": payload.learned}
