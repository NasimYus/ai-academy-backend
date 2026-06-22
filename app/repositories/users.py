from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User, UserStatus


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _role_id(db: AsyncSession, name: str) -> int:
    result = await db.execute(select(Role.id).where(Role.name == name))
    role_id = result.scalar_one_or_none()
    if role_id is None:
        raise ValueError(f"Role '{name}' is not seeded")
    return role_id


async def create(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    role_name: str = Role.USER,
    status: UserStatus = UserStatus.active,
    verified: bool = False,
) -> User:
    user = User(
        email=email,
        password=hash_password(password),
        full_name=full_name,
        role_name=role_name,
        role_id=await _role_id(db, role_name),
        status=status,
        verified=verified,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def set_verified(db: AsyncSession, user: User) -> User:
    user.verified = True
    user.status = UserStatus.active
    await db.commit()
    await db.refresh(user)
    return user
