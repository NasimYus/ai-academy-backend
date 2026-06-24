from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.forum import CourseForum, CourseForumAnswer


def _thread_loaded():
    return (
        selectinload(CourseForum.user),
        selectinload(CourseForum.answers).selectinload(CourseForumAnswer.user),
    )


async def list_for_course(
    db: AsyncSession, course_id: int, search: str | None = None
) -> list[CourseForum]:
    stmt = (
        select(CourseForum)
        .where(CourseForum.course_id == course_id)
        .options(*_thread_loaded())
        .order_by(CourseForum.pin.desc(), CourseForum.id.desc())
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(CourseForum.title.ilike(like), CourseForum.description.ilike(like)))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_thread(db: AsyncSession, forum_id: int) -> CourseForum | None:
    result = await db.execute(
        select(CourseForum).where(CourseForum.id == forum_id).options(*_thread_loaded())
    )
    return result.scalar_one_or_none()


async def create_thread(
    db: AsyncSession, *, course_id: int, user_id: int, title: str, description: str
) -> CourseForum:
    row = CourseForum(
        course_id=course_id, user_id=user_id, title=title, description=description, pin=False
    )
    db.add(row)
    await db.commit()
    return await get_thread(db, row.id)


async def save_thread(db: AsyncSession, forum: CourseForum) -> CourseForum:
    await db.commit()
    return await get_thread(db, forum.id)


async def list_answers(db: AsyncSession, forum_id: int) -> list[CourseForumAnswer]:
    result = await db.execute(
        select(CourseForumAnswer)
        .where(CourseForumAnswer.forum_id == forum_id)
        .options(selectinload(CourseForumAnswer.user))
        .order_by(CourseForumAnswer.pin.desc(), CourseForumAnswer.id.asc())
    )
    return list(result.scalars().all())


async def get_answer(db: AsyncSession, answer_id: int) -> CourseForumAnswer | None:
    result = await db.execute(
        select(CourseForumAnswer)
        .where(CourseForumAnswer.id == answer_id)
        .options(selectinload(CourseForumAnswer.user))
    )
    return result.scalar_one_or_none()


async def create_answer(
    db: AsyncSession, *, forum_id: int, user_id: int, description: str
) -> CourseForumAnswer:
    row = CourseForumAnswer(
        forum_id=forum_id, user_id=user_id, description=description, pin=False, resolved=False
    )
    db.add(row)
    await db.commit()
    return await get_answer(db, row.id)


async def save_answer(db: AsyncSession, answer: CourseForumAnswer) -> CourseForumAnswer:
    await db.commit()
    return await get_answer(db, answer.id)


async def counts(db: AsyncSession, course_id: int) -> dict[str, int]:
    """Aggregate forum stats for a course (legacy index payload)."""
    forum_ids_subq = select(CourseForum.id).where(CourseForum.course_id == course_id).subquery()

    questions_count = await db.scalar(
        select(func.count()).select_from(CourseForum).where(CourseForum.course_id == course_id)
    )
    resolved_forum_ids = (
        select(CourseForumAnswer.forum_id)
        .where(
            CourseForumAnswer.forum_id.in_(select(forum_ids_subq.c.id)),
            CourseForumAnswer.resolved.is_(True),
        )
        .distinct()
    )
    resolved_count = await db.scalar(
        select(func.count()).select_from(resolved_forum_ids.subquery())
    )
    forums_with_answers = (
        select(CourseForumAnswer.forum_id)
        .where(CourseForumAnswer.forum_id.in_(select(forum_ids_subq.c.id)))
        .distinct()
    )
    comments_count = await db.scalar(
        select(func.count()).select_from(forums_with_answers.subquery())
    )
    active_users_count = await db.scalar(
        select(func.count(distinct(CourseForumAnswer.user_id))).where(
            CourseForumAnswer.forum_id.in_(select(forum_ids_subq.c.id))
        )
    )
    return {
        "questions_count": questions_count or 0,
        "resolved_count": resolved_count or 0,
        "open_questions_count": (questions_count or 0) - (resolved_count or 0),
        "comments_count": comments_count or 0,
        "active_users_count": active_users_count or 0,
    }
