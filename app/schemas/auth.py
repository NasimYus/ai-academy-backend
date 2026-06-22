from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str  # email or mobile (legacy parity)
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    profile_completion: list[str] = []


class LogoutResult(BaseModel):
    status: str = "logout"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthToken(Token):
    """Token plus the authenticated user id (returned after register step 3)."""

    user_id: int


# --- registration (3-step flow, legacy parity) ---


class RegisterStep1(BaseModel):
    email: EmailStr | None = None
    mobile: str | None = None
    country_code: str | None = None
    password: str = Field(min_length=6)
    password_confirmation: str


class RegisterStep1Response(BaseModel):
    # status: "stored" (new) | "go_step_2" (exists, unverified) | "go_step_3" (verified, no name)
    status: str
    user_id: int
    code: str | None = None  # surfaced only in debug for testing


class RegisterStep2(BaseModel):
    user_id: int
    code: str


class VerificationResult(BaseModel):
    status: str = "verified"


class RegisterStep3(BaseModel):
    user_id: int
    full_name: str = Field(min_length=3)
    referral_code: str | None = None


class VerificationConfirm(BaseModel):
    username: str  # email or mobile
    code: str
    referral_code: str | None = None


# --- forgot / reset password (legacy parity) ---


class ForgotPasswordRequest(BaseModel):
    type: str | None = None  # "mobile" or None/anything else => email
    email: EmailStr | None = None
    mobile: str | None = None
    country_code: str | None = None


class ForgotPasswordResult(BaseModel):
    status: str  # "done"
    # Delivery (email/SMS) is deferred; these are surfaced only in debug for testing.
    token: str | None = None
    new_password: str | None = None


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    password_confirmation: str


class ResetPasswordResult(BaseModel):
    status: str  # "reset" | "no_request"
