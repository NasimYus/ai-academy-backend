from datetime import datetime

from pydantic import BaseModel, Field

from app.models.bundle import BundleStatus
from app.schemas.course import CourseRead


class BundleCreate(BaseModel):
    """Admin/instructor bundle create (legacy BundleController@store).

    A single-page form; only title is strictly required so a draft can be saved."""

    title: str = Field(min_length=1, max_length=255)
    locale: str | None = None
    teacher_id: int | None = None  # admin-only: assign owner instructor
    points: int | None = None
    slug: str | None = None
    seo_description: str | None = None
    summary: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    image_cover: str | None = None
    video_demo: str | None = None
    video_demo_source: str | None = None
    category_id: int | None = None
    price: float | None = None
    access_days: int | None = None
    subscribe: bool = False
    private: bool = False
    certificate: bool = False
    only_for_students: bool = False
    message_for_reviewer: str | None = None
    rules: bool = False
    draft: bool = False


class BundleManageRow(BaseModel):
    id: int
    title: str
    status: BundleStatus
    teacher_id: int | None
    teacher_name: str | None
    category: str | None
    price: float | None
    webinars_count: int
    created_at: datetime


class BundleManageList(BaseModel):
    total: int
    bundles: list[BundleManageRow]


class BundleRead(BaseModel):
    id: int
    title: str
    slug: str
    thumbnail: str | None
    image_cover: str | None
    price: float | None
    status: BundleStatus
    category: str | None
    webinars_count: int
    created_at: datetime


class BundlePublicRead(BaseModel):
    """Public bundle card (legacy BundleResource)."""

    id: int
    title: str
    slug: str
    thumbnail: str | None = None
    image_cover: str | None = None
    price: float | None = None
    points: int | None = None
    category: str | None = None
    webinars_count: int
    created_at: datetime


class BundleDetail(BundlePublicRead):
    courses: list[CourseRead] = []


class BundlePurchaseResponse(BaseModel):
    message: str


class BundleDashboard(BaseModel):
    bundles: list[BundleRead]
    bundles_count: int
    bundle_sales_amount: float
    bundle_sales_count: int
    bundles_hours: int
