from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    # In dev we surface the verification token so the SPA flow can be tested
    # without a real mailbox. In production this is sent by e-mail instead.
    user_id: int
    verification_token: str | None = None
