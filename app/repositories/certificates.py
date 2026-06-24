from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.certificate import Certificate


async def get_by_result(db: AsyncSession, quiz_result_id: int) -> Certificate | None:
    result = await db.execute(
        select(Certificate).where(Certificate.quiz_result_id == quiz_result_id)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, certificate_id: int) -> Certificate | None:
    result = await db.execute(
        select(Certificate)
        .where(Certificate.id == certificate_id)
        .options(selectinload(Certificate.student), selectinload(Certificate.quiz))
    )
    return result.scalar_one_or_none()


async def by_result_ids(db: AsyncSession, result_ids: list[int]) -> dict[int, Certificate]:
    if not result_ids:
        return {}
    result = await db.execute(select(Certificate).where(Certificate.quiz_result_id.in_(result_ids)))
    return {c.quiz_result_id: c for c in result.scalars().all()}


async def create(
    db: AsyncSession,
    *,
    quiz_id: int,
    quiz_result_id: int,
    student_id: int,
    user_grade: int | None,
) -> Certificate:
    certificate = Certificate(
        quiz_id=quiz_id,
        quiz_result_id=quiz_result_id,
        student_id=student_id,
        user_grade=user_grade,
    )
    db.add(certificate)
    await db.commit()
    await db.refresh(certificate)
    return certificate
