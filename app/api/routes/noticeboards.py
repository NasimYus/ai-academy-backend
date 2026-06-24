from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.noticeboard import CourseNoticeboard
from app.repositories import courses as courses_repo
from app.repositories import noticeboards as noticeboards_repo
from app.schemas.common import error_responses
from app.schemas.noticeboard import NoticeboardRead
from app.schemas.user import UserBrief

router = APIRouter(tags=["noticeboards"])

# Legacy CourseNoticeboard::getIcon — color → icon name.
_ICON_BY_COLOR = {
    "warning": "danger",
    "danger": "close-circle",
    "neutral": "more-circle",
    "info": "info-circle",
    "success": "tick-circle",
}


def _read(board: CourseNoticeboard) -> NoticeboardRead:
    return NoticeboardRead(
        id=board.id,
        title=board.title,
        message=board.message,
        color=board.color.value,
        icon=_ICON_BY_COLOR[board.color.value],
        created_at=board.created_at,
        creator=UserBrief.model_validate(board.creator) if board.creator else None,
    )


@router.get(
    "/courses/{course_id}/noticeboards",
    response_model=list[NoticeboardRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def list_noticeboards(
    course_id: int, current_user: CurrentUser, db: DbSession
) -> list[NoticeboardRead]:
    """Course announcements (legacy CourseNoticeboardController@index)."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    boards = await noticeboards_repo.list_for_course(db, course_id)
    return [_read(b) for b in boards]
