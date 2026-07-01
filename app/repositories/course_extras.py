from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_extra import CompanyLogo, CourseExtra, ExtraType, Faq


async def list_faqs(db: AsyncSession, course_id: int) -> list[Faq]:
    result = await db.execute(
        select(Faq).where(Faq.course_id == course_id).order_by(Faq.id.asc())
    )
    return list(result.scalars().all())


async def add_faq(
    db: AsyncSession, course_id: int, question: str, answer: str | None, locale: str
) -> Faq:
    obj = Faq(course_id=course_id, question=question, answer=answer, locale=locale)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_faq(db: AsyncSession, faq_id: int) -> Faq | None:
    return await db.get(Faq, faq_id)


async def list_extras(db: AsyncSession, course_id: int) -> list[CourseExtra]:
    result = await db.execute(
        select(CourseExtra).where(CourseExtra.course_id == course_id).order_by(CourseExtra.id.asc())
    )
    return list(result.scalars().all())


async def add_extra(
    db: AsyncSession, course_id: int, extra_type: ExtraType, title: str, locale: str
) -> CourseExtra:
    obj = CourseExtra(course_id=course_id, type=extra_type, title=title, locale=locale)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_extra(db: AsyncSession, extra_id: int) -> CourseExtra | None:
    return await db.get(CourseExtra, extra_id)


async def list_logos(db: AsyncSession, course_id: int) -> list[CompanyLogo]:
    result = await db.execute(
        select(CompanyLogo).where(CompanyLogo.course_id == course_id).order_by(CompanyLogo.id.asc())
    )
    return list(result.scalars().all())


async def add_logo(db: AsyncSession, course_id: int, image: str) -> CompanyLogo:
    obj = CompanyLogo(course_id=course_id, image=image)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_logo(db: AsyncSession, logo_id: int) -> CompanyLogo | None:
    return await db.get(CompanyLogo, logo_id)


async def delete_row(db: AsyncSession, obj) -> None:
    await db.delete(obj)
    await db.commit()
