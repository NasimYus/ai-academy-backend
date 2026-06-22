from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(Base):
    """User roles, mirrors the legacy `roles` table.

    Seeded with the legacy defaults: user / admin / organization / teacher.
    `caption` is plain text for now; translatable captions are deferred (F.4).
    """

    __tablename__ = "roles"

    # Legacy default ids relied upon by the app: user=1, organization=3, teacher=4.
    USER = "user"
    ADMIN = "admin"
    ORGANIZATION = "organization"
    TEACHER = "teacher"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    caption: Mapped[str] = mapped_column(String(64), nullable=False)
    users_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
