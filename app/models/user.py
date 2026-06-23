import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    inactive = "inactive"


class MeetingType(str, enum.Enum):
    all = "all"
    in_person = "in_person"
    online = "online"


class ThemeColorMode(str, enum.Enum):
    dark = "dark"
    light = "light"


class User(Base):
    """Parity port of the legacy `users` table (all columns).

    Field set mirrors legacy 1:1. Storage types are idiomatic Postgres rather
    than the legacy MySQL quirks: epoch-int timestamps -> timestamptz,
    spatial POINT `location` -> text placeholder (geo logic deferred),
    bit(3) `level_of_training` -> small int bitmask. Region ids carry no FK
    until the regions module lands. Business logic for finance/rewards/AI/etc.
    arrives in its phase; the columns exist now for parity.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- identity / login ---
    username: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    password: Mapped[str | None] = mapped_column(String(255))  # legacy name; holds bcrypt hash
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    organ_id: Mapped[int | None] = mapped_column(Integer)  # organization (self-ref), logical
    remember_token: Mapped[str | None] = mapped_column(String(255))  # Laravel legacy, unused
    google_id: Mapped[str | None] = mapped_column(String(255))
    facebook_id: Mapped[str | None] = mapped_column(String(255))

    # --- status / verification / ban ---
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), default=UserStatus.active, nullable=False
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    logged_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ban: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ban_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- profile ---
    bio: Mapped[str | None] = mapped_column(String(48))
    headline: Mapped[str | None] = mapped_column(String(128))
    about: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    avatar: Mapped[str | None] = mapped_column(String(128))
    avatar_settings: Mapped[str | None] = mapped_column(String(255))
    cover_img: Mapped[str | None] = mapped_column(String(128))
    profile_video: Mapped[str | None] = mapped_column(String(255))
    profile_secondary_image: Mapped[str | None] = mapped_column(String(255))

    # --- preferences ---
    language: Mapped[str | None] = mapped_column(String(128))
    currency: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str | None] = mapped_column(String(255))
    theme_color_mode: Mapped[ThemeColorMode | None] = mapped_column(
        Enum(ThemeColorMode, name="theme_color_mode")
    )
    newsletter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    public_message: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_profile_statistics: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_renew_subscription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    account_type: Mapped[str | None] = mapped_column(String(128))

    # --- finance (columns now; logic in Phase 4) ---
    financial_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    installment_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_installments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disable_cashback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    iban: Mapped[str | None] = mapped_column(String(128))
    account_id: Mapped[str | None] = mapped_column(String(128))
    commission: Mapped[int | None] = mapped_column(Integer)
    can_create_store: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- rewards / affiliate (columns now; logic in Phase 5) ---
    affiliate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_registration_bonus: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registration_bonus_amount: Mapped[float | None] = mapped_column(Numeric(15, 2))

    # --- misc (columns now; logic in later phases) ---
    access_content: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_ai_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    group_meeting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    meeting_type: Mapped[MeetingType] = mapped_column(
        Enum(MeetingType, name="meeting_type"), default=MeetingType.all, nullable=False
    )
    level_of_training: Mapped[int | None] = mapped_column(SmallInteger)  # legacy bit(3) bitmask
    location: Mapped[str | None] = mapped_column(Text)  # legacy spatial POINT; geo deferred
    country_id: Mapped[int | None] = mapped_column(Integer)  # FK -> regions, added in geo module
    province_id: Mapped[int | None] = mapped_column(Integer)
    city_id: Mapped[int | None] = mapped_column(Integer)
    district_id: Mapped[int | None] = mapped_column(Integer)
    identity_scan: Mapped[str | None] = mapped_column(Text)
    certificate: Mapped[str | None] = mapped_column(Text)
    offline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    offline_message: Mapped[str | None] = mapped_column(Text)

    # --- timestamps (legacy epoch-int -> timestamptz) ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # soft delete
