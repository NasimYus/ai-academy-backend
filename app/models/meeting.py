import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DayLabel(str, enum.Enum):
    saturday = "saturday"
    sunday = "sunday"
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"


class ReserveStatus(str, enum.Enum):
    open = "open"
    finished = "finished"
    pending = "pending"
    canceled = "canceled"


class ReserveMeetingType(str, enum.Enum):
    in_person = "in_person"
    online = "online"


class Meeting(Base):
    """An instructor's consultation config (legacy `meetings`)."""

    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount: Mapped[int | None] = mapped_column(Integer)  # price per session (null = free)
    discount: Mapped[int | None] = mapped_column(Integer)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creator: Mapped["User"] = relationship(lazy="raise")  # noqa: F821
    times: Mapped[list["MeetingTime"]] = relationship(
        back_populates="meeting",
        lazy="raise",
        order_by="MeetingTime.id",
        cascade="all, delete-orphan",
    )


class MeetingTime(Base):
    """A weekly availability slot (legacy `meeting_times`); `time` = 'HH:MM-HH:MM'."""

    __tablename__ = "meeting_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day_label: Mapped[DayLabel] = mapped_column(
        Enum(DayLabel, name="meeting_day_label"), nullable=False
    )
    time: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="times", lazy="raise")


class ReserveMeeting(Base):
    """A booking of a meeting slot by a user (legacy `reserve_meetings`).

    The paid checkout flow (sale_id) and Agora live-link are gated/deferred;
    reservations here are created directly. NOTE(Phase 7).
    """

    __tablename__ = "reserve_meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    meeting_time_id: Mapped[int] = mapped_column(
        ForeignKey("meeting_times.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day: Mapped[str | None] = mapped_column(String(16))
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReserveStatus] = mapped_column(
        Enum(ReserveStatus, name="reserve_meeting_status"),
        default=ReserveStatus.pending,
        nullable=False,
    )
    paid_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount: Mapped[int | None] = mapped_column(Integer)
    meeting_type: Mapped[ReserveMeetingType] = mapped_column(
        Enum(ReserveMeetingType, name="reserve_meeting_type"),
        default=ReserveMeetingType.online,
        nullable=False,
    )
    student_count: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(512))
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    meeting: Mapped["Meeting"] = relationship(lazy="raise")
    meeting_time: Mapped["MeetingTime"] = relationship(lazy="raise")
    user: Mapped["User"] = relationship(lazy="raise")  # noqa: F821
