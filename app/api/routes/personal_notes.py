from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.models.personal_note import NoteTargetType
from app.repositories import personal_notes as notes_repo
from app.schemas.common import error_responses
from app.schemas.personal_note import PersonalNoteRead
from app.services import storage

router = APIRouter(prefix="/personal-notes", tags=["personal-notes"])


@router.get(
    "",
    response_model=PersonalNoteRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def show_note(
    current_user: CurrentUser,
    db: DbSession,
    type: Annotated[NoteTargetType, Query()],
    item: Annotated[int, Query(description="target item id")],
) -> PersonalNoteRead:
    """A user's note for a content item (legacy CoursePersonalNotesController@show)."""
    note = await notes_repo.find(db, user_id=current_user.id, target_type=type, target_id=item)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return note


@router.post(
    "",
    response_model=PersonalNoteRead,
    responses=error_responses(status.HTTP_401_UNAUTHORIZED),
)
async def store_note(
    current_user: CurrentUser,
    db: DbSession,
    item_type: Annotated[NoteTargetType, Form()],
    item_id: Annotated[int, Form()],
    course_id: Annotated[int, Form()],
    note: Annotated[str, Form()],
    attachment: UploadFile | None = None,
) -> PersonalNoteRead:
    """Upsert a note (legacy CoursePersonalNotesController@store)."""
    row = await notes_repo.upsert(
        db,
        user_id=current_user.id,
        course_id=course_id,
        target_type=item_type,
        target_id=item_id,
        note=note,
    )
    if attachment is not None:
        path = storage.save_upload(attachment, f"personal_notes/{row.id}")
        await notes_repo.set_attachment(db, row, path)
    return row


@router.delete(
    "/delete/{note_id}",
    responses=error_responses(status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND),
)
async def destroy_note(note_id: int, current_user: CurrentUser, db: DbSession) -> dict[str, str]:
    """Delete a note (legacy destroy; scoped to the owner — legacy left it unscoped)."""
    note = await notes_repo.get_owned(db, note_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    await notes_repo.delete(db, note)
    return {"status": "ok"}
