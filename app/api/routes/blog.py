from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.repositories import blog as blog_repo
from app.schemas.blog import (
    BlogCategoryRead,
    BlogCommentCreate,
    BlogList,
    BlogShow,
)
from app.schemas.common import error_responses
from app.services import blog_presenter

router = APIRouter(prefix="/blogs", tags=["blog"])


@router.get("", response_model=BlogList)
async def index(
    db: DbSession,
    cat: Annotated[int | None, Query()] = None,
    limit: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int | None, Query(ge=0)] = None,
) -> BlogList:
    """Published posts (legacy Web\\BlogController@index, ?cat/?limit/?offset)."""
    blogs = await blog_repo.list_published(db, category_id=cat, limit=limit, offset=offset)
    counts = await blog_repo.comment_counts(db, [b.id for b in blogs])
    return BlogList(
        count=len(blogs),
        blogs=[blog_presenter.to_brief(b, counts.get(b.id, 0)) for b in blogs],
    )


@router.get("/categories", response_model=list[BlogCategoryRead])
async def categories(db: DbSession) -> list[BlogCategoryRead]:
    """Blog categories (legacy Web\\BlogCategoryController@index)."""
    rows = await blog_repo.list_categories(db)
    return [BlogCategoryRead(id=c.id, title=c.title, slug=c.slug) for c in rows]


@router.get(
    "/{blog_id}",
    response_model=BlogShow,
    responses=error_responses(status.HTTP_404_NOT_FOUND),
)
async def show(blog_id: int, db: DbSession) -> BlogShow:
    """A single published post with its comments (legacy Web\\BlogController@show)."""
    blog = await blog_repo.get_published(db, blog_id)
    if blog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found")
    comments = await blog_repo.list_comments(db, blog_id)
    return BlogShow(blog=blog_presenter.to_detail(blog, comments))


@router.post(
    "/{blog_id}/comments",
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def add_comment(
    blog_id: int, payload: BlogCommentCreate, current_user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Post a comment/reply on a blog (legacy CommentsController@store, item=blog)."""
    blog = await blog_repo.get_by_id(db, blog_id)
    if blog is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found")
    if not blog.enable_comment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="comments_disabled")
    await blog_repo.add_comment(
        db,
        blog_id=blog_id,
        user_id=current_user.id,
        comment=payload.comment,
        reply_id=payload.reply_id,
    )
    return {"status": "stored"}
