import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.community_forum import (
    ForumCategory,
    ForumCategoryStatus,
    ForumTopic,
    ForumTopicPost,
)


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "topic"


async def unique_topic_slug(db: AsyncSession, title: str) -> str:
    base = _slugify(title)
    candidate, i = base, 2
    while (await db.execute(select(ForumTopic.id).where(ForumTopic.slug == candidate))).first():
        candidate = f"{base}-{i}"
        i += 1
    return candidate


async def unique_category_slug(db: AsyncSession, title: str) -> str:
    base = _slugify(title)
    candidate, i = base, 2
    while (
        await db.execute(select(ForumCategory.id).where(ForumCategory.slug == candidate))
    ).first():
        candidate = f"{base}-{i}"
        i += 1
    return candidate


async def list_categories(db: AsyncSession) -> list[tuple[ForumCategory, int]]:
    result = await db.execute(
        select(ForumCategory, func.count(ForumTopic.id))
        .outerjoin(ForumTopic, ForumTopic.forum_id == ForumCategory.id)
        .where(ForumCategory.status == ForumCategoryStatus.active)
        .group_by(ForumCategory.id)
        .order_by(ForumCategory.order.asc(), ForumCategory.id.asc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_category(db: AsyncSession, category_id: int) -> ForumCategory | None:
    return await db.get(ForumCategory, category_id)


async def topics_in_category(
    db: AsyncSession, forum_id: int, search: str | None = None
) -> list[tuple[ForumTopic, int]]:
    query = (
        select(ForumTopic, func.count(ForumTopicPost.id))
        .outerjoin(ForumTopicPost, ForumTopicPost.topic_id == ForumTopic.id)
        .where(ForumTopic.forum_id == forum_id)
        .options(selectinload(ForumTopic.creator))
        .group_by(ForumTopic.id)
        .order_by(ForumTopic.pin.desc(), ForumTopic.created_at.desc())
    )
    if search:
        query = query.where(ForumTopic.title.ilike(f"%{search}%"))
    result = await db.execute(query)
    return [(row[0], row[1]) for row in result.all()]


async def get_topic_by_slug(db: AsyncSession, slug: str) -> ForumTopic | None:
    result = await db.execute(
        select(ForumTopic).where(ForumTopic.slug == slug).options(selectinload(ForumTopic.creator))
    )
    return result.scalars().first()


async def posts_for_topic(db: AsyncSession, topic_id: int) -> list[ForumTopicPost]:
    result = await db.execute(
        select(ForumTopicPost)
        .where(ForumTopicPost.topic_id == topic_id)
        .options(selectinload(ForumTopicPost.user))
        .order_by(ForumTopicPost.pin.desc(), ForumTopicPost.created_at.asc())
    )
    return list(result.scalars().all())


async def create_topic(
    db: AsyncSession,
    *,
    creator_id: int,
    forum_id: int,
    title: str,
    description: str,
    cover: str | None,
) -> ForumTopic:
    topic = ForumTopic(
        creator_id=creator_id,
        forum_id=forum_id,
        slug=await unique_topic_slug(db, title),
        title=title,
        description=description,
        cover=cover,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic, attribute_names=["creator"])
    return topic


async def create_post(
    db: AsyncSession,
    *,
    user_id: int,
    topic_id: int,
    description: str,
    parent_id: int | None,
    attach: str | None,
) -> ForumTopicPost:
    post = ForumTopicPost(
        user_id=user_id,
        topic_id=topic_id,
        description=description,
        parent_id=parent_id,
        attach=attach,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post, attribute_names=["user"])
    return post


async def my_topics(db: AsyncSession, user_id: int) -> list[tuple[ForumTopic, int]]:
    result = await db.execute(
        select(ForumTopic, func.count(ForumTopicPost.id))
        .outerjoin(ForumTopicPost, ForumTopicPost.topic_id == ForumTopic.id)
        .where(ForumTopic.creator_id == user_id)
        .options(selectinload(ForumTopic.creator))
        .group_by(ForumTopic.id)
        .order_by(ForumTopic.created_at.desc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def my_posts(db: AsyncSession, user_id: int) -> list[tuple[ForumTopicPost, str, str]]:
    result = await db.execute(
        select(ForumTopicPost, ForumTopic.title, ForumTopic.slug)
        .join(ForumTopic, ForumTopic.id == ForumTopicPost.topic_id)
        .where(ForumTopicPost.user_id == user_id)
        .options(selectinload(ForumTopicPost.user))
        .order_by(ForumTopicPost.created_at.desc())
    )
    return [(row[0], row[1], row[2]) for row in result.all()]
