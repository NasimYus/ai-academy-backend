import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PackageRole(str, enum.Enum):
    instructors = "instructors"
    organizations = "organizations"


class PackageStatus(str, enum.Enum):
    disabled = "disabled"
    active = "active"


class RegistrationPackage(Base):
    """An instructor/organization capacity package, parity of `registration_packages`.

    Null count/`days` columns mean "unlimited" (legacy `?? 'unlimited'`).
    Quota enforcement (courses/meetings caps) is deferred. Title/description inline.
    """

    __tablename__ = "registration_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[PackageRole] = mapped_column(
        Enum(PackageRole, name="package_role"), index=True, nullable=False
    )
    days: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(15, 3), default=0, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(512))
    instructors_count: Mapped[int | None] = mapped_column(Integer)
    students_count: Mapped[int | None] = mapped_column(Integer)
    courses_capacity: Mapped[int | None] = mapped_column(Integer)
    courses_count: Mapped[int | None] = mapped_column(Integer)
    meeting_count: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PackageStatus] = mapped_column(
        Enum(PackageStatus, name="package_status"), default=PackageStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserRegistrationPackage(Base):
    """A user's purchased/activated package (legacy: a registration-package Sale)."""

    __tablename__ = "user_registration_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("registration_packages.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    package: Mapped[RegistrationPackage] = relationship("RegistrationPackage", lazy="raise")
