from datetime import datetime

from pydantic import BaseModel

from app.models.bundle import BundleStatus


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


class BundleDashboard(BaseModel):
    bundles: list[BundleRead]
    bundles_count: int
    bundle_sales_amount: float
    bundle_sales_count: int
    bundles_hours: int
