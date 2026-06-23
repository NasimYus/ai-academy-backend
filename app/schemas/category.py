from pydantic import BaseModel


class SubCategoryRead(BaseModel):
    id: int
    title: str
    icon: str | None = None
    webinars_count: int = 0


class CategoryRead(BaseModel):
    id: int
    title: str
    color: str | None = None
    icon: str | None = None
    sub_categories: list[SubCategoryRead] = []
    webinars_count: int = 0


class CategoryList(BaseModel):
    count: int
    categories: list[CategoryRead]


class TrendCategoryRead(BaseModel):
    id: int  # category id
    title: str
    color: str | None = None
    icon: str | None = None


class TrendCategoryList(BaseModel):
    count: int
    categories: list[TrendCategoryRead]
