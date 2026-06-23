from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentSource


async def exists(db: AsyncSession, *, user_id: int, course_id: int) -> bool:
    result = await db.execute(
        select(Enrollment.id).where(
            Enrollment.user_id == user_id, Enrollment.course_id == course_id
        )
    )
    return result.first() is not None


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    course_id: int,
    source: EnrollmentSource = EnrollmentSource.free,
) -> Enrollment:
    enrollment = Enrollment(user_id=user_id, course_id=course_id, source=source)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def list_courses_for_user(db: AsyncSession, user_id: int) -> list[Course]:
    """Courses the user is enrolled in (for 'my courses')."""
    result = await db.execute(
        select(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id == user_id)
        .options(selectinload(Course.teacher), selectinload(Course.category))
        .order_by(Enrollment.created_at.desc())
    )
    return list(result.scalars().all())
