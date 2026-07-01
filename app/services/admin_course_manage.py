"""Admin course-management aggregation (parity of Admin\\WebinarController@index +
filterWebinar). Headline stats are per-type; rows carry sales/income/students and
honour the search / date / category / instructor / status / sort filters."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CourseStatus, CourseType
from app.models.sale import Sale
from app.repositories import enrollments as enrollments_repo
from app.schemas.admin_course_manage import (
    AdminCourseManageList,
    AdminCourseManageRow,
    LiveSessionList,
)

_SORTS = {
    "created_at_desc": Course.created_at.desc(),
    "created_at_asc": Course.created_at.asc(),
    "updated_at_desc": Course.updated_at.desc(),
    "updated_at_asc": Course.updated_at.asc(),
    "price_asc": Course.price.asc(),
    "price_desc": Course.price.desc(),
}


async def list_courses(
    db: AsyncSession,
    *,
    course_type: CourseType,
    search: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    category_id: int | None = None,
    teacher_id: int | None = None,
    status: CourseStatus | None = None,
    sort: str | None = None,
    page: int = 1,
    per_page: int = 10,
) -> AdminCourseManageList:
    base = select(Course).where(Course.type == course_type)

    # --- headline stats (by type, ignoring row filters) -------------------
    total_courses = int(
        await db.scalar(select(func.count()).select_from(Course).where(Course.type == course_type))
        or 0
    )
    total_pending = int(
        await db.scalar(
            select(func.count())
            .select_from(Course)
            .where(Course.type == course_type, Course.status == CourseStatus.pending)
        )
        or 0
    )
    total_duration = int(
        await db.scalar(
            select(func.coalesce(func.sum(Course.duration), 0)).where(Course.type == course_type)
        )
        or 0
    )
    total_sales = int(
        await db.scalar(
            select(func.count())
            .select_from(Sale)
            .join(Course, Course.id == Sale.webinar_id)
            .where(Course.type == course_type, Sale.refund_at.is_(None))
        )
        or 0
    )

    # --- filters ----------------------------------------------------------
    filtered = base
    if search:
        filtered = filtered.where(Course.title.ilike(f"%{search}%"))
    if from_date is not None:
        filtered = filtered.where(Course.created_at >= from_date)
    if to_date is not None:
        filtered = filtered.where(Course.created_at <= to_date)
    if category_id is not None:
        filtered = filtered.where(Course.category_id == category_id)
    if teacher_id is not None:
        filtered = filtered.where(Course.teacher_id == teacher_id)
    if status is not None:
        filtered = filtered.where(Course.status == status)

    total = int(await db.scalar(select(func.count()).select_from(filtered.subquery())) or 0)

    order = _SORTS.get(sort or "created_at_desc", Course.created_at.desc())
    page = max(1, page)
    rows = (
        (
            await db.execute(
                filtered.options(selectinload(Course.teacher), selectinload(Course.category))
                .order_by(order)
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )

    ids = [c.id for c in rows]
    # sales count + income per course for this page
    sales_by_course: dict[int, tuple[int, float]] = {}
    if ids:
        agg = await db.execute(
            select(
                Sale.webinar_id,
                func.count().label("cnt"),
                func.coalesce(func.sum(Sale.total_amount), 0).label("gross"),
                func.coalesce(func.sum(Sale.tax), 0).label("tax"),
                func.coalesce(func.sum(Sale.commission), 0).label("commission"),
            )
            .where(Sale.webinar_id.in_(ids), Sale.refund_at.is_(None))
            .group_by(Sale.webinar_id)
        )
        for wid, cnt, gross, tax, commission in agg.all():
            income = float(gross) - (float(tax) + float(commission))
            sales_by_course[wid] = (int(cnt), income)
    students = await enrollments_repo.count_for_courses(db, ids) if ids else {}

    courses = []
    for c in rows:
        sc, income = sales_by_course.get(c.id, (0, 0.0))
        courses.append(
            AdminCourseManageRow(
                id=c.id,
                title=c.title,
                type=c.type,
                status=c.status,
                category_name=c.category.title if c.category else None,
                teacher_id=c.teacher_id,
                teacher_name=c.teacher.full_name if c.teacher else None,
                price=float(c.price),
                is_free=float(c.price) <= 0,
                capacity=c.capacity,
                duration=c.duration,
                sales_count=sc,
                students_count=students.get(c.id, 0),
                income=income,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return AdminCourseManageList(
        total_courses=total_courses,
        total_pending=total_pending,
        total_duration=total_duration,
        total_sales=total_sales,
        page=page,
        per_page=per_page,
        total=total,
        courses=courses,
    )


async def list_live_sessions(
    db: AsyncSession, *, page: int = 1, per_page: int = 10
) -> LiveSessionList:
    """Live-sessions history. NOTE: the legacy `sessions` table (Agora/BBB/Jitsi
    live classes) is not migrated yet — gate-stub to an empty list (a clean DB has
    no live sessions), keeping the paginated shape for the frontend."""
    return LiveSessionList(page=max(1, page), per_page=per_page, total=0, sessions=[])
