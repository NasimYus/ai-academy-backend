from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.newsletter import Newsletter


async def exists_by_email(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(Newsletter.id).where(Newsletter.email == email))
    return result.first() is not None


async def create(db: AsyncSession, *, email: str, user_id: int | None) -> Newsletter:
    newsletter = Newsletter(email=email, user_id=user_id)
    db.add(newsletter)
    await db.commit()
    await db.refresh(newsletter)
    return newsletter
