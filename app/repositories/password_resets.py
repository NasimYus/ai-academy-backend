from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordReset


async def create(db: AsyncSession, *, email: str, token: str) -> PasswordReset:
    row = PasswordReset(email=email, token=token)
    db.add(row)
    await db.commit()
    return row


async def find(db: AsyncSession, *, email: str, token: str) -> PasswordReset | None:
    result = await db.execute(
        select(PasswordReset).where(PasswordReset.email == email, PasswordReset.token == token)
    )
    return result.scalars().first()


async def delete_by_email(db: AsyncSession, email: str) -> None:
    await db.execute(delete(PasswordReset).where(PasswordReset.email == email))
