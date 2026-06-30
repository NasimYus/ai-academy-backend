from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactResponse

router = APIRouter(tags=["contact"])


@router.post("/contact", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def submit_contact(payload: ContactCreate, db: DbSession) -> ContactResponse:
    """Public contact-form submission (legacy ContactController@store).

    Stores the message; admin notification/email are settings-gated (deferred,
    like the other notification stubs)."""
    db.add(
        Contact(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            subject=payload.subject,
            message=payload.message,
        )
    )
    await db.commit()
    return ContactResponse(message="sent")
