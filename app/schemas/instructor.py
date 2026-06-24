from datetime import datetime

from pydantic import BaseModel, Field

from app.models.course import CourseType, VideoDemoSource

# Instructor course create/edit — parity of WebinarsController@storeAll/updateAll.
# Tags / filters / partner-instructors are separate subsystems (deferred).


class CourseCreate(BaseModel):
    type: CourseType
    title: str = Field(min_length=1, max_length=255)
    thumbnail: str
    image_cover: str
    description: str
    category_id: int
    duration: int | None = None

    # webinar-only scheduling (legacy required_if:type,webinar)
    start_date: datetime | None = None
    capacity: int | None = None

    seo_description: str | None = None
    video_demo: str | None = None
    video_demo_source: VideoDemoSource | None = None
    price: float = 0
    organization_price: float | None = None
    points: int | None = None
    access_days: int | None = None

    private: bool = False
    support: bool = False
    downloadable: bool = False
    partner_instructor: bool = False
    subscribe: bool = False

    # T&C accepted (legacy `rules` == 1); when false the course stays a draft.
    rules: bool = False
    # explicit "save as draft" (legacy `draft`/`get_next`)
    draft: bool = False


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    type: CourseType | None = None
    thumbnail: str | None = None
    image_cover: str | None = None
    description: str | None = None
    category_id: int | None = None
    duration: int | None = None
    start_date: datetime | None = None
    capacity: int | None = None
    seo_description: str | None = None
    video_demo: str | None = None
    video_demo_source: VideoDemoSource | None = None
    price: float | None = None
    organization_price: float | None = None
    points: int | None = None
    access_days: int | None = None
    private: bool | None = None
    support: bool | None = None
    downloadable: bool | None = None
    partner_instructor: bool | None = None
    subscribe: bool | None = None
