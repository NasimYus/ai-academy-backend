import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccountingType(str, enum.Enum):
    """Legacy Accounting `type` — money added to or taken from the ledger."""

    addiction = "addiction"
    deduction = "deduction"


class AccountingTypeAccount(str, enum.Enum):
    """Legacy Accounting `type_account` (only `asset` matters for the wallet)."""

    asset = "asset"
    income = "income"
    subscribe = "subscribe"
    promotion = "promotion"
    registration_package = "registration_package"
    installment_payment = "installment_payment"


class Accounting(Base):
    """A single ledger row, parity of legacy `accounting`.

    The student wallet balance (`getAccountingCharge`) is the sum of
    `asset` additions minus deductions where `system` and `tax` are both false.
    NOTE(Phase): item-specific FKs beyond `course_id` (bundle/subscribe/…) and
    automatic ledger writes on purchase are not migrated yet.
    """

    __tablename__ = "accounting"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    type: Mapped[AccountingType] = mapped_column(
        Enum(AccountingType, name="accounting_type"), nullable=False
    )
    type_account: Mapped[AccountingTypeAccount] = mapped_column(
        Enum(AccountingTypeAccount, name="accounting_type_account"),
        default=AccountingTypeAccount.asset,
        nullable=False,
    )
    system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tax: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OfflinePaymentStatus(str, enum.Enum):
    waiting = "waiting"
    approved = "approved"
    reject = "reject"


class OfflinePayment(Base):
    """An offline (bank-transfer) top-up request, parity of legacy
    `offline_payments`. Approval (→ wallet credit) is an admin action, not yet
    migrated; here requests are created in `waiting`. NOTE(Phase).
    """

    __tablename__ = "offline_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Legacy uses offline_bank_id → offline_banks; that admin subsystem isn't
    # migrated, so the bank name is stored inline.
    bank: Mapped[str | None] = mapped_column(String(255))
    reference_number: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    status: Mapped[OfflinePaymentStatus] = mapped_column(
        Enum(OfflinePaymentStatus, name="offline_payment_status"),
        default=OfflinePaymentStatus.waiting,
        nullable=False,
    )
    attachment: Mapped[str | None] = mapped_column(String(512))
    pay_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
