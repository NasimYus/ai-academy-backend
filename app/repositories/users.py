from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User, UserStatus


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_mobile(db: AsyncSession, mobile: str) -> User | None:
    result = await db.execute(select(User).where(User.mobile == mobile))
    return result.scalar_one_or_none()


async def get_by_field(db: AsyncSession, field: str, value: str) -> User | None:
    """Look a user up by 'email' or 'mobile'."""
    if field == "mobile":
        return await get_by_mobile(db, value)
    return await get_by_email(db, value)


async def _role_id(db: AsyncSession, name: str) -> int:
    result = await db.execute(select(Role.id).where(Role.name == name))
    role_id = result.scalar_one_or_none()
    if role_id is None:
        raise ValueError(f"Role '{name}' is not seeded")
    return role_id


async def create(
    db: AsyncSession,
    *,
    email: str | None = None,
    mobile: str | None = None,
    password: str,
    full_name: str | None = None,
    role_name: str = Role.USER,
    status: UserStatus = UserStatus.active,
    verified: bool = False,
    affiliate: bool = True,
) -> User:
    user = User(
        email=email,
        mobile=mobile,
        password=hash_password(password),
        full_name=full_name,
        role_name=role_name,
        role_id=await _role_id(db, role_name),
        status=status,
        verified=verified,
        affiliate=affiliate,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_by_provider_or_email(
    db: AsyncSession, *, provider_field: str, provider_id: str, email: str
) -> User | None:
    """Find a user by OAuth provider id (google_id/facebook_id) or email."""
    column = getattr(User, provider_field)
    result = await db.execute(
        select(User).where(or_(column == provider_id, User.email == email))
    )
    return result.scalars().first()


async def create_oauth(
    db: AsyncSession,
    *,
    email: str,
    full_name: str,
    provider_field: str,
    provider_id: str,
    role_name: str = Role.USER,
) -> User:
    """Create a verified, password-less account from an OAuth profile."""
    user = User(
        email=email,
        full_name=full_name,
        password=None,
        role_name=role_name,
        role_id=await _role_id(db, role_name),
        status=UserStatus.active,
        verified=True,
    )
    setattr(user, provider_field, provider_id)
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
