from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=64)
    subject: str = Field(min_length=2, max_length=255)
    message: str = Field(min_length=2)


class ContactResponse(BaseModel):
    message: str
