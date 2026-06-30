from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.repositories import comments as comments_repo
from app.schemas.comment import MyCommentRead
from app.schemas.common import error_responses

router = APIRouter(prefix="/panel", tags=["comments"])


@router.get(
    "/my-comments",
    response_model=list[MyCommentRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_comments(current_user: CurrentUser, db: DbSession) -> list[MyCommentRead]:
    """The student's own comments (legacy panel `courses/my-comments`)."""
    comments = await comments_repo.list_for_user(db, current_user.id)
    return [
        MyCommentRead(
            id=c.id,
            comment=c.comment,
            status=c.status.value,
            course_id=c.course_id,
            blog_id=c.blog_id,
            created_at=c.created_at,
        )
        for c in comments
    ]
