from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.models.support import SupportStatus
from app.repositories import courses as courses_repo
from app.repositories import support as support_repo
from app.schemas.common import error_responses
from app.schemas.support import (
    StoredAttach,
    SupportDepartmentRead,
    SupportDetail,
    SupportIndex,
    SupportType,
)
from app.services import storage
from app.services.support_presenter import to_detail

router = APIRouter(prefix="/support", tags=["support"])


@router.get(
    "/class_support",
    response_model=list[SupportDetail],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def class_support(current_user: CurrentUser, db: DbSession) -> list[SupportDetail]:
    """Course tickets the user opened (legacy SupportsController@classSupport)."""
    rows = await support_repo.class_support(db, current_user.id)
    return [to_detail(s) for s in rows]


@router.get(
    "/my_class_support",
    response_model=list[SupportDetail],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def my_class_support(current_user: CurrentUser, db: DbSession) -> list[SupportDetail]:
    """Course tickets on courses the user teaches (legacy @myClassSupport)."""
    course_ids = await support_repo.taught_course_ids(db, current_user.id)
    rows = await support_repo.my_class_support(db, course_ids)
    return [to_detail(s) for s in rows]


@router.get(
    "/tickets",
    response_model=list[SupportDetail],
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def tickets(current_user: CurrentUser, db: DbSession) -> list[SupportDetail]:
    """Platform tickets the user opened (legacy SupportsController@platformSupport)."""
    rows = await support_repo.platform_support(db, current_user.id)
    return [to_detail(s) for s in rows]


@router.get(
    "/departments",
    response_model=list[SupportDepartmentRead],
)
async def departments(db: DbSession) -> list[SupportDepartmentRead]:
    """Platform support departments (legacy SupportDepartmentsController@index)."""
    rows = await support_repo.list_departments(db)
    return [SupportDepartmentRead(id=d.id, title=d.title) for d in rows]


@router.get(
    "",
    response_model=SupportIndex,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def index(current_user: CurrentUser, db: DbSession) -> SupportIndex:
    """All of the user's support (legacy SupportsController@index)."""
    course_ids = await support_repo.taught_course_ids(db, current_user.id)
    mine = await support_repo.class_support(db, current_user.id)
    teaching = await support_repo.my_class_support(db, course_ids)
    platform = await support_repo.platform_support(db, current_user.id)
    return SupportIndex(
        class_support=[to_detail(s) for s in mine],
        my_class_support=[to_detail(s) for s in teaching],
        tickets=[to_detail(s) for s in platform],
    )


@router.get(
    "/{support_id}",
    response_model=SupportDetail,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def show(support_id: int, current_user: CurrentUser, db: DbSession) -> SupportDetail:
    """A single ticket (legacy SupportsController@show)."""
    support = await support_repo.get_detail(db, support_id)
    if support is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support not found")
    return to_detail(support)


@router.post(
    "",
    response_model=StoredAttach,
    responses=error_responses(
        status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND
    ),
)
async def store(
    current_user: CurrentUser,
    db: DbSession,
    title: Annotated[str, Form(min_length=2)],
    type: Annotated[SupportType, Form()],
    message: Annotated[str, Form(min_length=2)],
    department_id: Annotated[int | None, Form()] = None,
    course_id: Annotated[int | None, Form()] = None,
    attach: UploadFile | None = None,
) -> StoredAttach:
    """Open a new support ticket (legacy SupportsController@store)."""
    if type == SupportType.course_support:
        if course_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="course_required")
        if await courses_repo.get_by_id(db, course_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        department_id = None  # course tickets carry no department (legacy)
    else:
        if department_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="department_required"
            )
        if not await support_repo.department_exists(db, department_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )
        course_id = None  # platform tickets carry no course (legacy)

    attach_path = storage.save_upload(attach, "supports") if attach is not None else None
    support = await support_repo.create_support(
        db,
        user_id=current_user.id,
        title=title,
        course_id=course_id,
        department_id=department_id,
        message=message,
        attach=attach_path,
    )
    _ = support
    return StoredAttach(attach=attach_path)


@router.post(
    "/{support_id}/conversations",
    response_model=StoredAttach,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def store_conversation(
    support_id: int,
    current_user: CurrentUser,
    db: DbSession,
    message: Annotated[str, Form(min_length=2)],
    attachment: UploadFile | None = None,
) -> StoredAttach:
    """Reply to a ticket (legacy SupportsController@storeConversations)."""
    course_ids = await support_repo.taught_course_ids(db, current_user.id)
    support = await support_repo.get_for_participant(
        db, support_id, user_id=current_user.id, course_ids=course_ids
    )
    if support is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support not found")

    # Owner reply re-opens the ticket; a teacher reply marks it replied (legacy).
    is_owner = support.user_id == current_user.id
    new_status = SupportStatus.open if is_owner else SupportStatus.replied
    attach_path = None
    if attachment is not None:
        attach_path = storage.save_upload(attachment, f"supports/{support_id}")
    await support_repo.add_conversation(
        db,
        support=support,
        sender_id=current_user.id,
        message=message,
        attach=attach_path,
        status=new_status,
    )
    return StoredAttach(attach=attach_path)


@router.get(
    "/{support_id}/close",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def close(support_id: int, current_user: CurrentUser, db: DbSession) -> dict[str, str]:
    """Close a ticket (legacy SupportsController@close — GET in legacy)."""
    course_ids = await support_repo.taught_course_ids(db, current_user.id)
    support = await support_repo.get_for_participant(
        db, support_id, user_id=current_user.id, course_ids=course_ids
    )
    if support is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support not found")
    await support_repo.set_status(db, support, SupportStatus.close)
    return {"status": "closed"}
