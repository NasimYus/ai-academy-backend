from datetime import datetime

from pydantic import BaseModel

from app.models.bundle import BundleStatus
from app.schemas.course import CourseRead


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
