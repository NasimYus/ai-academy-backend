from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User, UserStatus


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def admin_list(
    db: AsyncSession,
    *,
    role_name: str | None = None,
    status: UserStatus | None = None,
    banned: bool | None = None,
    limit: int = 200,
) -> list[User]:
    """Users for admin management, newest first (optionally filtered)."""
    stmt = select(User)
    if role_name is not None:
        stmt = stmt.where(User.role_name == role_name)
    if status is not None:
        stmt = stmt.where(User.status == status)
    if banned is not None:
        stmt = stmt.where(User.ban.is_(banned))
    stmt = stmt.order_by(User.id.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def list_providers(
    db: AsyncSession,
    roles: list[str],
    *,
    search: str | None = None,
    sort: str | None = None,
) -> list[User]:
    """Legacy handleProviders: active, non-banned users in the given roles."""
    now = datetime.now(UTC)
    stmt = select(User).where(
        User.status == UserStatus.active,
        User.role_name.in_(roles),
        or_(User.ban.is_(False), and_(User.ban_end_at.is_not(None), User.ban_end_at < now)),
    )
    if search:
        stmt = stmt.where(User.full_name.ilike(f"%{search}%"))
    order = User.created_at.asc() if sort == "oldest" else User.created_at.desc()
    result = await db.execute(stmt.order_by(order))
    return list(result.scalars().all())


async def get_public_profile(db: AsyncSession, user_id: int) -> User | None:
    """Legacy UserController@profile: organization/teacher/user by id."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.role_name.in_([Role.ORGANIZATION, Role.TEACHER, Role.USER]),
        )
    )
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_mobile(db: AsyncSession, mobile: str) -> User | None:
    result = await db.execute(select(User).where(User.mobile == mobile))
    return result.scalar_one_or_none()


async def search(db: AsyncSession, query: str) -> list[User]:
    """Legacy SearchController: active users matching name/email/mobile."""
    like = f"%{query}%"
    result = await db.execute(
        select(User).where(
            User.status == UserStatus.active,
            or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.mobile.ilike(like),
            ),
        )
    )
    return list(result.scalars().all())


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
    result = await db.execute(select(User).where(or_(column == provider_id, User.email == email)))
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
