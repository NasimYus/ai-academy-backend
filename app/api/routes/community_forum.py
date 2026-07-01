from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models.community_forum import ForumTopic, ForumTopicPost
from app.repositories import community_forum as forum_repo
from app.schemas.common import error_responses
from app.schemas.community_forum import (
    ForumAuthor,
    ForumCategoryRead,
    ForumPostCreate,
    ForumPostRead,
    ForumTopicCreate,
    ForumTopicDetail,
    ForumTopicRow,
    MyForumPostRow,
)

router = APIRouter(tags=["forum"])


def _author(user) -> ForumAuthor | None:
    if user is None:
        return None
    return ForumAuthor(id=user.id, full_name=user.full_name, avatar=user.avatar)


def _topic_row(topic: ForumTopic, posts_count: int) -> ForumTopicRow:
    return ForumTopicRow(
        id=topic.id,
        slug=topic.slug,
        forum_id=topic.forum_id,
        title=topic.title,
        cover=topic.cover,
        pin=topic.pin,
        close=topic.close,
        author=_author(topic.creator),
        posts_count=posts_count,
        created_at=topic.created_at,
    )


def _post_read(post: ForumTopicPost) -> ForumPostRead:
    return ForumPostRead(
        id=post.id,
        description=post.description,
        attach=post.attach,
        pin=post.pin,
        parent_id=post.parent_id,
        author=_author(post.user),
        created_at=post.created_at,
    )


@router.get("/forums", response_model=list[ForumCategoryRead])
async def list_categories(db: DbSession) -> list[ForumCategoryRead]:
    """Active forum categories with topic counts (legacy ForumController@index)."""
    return [
        ForumCategoryRead(
            id=cat.id,
            slug=cat.slug,
            title=cat.title,
            description=cat.description,
            icon=cat.icon,
            topics_count=count,
        )
        for cat, count in await forum_repo.list_categories(db)
    ]


@router.get(
    "/forums/{forum_id}/topics",
    response_model=list[ForumTopicRow],
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def list_topics(
    forum_id: int, db: DbSession, search: Annotated[str | None, Query()] = None
) -> list[ForumTopicRow]:
    if await forum_repo.get_category(db, forum_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forum not found")
    rows = await forum_repo.topics_in_category(db, forum_id, search)
    return [_topic_row(topic, count) for topic, count in rows]


@router.get(
    "/forum-topics/{slug}",
    response_model=ForumTopicDetail,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def topic_detail(slug: str, db: DbSession) -> ForumTopicDetail:
    topic = await forum_repo.get_topic_by_slug(db, slug)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    posts = await forum_repo.posts_for_topic(db, topic.id)
    return ForumTopicDetail(
        id=topic.id,
        slug=topic.slug,
        forum_id=topic.forum_id,
        title=topic.title,
        description=topic.description,
        cover=topic.cover,
        pin=topic.pin,
        close=topic.close,
        author=_author(topic.creator),
        created_at=topic.created_at,
        posts=[_post_read(p) for p in posts],
    )


@router.post(
    "/forum-topics",
    response_model=ForumTopicRow,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_CONTENT),
)
async def create_topic(
    payload: ForumTopicCreate, current_user: CurrentUser, db: DbSession
) -> ForumTopicRow:
    """Start a new topic (legacy ForumController@createTopic)."""
    if await forum_repo.get_category(db, payload.forum_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="forum_not_found"
        )
    topic = await forum_repo.create_topic(
        db,
        creator_id=current_user.id,
        forum_id=payload.forum_id,
        title=payload.title,
        description=payload.description,
        cover=payload.cover,
    )
    return _topic_row(topic, 0)


@router.post(
    "/forum-topics/{topic_id}/posts",
    response_model=ForumPostRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ),
)
async def create_post(
    topic_id: int, payload: ForumPostCreate, current_user: CurrentUser, db: DbSession
) -> ForumPostRead:
    topic = await db.get(ForumTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    if topic.close:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="topic_closed"
        )
    post = await forum_repo.create_post(
        db,
        user_id=current_user.id,
        topic_id=topic_id,
        description=payload.description,
        parent_id=payload.parent_id,
        attach=payload.attach,
    )
    return _post_read(post)


@router.get(
    "/panel/forums/topics",
    response_model=list[ForumTopicRow],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_topics(current_user: CurrentUser, db: DbSession) -> list[ForumTopicRow]:
    rows = await forum_repo.my_topics(db, current_user.id)
    return [_topic_row(topic, count) for topic, count in rows]


@router.get(
    "/panel/forums/posts",
    response_model=list[MyForumPostRow],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_posts(current_user: CurrentUser, db: DbSession) -> list[MyForumPostRow]:
    rows = await forum_repo.my_posts(db, current_user.id)
    return [
        MyForumPostRow(
            id=post.id,
            description=post.description,
            topic_title=title,
            topic_slug=slug,
            created_at=post.created_at,
        )
        for post, title, slug in rows
    ]
