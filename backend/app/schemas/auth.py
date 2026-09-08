import uuid

from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Password must be at least 10 characters long")
        if not any(c.isdigit() for c in value) or not any(c.isalpha() for c in value):
            raise ValueError("Password must contain at least one letter and one digit")
        return value


class VerifyEmailRequest(BaseModel):
    token: str


class CurrentUserResponse(ORMModel):
    id: uuid.UUID
    email: str
    company_id: uuid.UUID | None
    is_super_admin: bool
    is_verified: bool
    permissions: list[str] = []
    employee_id: uuid.UUID | None = None
    full_name: str | None = None
    ai_chatbot_enabled: bool = False
