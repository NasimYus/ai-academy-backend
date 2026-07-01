from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.course_relation import Prerequisite, RelatedCourse


async def list_prerequisites(db: AsyncSession, course_id: int) -> list[tuple[Prerequisite, str]]:
    result = await db.execute(
        select(Prerequisite, Course.title)
        .join(Course, Course.id == Prerequisite.prerequisite_id)
        .where(Prerequisite.course_id == course_id)
        .order_by(Prerequisite.order.asc(), Prerequisite.id.asc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def add_prerequisite(
    db: AsyncSession, course_id: int, prerequisite_id: int, required: bool
) -> Prerequisite:
    obj = Prerequisite(course_id=course_id, prerequisite_id=prerequisite_id, required=required)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_prerequisite(db: AsyncSession, prerequisite_row_id: int) -> Prerequisite | None:
    return await db.get(Prerequisite, prerequisite_row_id)


async def list_related(db: AsyncSession, course_id: int) -> list[tuple[RelatedCourse, str]]:
    result = await db.execute(
        select(RelatedCourse, Course.title)
        .join(Course, Course.id == RelatedCourse.related_id)
        .where(RelatedCourse.course_id == course_id)
        .order_by(RelatedCourse.id.asc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def add_related(db: AsyncSession, course_id: int, related_id: int) -> RelatedCourse:
    obj = RelatedCourse(course_id=course_id, related_id=related_id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_related(db: AsyncSession, related_row_id: int) -> RelatedCourse | None:
    return await db.get(RelatedCourse, related_row_id)


async def delete_relation(db: AsyncSession, obj) -> None:
    await db.delete(obj)
    await db.commit()
