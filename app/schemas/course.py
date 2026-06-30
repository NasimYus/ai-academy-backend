from datetime import datetime

from pydantic import BaseModel

from app.models.course import CourseStatus, CourseType, VideoDemoSource
from app.schemas.review import CommentRead, ReviewRead

# Parity with legacy Webinar `brief`/`details` accessors. Fields backed by
# entities from later phases are present (stable FE contract) but stubbed —
# marked NOTE(Phase N). Source of truth: app/Models/Api/Webinar.php.


class CourseTeacher(BaseModel):
    """Subset of the legacy `teacher->brief` available in Phase 1."""

    id: int
    username: str | None = None
    full_name: str | None = None
    role_name: str | None = None
    avatar: str | None = None
    bio: str | None = None
    headline: str | None = None
    offline: bool = False


class CourseRateType(BaseModel):
    content_quality: float = 0
    instructor_skills: float = 0
    purchase_worth: float = 0
    support_quality: float = 0


class CourseRead(BaseModel):
    """Legacy `Webinar::brief` — list cards and the base of detail."""

    id: int
    title: str
    slug: str
    type: CourseType
    status: CourseStatus
    label: str | None = None

    image: str | None = None
    image_cover: str | None = None

    price: float
    price_string: str | None = None
    currency: str | None = None  # display currency code (F.5); null = default
    best_ticket_price: float | None = None  # NOTE(4.2) tickets/discounts → = price
    discount_percent: int = 0  # NOTE(4.2)

    duration: int | None = None
    access_days: int | None = None
    capacity: int | None = None
    points: int | None = None
    start_date: datetime | None = None
    created_at: datetime

    teacher: CourseTeacher | None = None
    category: str | None = None
    category_id: int | None = None

    students_count: int = 0  # NOTE(4.x) Sale
    rate: float = 0  # NOTE(2.6) reviews
    reviews_count: int = 0  # NOTE(2.6)

    is_favorite: bool = False  # NOTE(5.x)
    is_private: bool = False
    forum: bool = False
    badges: list[dict] = []  # NOTE(5.x)

    auth: bool = False  # NOTE(4/5) optional-auth not wired on guest detail yet
    auth_has_bought: bool = False  # NOTE(4.x)
    can_view: bool = True
    can_view_error: list[str] | None = None


class CourseDetail(CourseRead):
    """Legacy `Webinar::details` = brief + the keys below."""

    locale: str | None = None
    summary: str | None = None
    icon: str | None = None
    description: str | None = None
    seo_description: str | None = None
    video_demo: str | None = None
    video_demo_source: VideoDemoSource | None = None

    support: bool = False
    subscribe: bool = False
    downloadable: bool = False
    certificate: bool = False
    can_add_to_cart: bool = False  # NOTE(4.1)
    can_buy_with_points: bool = False  # NOTE(5.x rewards)

    tax: float = 0  # NOTE(F.5) multi-currency / tax config
    price_with_discount: float = 0

    rate_type: CourseRateType = CourseRateType()

    # Curriculum & relations — built in their own phases.
    prerequisites: list[dict] = []  # NOTE(3.1)
    faqs: list[dict] = []  # NOTE(6.x)
    tags: list[dict] = []  # NOTE(6.x)
    comments: list[CommentRead] = []
    reviews: list[ReviewRead] = []
    chapters: list[dict] = []  # NOTE(3.2)
    sessions_count: int = 0  # NOTE(3.2)
    files_count: int = 0  # NOTE(3.2)
    text_lessons_count: int = 0  # NOTE(3.2)
    quizzes: list[dict] = []  # NOTE(3.4)
    quizzes_count: int = 0  # NOTE(3.4)
    certificate_quizzes: list[dict] = []  # NOTE(3.6)
    tickets: list[dict] = []  # NOTE(4.2)
