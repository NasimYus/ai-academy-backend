from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.repositories import courses as courses_repo
from app.repositories import forums as forums_repo
from app.schemas.common import error_responses
from app.schemas.forum import (
    ForumAnswerInput,
    ForumAnswerRead,
    ForumListResponse,
    ForumThreadRead,
)
from app.services import access, storage
from app.services import forums as forum_service

router = APIRouter(tags=["forums"])

_NOT_PURCHASED = "not_purchased"
_FORBIDDEN = "forbidden"


async def _require_access(db, current_user, course_id: int):
    """Legacy WebinarPolicy@view — must have course access. Returns the course."""
    course = await courses_repo.get_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not await access.has_course_access(db, current_user, course):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_NOT_PURCHASED)
    return course


# ---- threads -------------------------------------------------------------


@router.get(
    "/courses/{course_id}/forums",
    response_model=ForumListResponse,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def list_forums(
    course_id: int,
    current_user: CurrentUser,
    db: DbSession,
    search: Annotated[str | None, Query()] = None,
) -> ForumListResponse:
    """Course Q&A threads + aggregate counts (legacy CourseForumController@index)."""
    course = await _require_access(db, current_user, course_id)
    threads = await forums_repo.list_for_course(db, course_id, search)
    stats = await forums_repo.counts(db, course_id)
    return ForumListResponse(
        forums=[forum_service.thread_read(t, current_user, course) for t in threads], **stats
    )


@router.post(
    "/courses/{course_id}/forums",
    response_model=ForumThreadRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def create_forum(
    course_id: int,
    current_user: CurrentUser,
    db: DbSession,
    title: Annotated[str, Form(max_length=255)],
    description: Annotated[str, Form()],
    attachment: UploadFile | None = None,
) -> ForumThreadRead:
    """Open a question (legacy CourseForumController@store)."""
    course = await _require_access(db, current_user, course_id)
    forum = await forums_repo.create_thread(
        db, course_id=course_id, user_id=current_user.id, title=title, description=description
    )
    if attachment is not None:
        forum.attach = storage.save_upload(attachment, f"forums/{forum.id}")
        forum = await forums_repo.save_thread(db, forum)
    return forum_service.thread_read(forum, current_user, course)


@router.put(
    "/forums/{forum_id}",
    response_model=ForumThreadRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def update_forum(
    forum_id: int,
    current_user: CurrentUser,
    db: DbSession,
    title: Annotated[str, Form(max_length=255)],
    description: Annotated[str, Form()],
    attachment: UploadFile | None = None,
) -> ForumThreadRead:
    """Edit a question — author only (legacy CourseForumController@update)."""
    forum = await forums_repo.get_thread(db, forum_id)
    if forum is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forum not found")
    course = await _require_access(db, current_user, forum.course_id)
    if forum.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)

    forum.title = title
    forum.description = description
    if attachment is not None:
        forum.attach = storage.save_upload(attachment, f"forums/{forum.id}")
    forum = await forums_repo.save_thread(db, forum)
    return forum_service.thread_read(forum, current_user, course)


@router.post(
    "/forums/{forum_id}/pin",
    response_model=ForumThreadRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def pin_forum(forum_id: int, current_user: CurrentUser, db: DbSession) -> ForumThreadRead:
    """Toggle pin — course owner only (legacy CourseForumController@pin)."""
    forum = await forums_repo.get_thread(db, forum_id)
    if forum is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forum not found")
    course = await _require_access(db, current_user, forum.course_id)
    if not forum_service.is_course_owner(course, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    forum.pin = not forum.pin
    forum = await forums_repo.save_thread(db, forum)
    return forum_service.thread_read(forum, current_user, course)


# ---- answers -------------------------------------------------------------


async def _answer_context(db, current_user, answer_id: int):
    """Load (answer, thread, course) and gate on course access. 404 if missing."""
    answer = await forums_repo.get_answer(db, answer_id)
    if answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
    thread = await forums_repo.get_thread(db, answer.forum_id)
    course = await _require_access(db, current_user, thread.course_id)
    return answer, thread, course


@router.get(
    "/forums/{forum_id}/answers",
    response_model=list[ForumAnswerRead],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def list_answers(
    forum_id: int, current_user: CurrentUser, db: DbSession
) -> list[ForumAnswerRead]:
    """Answers on a thread (legacy CourseForumAnswerController@index)."""
    forum = await forums_repo.get_thread(db, forum_id)
    if forum is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forum not found")
    course = await _require_access(db, current_user, forum.course_id)
    answers = await forums_repo.list_answers(db, forum_id)
    return [forum_service.answer_read(a, current_user, course, forum.user_id) for a in answers]


@router.post(
    "/forums/{forum_id}/answers",
    response_model=ForumAnswerRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def create_answer(
    forum_id: int, payload: ForumAnswerInput, current_user: CurrentUser, db: DbSession
) -> ForumAnswerRead:
    """Answer a question (legacy CourseForumAnswerController@store)."""
    forum = await forums_repo.get_thread(db, forum_id)
    if forum is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forum not found")
    course = await _require_access(db, current_user, forum.course_id)
    answer = await forums_repo.create_answer(
        db, forum_id=forum_id, user_id=current_user.id, description=payload.description
    )
    return forum_service.answer_read(answer, current_user, course, forum.user_id)


@router.put(
    "/answers/{answer_id}",
    response_model=ForumAnswerRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def update_answer(
    answer_id: int, payload: ForumAnswerInput, current_user: CurrentUser, db: DbSession
) -> ForumAnswerRead:
    """Edit an answer — author only (legacy CourseForumAnswerController@update)."""
    answer, thread, course = await _answer_context(db, current_user, answer_id)
    if answer.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    answer.description = payload.description
    answer = await forums_repo.save_answer(db, answer)
    return forum_service.answer_read(answer, current_user, course, thread.user_id)


@router.post(
    "/answers/{answer_id}/pin",
    response_model=ForumAnswerRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def pin_answer(answer_id: int, current_user: CurrentUser, db: DbSession) -> ForumAnswerRead:
    """Toggle answer pin — course owner only."""
    answer, thread, course = await _answer_context(db, current_user, answer_id)
    if not forum_service.is_course_owner(course, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    answer.pin = not answer.pin
    answer = await forums_repo.save_answer(db, answer)
    return forum_service.answer_read(answer, current_user, course, thread.user_id)


@router.post(
    "/answers/{answer_id}/resolve",
    response_model=ForumAnswerRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, 404),
)
async def resolve_answer(
    answer_id: int, current_user: CurrentUser, db: DbSession
) -> ForumAnswerRead:
    """Toggle resolved — course owner or the question author."""
    answer, thread, course = await _answer_context(db, current_user, answer_id)
    if not (
        forum_service.is_course_owner(course, current_user) or thread.user_id == current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)
    answer.resolved = not answer.resolved
    answer = await forums_repo.save_answer(db, answer)
    return forum_service.answer_read(answer, current_user, course, thread.user_id)
