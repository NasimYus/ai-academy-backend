"""Presenters mapping Course ORM rows to API schemas (legacy Webinar brief/details).

Shared by the courses and search routes. Relationships must be eager-loaded by
the repository (they are `lazy="raise"`).
"""

from app.models.course import Course
from app.schemas.course import CourseDetail, CourseRead, CourseTeacher


def price_string(price: float) -> str | None:
    # Legacy handlePrice(): formatted only when price > 0 (currency/i18n → F.5).
    return f"{price:,.0f}" if price and price > 0 else None


def teacher_brief(course: Course) -> CourseTeacher | None:
    teacher = course.teacher
    if teacher is None:
        return None
    return CourseTeacher(
        id=teacher.id,
        username=teacher.username,
        full_name=teacher.full_name,
        role_name=teacher.role_name,
        avatar=teacher.avatar,
        bio=teacher.bio,
        headline=teacher.headline,
        offline=bool(teacher.offline),
    )


def to_brief(course: Course) -> CourseRead:
    price = float(course.price)
    return CourseRead(
        id=course.id,
        title=course.title,
        slug=course.slug,
        type=course.type,
        status=course.status,
        image=course.thumbnail,
        image_cover=course.image_cover,
        price=price,
        price_string=price_string(price),
        best_ticket_price=price,  # NOTE(4.2) no tickets/special-offers yet
        duration=course.duration,
        access_days=course.access_days,
        capacity=course.capacity,
        points=course.points,
        start_date=course.start_date,
        created_at=course.created_at,
        teacher=teacher_brief(course),
        category=course.category.title if course.category else None,
        category_id=course.category_id,
        is_private=course.private,
        forum=course.forum,
    )


def to_detail(course: Course) -> CourseDetail:
    price = float(course.price)
    return CourseDetail(
        **to_brief(course).model_dump(),
        description=course.description,
        seo_description=course.seo_description,
        video_demo=course.video_demo,
        video_demo_source=course.video_demo_source,
        support=course.support,
        subscribe=course.subscribe,
        downloadable=course.downloadable,
        certificate=course.certificate,
        price_with_discount=price,  # NOTE(4.2) = price until discounts exist
    )
