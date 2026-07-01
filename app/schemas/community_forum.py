from datetime import datetime

from pydantic import BaseModel, Field


class ForumAuthor(BaseModel):
    id: int
    full_name: str | None = None
    avatar: str | None = None


class ForumCategoryRead(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None = None
    icon: str | None = None
    topics_count: int = 0


class ForumTopicRow(BaseModel):
    id: int
    slug: str
    forum_id: int
    title: str
    cover: str | None = None
    pin: bool = False
    close: bool = False
    author: ForumAuthor | None = None
    posts_count: int = 0
    created_at: datetime


class ForumPostRead(BaseModel):
    id: int
    description: str
    attach: str | None = None
    pin: bool = False
    parent_id: int | None = None
    author: ForumAuthor | None = None
    created_at: datetime


class ForumTopicDetail(BaseModel):
    id: int
    slug: str
    forum_id: int
    title: str
    description: str
    cover: str | None = None
    pin: bool = False
    close: bool = False
    author: ForumAuthor | None = None
    created_at: datetime
    posts: list[ForumPostRead] = []


class ForumTopicCreate(BaseModel):
    forum_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    cover: str | None = None


class ForumPostCreate(BaseModel):
    description: str = Field(min_length=1)
    parent_id: int | None = None
    attach: str | None = None


class MyForumPostRow(BaseModel):
    id: int
    description: str
    topic_title: str
    topic_slug: str
    created_at: datetime
