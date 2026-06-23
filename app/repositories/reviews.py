from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import CourseReview, ReviewStatus


async def list_for_course(db: AsyncSession, course_id: int) -> list[CourseReview]:
    result = await db.execute(
        select(CourseReview)
        .where(CourseReview.course_id == course_id, CourseReview.status == ReviewStatus.active)
        .options(selectinload(CourseReview.user))
        .order_by(CourseReview.created_at.desc())
    )
    return list(result.scalars().all())


async def aggregate_for_course(db: AsyncSession, course_id: int) -> dict[str, float | int]:
    """Avg of each rating dimension + overall rate and count (active reviews)."""
    result = await db.execute(
        select(
            func.count(CourseReview.id),
            func.coalesce(func.avg(CourseReview.rates), 0),
            func.coalesce(func.avg(CourseReview.content_quality), 0),
            func.coalesce(func.avg(CourseReview.instructor_skills), 0),
            func.coalesce(func.avg(CourseReview.purchase_worth), 0),
            func.coalesce(func.avg(CourseReview.support_quality), 0),
        ).where(CourseReview.course_id == course_id, CourseReview.status == ReviewStatus.active)
    )
    count, rate, content, instructor, worth, support = result.one()
    return {
        "count": count,
        "rate": round(float(rate), 2),
        "content_quality": round(float(content), 2),
        "instructor_skills": round(float(instructor), 2),
        "purchase_worth": round(float(worth), 2),
        "support_quality": round(float(support), 2),
    }
