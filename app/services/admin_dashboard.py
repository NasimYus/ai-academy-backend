"""Admin general dashboard aggregation (parity of Admin\\DashboardController@index
+ DashboardTrait). Dates are timezone-aware datetimes rather than epoch ints."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting import Accounting, AccountingType
from app.models.comment import Comment, CommentStatus
from app.models.course import Course, CourseStatus, CourseType
from app.models.sale import Sale, SaleType
from app.models.support import Support, SupportStatus
from app.models.user import User
from app.schemas.admin_dashboard import (
    AdminDashboard,
    ChartData,
    DailySalesByType,
    GrowStat,
    PeriodStats,
    RecentComment,
    RecentCourseRow,
    RecentTicket,
)

MONTHS_RU = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
]  # fmt: skip


def _day_start(d: datetime) -> datetime:
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=UTC)
    return start, end


async def _sales_sum(db: AsyncSession, start: datetime | None, end: datetime | None) -> float:
    stmt = select(func.coalesce(func.sum(Sale.total_amount), 0)).where(Sale.refund_at.is_(None))
    if start is not None:
        stmt = stmt.where(Sale.created_at >= start)
    if end is not None:
        stmt = stmt.where(Sale.created_at < end)
    return float(await db.scalar(stmt) or 0)


async def _sales_count(db: AsyncSession, start: datetime | None, end: datetime | None) -> int:
    stmt = select(func.count()).select_from(Sale).where(Sale.refund_at.is_(None))
    if start is not None:
        stmt = stmt.where(Sale.created_at >= start)
    if end is not None:
        stmt = stmt.where(Sale.created_at < end)
    return int(await db.scalar(stmt) or 0)


async def _income(db: AsyncSession, start: datetime | None, end: datetime | None) -> float:
    """Platform income = accounting rows where system OR tax; additions − deductions."""
    base = select(func.coalesce(func.sum(Accounting.amount), 0)).where(
        or_(Accounting.system.is_(True), Accounting.tax.is_(True))
    )
    if start is not None:
        base = base.where(Accounting.created_at >= start)
    if end is not None:
        base = base.where(Accounting.created_at < end)
    add = float(await db.scalar(base.where(Accounting.type == AccountingType.addiction)) or 0)
    ded = float(await db.scalar(base.where(Accounting.type == AccountingType.deduction)) or 0)
    return max(add - ded, 0.0)


def _grow(last: float, new: float) -> GrowStat:
    if last != 0:
        res = (new - last) / abs(last) * 100
        return GrowStat(
            amount=new, grow_percent=f"{round(res, 3)}%", grow_status="up" if res > 0 else "down"
        )
    return GrowStat(amount=new, grow_percent="No previous value", grow_status="up")


async def build(db: AsyncSession) -> AdminDashboard:
    now = datetime.now(UTC)
    today = _day_start(now)
    tomorrow = today + timedelta(days=1)
    month_start, month_end = _month_bounds(now.year, now.month)
    year_start = datetime(now.year, 1, 1, tzinfo=UTC)
    year_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    week_start = _day_start(now - timedelta(days=now.weekday()))
    week_end = week_start + timedelta(days=7)

    # Daily sales by type (today).
    appt_stmt = (
        select(func.count())
        .select_from(Sale)
        .where(Sale.refund_at.is_(None), Sale.type == SaleType.meeting)
        .where(Sale.created_at >= today, Sale.created_at < tomorrow)
    )
    appointments = int(await db.scalar(appt_stmt) or 0)
    by_type = await db.execute(
        select(Course.type, func.count())
        .select_from(Sale)
        .join(Course, Course.id == Sale.webinar_id)
        .where(
            Sale.refund_at.is_(None),
            Sale.type == SaleType.webinar,
            Sale.created_at >= today,
            Sale.created_at < tomorrow,
        )
        .group_by(Course.type)
    )
    type_counts = {t: c for t, c in by_type.all()}
    webinars = int(type_counts.get(CourseType.webinar, 0))
    courses_cnt = int(type_counts.get(CourseType.course, 0))
    daily = DailySalesByType(
        webinars=webinars,
        courses=courses_cnt,
        appointments=appointments,
        total=webinars + courses_cnt + appointments,
    )

    # Income + sales-count period stats.
    income = PeriodStats(
        today=await _income(db, today, tomorrow),
        month=await _income(db, month_start, month_end),
        year=await _income(db, year_start, year_end),
        total=await _income(db, None, None),
    )
    sales_counts = PeriodStats(
        today=await _sales_count(db, today, tomorrow),
        month=await _sales_count(db, month_start, month_end),
        year=await _sales_count(db, year_start, year_end),
        total=await _sales_count(db, None, None),
    )

    # Small counters.
    new_comments = int(
        await db.scalar(
            select(func.count()).select_from(Comment).where(Comment.status == CommentStatus.new)
        )
        or 0
    )
    new_tickets = int(
        await db.scalar(
            select(func.count())
            .select_from(Support)
            .where(
                Support.department_id.is_not(None),
                Support.status.in_([SupportStatus.open, SupportStatus.replied]),
                Support.updated_at >= today,
                Support.updated_at < tomorrow,
            )
        )
        or 0
    )
    pending_reviews = int(
        await db.scalar(
            select(func.count()).select_from(Course).where(Course.status == CourseStatus.pending)
        )
        or 0
    )

    # Charts.
    year_labels, year_data = [], []
    for month in range(1, 13):
        ms, me = _month_bounds(now.year, month)
        year_labels.append(MONTHS_RU[month - 1])
        year_data.append(round(await _sales_sum(db, ms, me), 2))
    days_in_month = (month_end - month_start).days
    month_labels, month_data = [], []
    for day in range(1, days_in_month + 1):
        ds = month_start + timedelta(days=day - 1)
        month_labels.append(f"{day:02d}")
        month_data.append(round(await _sales_sum(db, ds, ds + timedelta(days=1)), 2))

    # Sales stat cards with growth vs the previous period.
    sales_stats = {
        "today": _grow(
            await _sales_sum(db, today - timedelta(days=1), today),
            await _sales_sum(db, today, tomorrow),
        ),
        "week": _grow(
            await _sales_sum(db, week_start - timedelta(days=7), week_start),
            await _sales_sum(db, week_start, week_end),
        ),
        "month": _grow(
            await _sales_sum(
                db,
                *_month_bounds(
                    now.year if now.month > 1 else now.year - 1,
                    now.month - 1 if now.month > 1 else 12,
                ),
            ),
            await _sales_sum(db, month_start, month_end),
        ),
        "year": _grow(
            await _sales_sum(
                db, datetime(now.year - 1, 1, 1, tzinfo=UTC), datetime(now.year, 1, 1, tzinfo=UTC)
            ),
            await _sales_sum(db, year_start, year_end),
        ),
    }

    # Recent lists.
    comments_rows = (
        (
            await db.execute(
                select(Comment)
                .options(selectinload(Comment.user))
                .order_by(Comment.created_at.desc())
                .limit(6)
            )
        )
        .scalars()
        .all()
    )
    recent_comments = [
        RecentComment(
            id=c.id,
            user_name=c.user.full_name if c.user else None,
            comment=c.comment,
            created_at=c.created_at,
        )
        for c in comments_rows
    ]

    tickets_rows = (
        (
            await db.execute(
                select(Support)
                .where(Support.department_id.is_not(None))
                .order_by(Support.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    recent_tickets = [
        RecentTicket(id=t.id, title=t.title, status=t.status.value, created_at=t.created_at)
        for t in tickets_rows
    ]
    tickets_pending = int(
        await db.scalar(
            select(func.count())
            .select_from(Support)
            .where(
                Support.department_id.is_not(None),
                Support.status.in_([SupportStatus.open, SupportStatus.replied]),
            )
        )
        or 0
    )

    async def _recent_courses(course_type: CourseType) -> tuple[list[RecentCourseRow], int]:
        rows = (
            (
                await db.execute(
                    select(Course)
                    .options(selectinload(Course.teacher))
                    .where(Course.type == course_type)
                    .order_by(Course.created_at.desc())
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )
        pending = int(
            await db.scalar(
                select(func.count())
                .select_from(Course)
                .where(Course.type == course_type, Course.status == CourseStatus.pending)
            )
            or 0
        )
        return [
            RecentCourseRow(
                id=c.id,
                title=c.title,
                teacher_name=c.teacher.full_name if c.teacher else None,
                status=c.status.value,
            )
            for c in rows
        ], pending

    recent_webinars, webinars_pending = await _recent_courses(CourseType.webinar)
    recent_courses, courses_pending = await _recent_courses(CourseType.course)

    # User registrations chart (day of current month).
    users_labels, users_data = [], []
    for day in range(1, days_in_month + 1):
        ds = month_start + timedelta(days=day - 1)
        users_labels.append(f"{day:02d}")
        cnt = int(
            await db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.created_at >= ds, User.created_at < ds + timedelta(days=1))
            )
            or 0
        )
        users_data.append(cnt)

    return AdminDashboard(
        daily_sales_by_type=daily,
        income=income,
        sales_counts=sales_counts,
        new_sales=0,  # NOTE: legacy uses sale_log (unacknowledged); not migrated yet
        new_comments=new_comments,
        new_tickets=new_tickets,
        pending_reviews=pending_reviews,
        sales_chart_year=ChartData(labels=year_labels, data=year_data),
        sales_chart_month=ChartData(labels=month_labels, data=month_data),
        sales_stats=sales_stats,
        recent_comments=recent_comments,
        recent_tickets=recent_tickets,
        recent_tickets_pending=tickets_pending,
        recent_webinars=recent_webinars,
        recent_webinars_pending=webinars_pending,
        recent_courses=recent_courses,
        recent_courses_pending=courses_pending,
        users_chart=ChartData(labels=users_labels, data=[float(x) for x in users_data]),
    )
