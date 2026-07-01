from pydantic import BaseModel, Field


class AdminCategoryRead(BaseModel):
    id: int
    parent_id: int | None = None
    title: str
    slug: str | None = None
    icon: str | None = None
    order: int = 0
    enable: bool = True


class CategoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    parent_id: int | None = None
    icon: str | None = None
    order: int = 0
    enable: bool = True


class CategoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=64)
    parent_id: int | None = None
    icon: str | None = None
    order: int | None = None
    enable: bool | None = None
