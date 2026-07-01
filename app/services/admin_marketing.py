"""Admin marketing dashboard aggregation (parity of Admin\\DashboardController@marketing
+ DashboardTrait marketing helpers). Dates are timezone-aware datetimes rather than
epoch ints; net profit uses accounting rows where system is true and tax is false."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Accounting, AccountingType
from app.models.course import Course, CourseStatus, CourseType
from app.models.featured_course import FeaturedCourse, FeaturedStatus
from app.models.meeting import Meeting
from app.models.role import Role
from app.models.sale import Sale
from app.models.user import User, UserStatus
from app.schemas.admin_dashboard import ChartData
from app.schemas.admin_marketing import (
    ActiveStudentRow,
    AdminMarketing,
    TopAppointmentRow,
    TopClassRow,
    TopSellerRow,
)
from app.services.admin_dashboard import MONTHS_RU, _day_start, _grow, _month_bounds


async def _net_profit(db: AsyncSession, start: datetime | None, end: datetime | None) -> float:
    """Net profit = accounting rows where system is true and tax is false;
    additions − deductions, floored at 0 (legacy computingAccounting)."""
    base = select(func.coalesce(func.sum(Accounting.amount), 0)).where(
        Accounting.system.is_(True), Accounting.tax.is_(False)
    )
    if start is not None:
        base = base.where(Accounting.created_at >= start)
    if end is not None:
        base = base.where(Accounting.created_at < end)
    add = float(await db.scalar(base.where(Accounting.type == AccountingType.addiction)) or 0)
    ded = float(await db.scalar(base.where(Accounting.type == AccountingType.deduction)) or 0)
    return max(add - ded, 0.0)


async def build(db: AsyncSession) -> AdminMarketing:
    now = datetime.now(UTC)
    today = _day_start(now)
    tomorrow = today + timedelta(days=1)
    month_start, month_end = _month_bounds(now.year, now.month)
    year_start = datetime(now.year, 1, 1, tzinfo=UTC)
    year_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    week_start = _day_start(now - timedelta(days=now.weekday()))
    week_end = week_start + timedelta(days=7)

    # --- top counters ------------------------------------------------------
    buyers = select(Sale.buyer_id).where(Sale.refund_at.is_(None)).scalar_subquery()
    users_without_purchases = int(
        await db.scalar(select(func.count()).select_from(User).where(User.id.notin_(buyers))) or 0
    )

    # teachers that own or teach an active class (creator_id or teacher_id)
    teachers_with_class = (
        select(Course.creator_id)
        .where(Course.status == CourseStatus.active, Course.creator_id.is_not(None))
        .union(
            select(Course.teacher_id).where(
                Course.status == CourseStatus.active, Course.teacher_id.is_not(None)
            )
        )
        .scalar_subquery()
    )
    teachers_without_class = int(
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role_name == Role.TEACHER, User.id.notin_(teachers_with_class))
        )
        or 0
    )

    featured_classes = int(
        await db.scalar(
            select(func.count())
            .select_from(FeaturedCourse)
            .where(FeaturedCourse.status == FeaturedStatus.publish)
        )
        or 0
    )

    # NOTE: legacy counts active `tickets` (webinar early-bird discounts w/ capacity),
    # a table not yet migrated — gate-stub to 0 (matches a clean DB).
    active_discounts = 0

    # --- classes statistics (% split by course type) ----------------------
    total_active = int(
        await db.scalar(
            select(func.count()).select_from(Course).where(Course.status == CourseStatus.active)
        )
        or 0
    )
    stat_labels: list[str] = []
    stat_data: list[float] = []
    for ctype in (CourseType.webinar, CourseType.course, CourseType.text_lesson):
        cnt = int(
            await db.scalar(
                select(func.count())
                .select_from(Course)
                .where(Course.status == CourseStatus.active, Course.type == ctype)
            )
            or 0
        )
        stat_labels.append(ctype.value)
        stat_data.append(round(cnt * 100 / total_active, 2) if total_active else 0.0)
    classes_statistics = ChartData(labels=stat_labels, data=stat_data)

    # --- net profit charts -------------------------------------------------
    year_labels, year_data = [], []
    for month in range(1, 13):
        ms, me = _month_bounds(now.year, month)
        year_labels.append(MONTHS_RU[month - 1])
        year_data.append(round(await _net_profit(db, ms, me), 2))
    days_in_month = (month_end - month_start).days
    month_labels, month_data = [], []
    for day in range(1, days_in_month + 1):
        ds = month_start + timedelta(days=day - 1)
        month_labels.append(f"{day:02d}")
        month_data.append(round(await _net_profit(db, ds, ds + timedelta(days=1)), 2))

    net_profit_stats = {
        "today": _grow(
            await _net_profit(db, today - timedelta(days=1), today),
            await _net_profit(db, today, tomorrow),
        ),
        "week": _grow(
            await _net_profit(db, week_start - timedelta(days=7), week_start),
            await _net_profit(db, week_start, week_end),
        ),
        "month": _grow(
            await _net_profit(
                db,
                *_month_bounds(
                    now.year if now.month > 1 else now.year - 1,
                    now.month - 1 if now.month > 1 else 12,
                ),
            ),
            await _net_profit(db, month_start, month_end),
        ),
        "year": _grow(
            await _net_profit(
                db, datetime(now.year - 1, 1, 1, tzinfo=UTC), datetime(now.year, 1, 1, tzinfo=UTC)
            ),
            await _net_profit(db, year_start, year_end),
        ),
    }

    # --- top selling classes ----------------------------------------------
    sales_count = func.count(Sale.webinar_id).label("sales_count")
    sales_amount = func.coalesce(func.sum(Sale.total_amount), 0).label("sales_amount")
    cls_rows = (
        await db.execute(
            select(Course.id, Course.title, sales_count, sales_amount)
            .join(Sale, Sale.webinar_id == Course.id)
            .where(
                Course.status == CourseStatus.active,
                Sale.refund_at.is_(None),
                Sale.amount > 0,
            )
            .group_by(Course.id, Course.title)
            .order_by(sales_count.desc())
            .limit(5)
        )
    ).all()
    top_selling_classes = [
        TopClassRow(
            id=r.id,
            title=r.title,
            sales_count=int(r.sales_count),
            sales_amount=float(r.sales_amount),
        )
        for r in cls_rows
    ]

    # --- top selling appointments (meetings) ------------------------------
    appt_count = func.count(Sale.meeting_id).label("sales_count")
    appt_rows = (
        await db.execute(
            select(Meeting.id, User.full_name, appt_count, sales_amount)
            .join(Sale, Sale.meeting_id == Meeting.id)
            .join(User, User.id == Meeting.creator_id, isouter=True)
            .where(
                Meeting.disabled.is_(False),
                Sale.refund_at.is_(None),
                Sale.amount > 0,
            )
            .group_by(Meeting.id, User.full_name)
            .order_by(appt_count.desc())
            .limit(5)
        )
    ).all()
    top_selling_appointments = [
        TopAppointmentRow(
            id=r.id,
            consultant_name=r.full_name,
            sales_count=int(r.sales_count),
            sales_amount=float(r.sales_amount),
        )
        for r in appt_rows
    ]

    # --- top selling teachers / organizations -----------------------------
    async def _top_sellers(role_name: str) -> list[TopSellerRow]:
        seller_count = func.count(Sale.seller_id).label("sales_count")
        rows = (
            await db.execute(
                select(User.id, User.full_name, seller_count, sales_amount)
                .join(Sale, Sale.seller_id == User.id)
                .where(
                    User.status == UserStatus.active,
                    User.role_name == role_name,
                    Sale.refund_at.is_(None),
                    Sale.amount > 0,
                )
                .group_by(User.id, User.full_name)
                .order_by(seller_count.desc())
                .limit(5)
            )
        ).all()
        result: list[TopSellerRow] = []
        for r in rows:
            duration = int(
                await db.scalar(
                    select(func.coalesce(func.sum(Course.duration), 0)).where(
                        Course.status == CourseStatus.active,
                        or_(Course.creator_id == r.id, Course.teacher_id == r.id),
                    )
                )
                or 0
            )
            result.append(
                TopSellerRow(
                    id=r.id,
                    name=r.full_name,
                    classes_duration=duration,
                    sales_count=int(r.sales_count),
                    sales_amount=float(r.sales_amount),
                )
            )
        return result

    top_selling_teachers = await _top_sellers(Role.TEACHER)
    top_selling_organizations = await _top_sellers(Role.ORGANIZATION)

    # --- most active students ---------------------------------------------
    purchased = func.count(Sale.webinar_id).label("purchased_classes")
    reserved = func.count(Sale.meeting_id).label("reserved_appointments")
    total_cost = func.coalesce(func.sum(Sale.total_amount), 0).label("total_cost")
    student_rows = (
        await db.execute(
            select(User.id, User.full_name, purchased, reserved, total_cost)
            .join(Sale, Sale.buyer_id == User.id)
            .where(
                User.status == UserStatus.active,
                User.role_name == Role.USER,
                Sale.refund_at.is_(None),
                Sale.amount > 0,
            )
            .group_by(User.id, User.full_name)
            .order_by(purchased.desc(), reserved.desc())
            .limit(5)
        )
    ).all()
    most_active_students = [
        ActiveStudentRow(
            id=r.id,
            name=r.full_name,
            purchased_classes=int(r.purchased_classes),
            reserved_appointments=int(r.reserved_appointments),
            total_cost=float(r.total_cost),
        )
        for r in student_rows
    ]

    return AdminMarketing(
        users_without_purchases=users_without_purchases,
        teachers_without_class=teachers_without_class,
        featured_classes=featured_classes,
        active_discounts=active_discounts,
        classes_statistics=classes_statistics,
        net_profit_chart_year=ChartData(labels=year_labels, data=year_data),
        net_profit_chart_month=ChartData(labels=month_labels, data=month_data),
        net_profit_stats=net_profit_stats,
        top_selling_classes=top_selling_classes,
        top_selling_appointments=top_selling_appointments,
        top_selling_teachers=top_selling_teachers,
        top_selling_organizations=top_selling_organizations,
        most_active_students=most_active_students,
    )
