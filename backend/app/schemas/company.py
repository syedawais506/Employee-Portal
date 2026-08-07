import uuid

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class CompanyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    status: str | None = None


class CompanyResponse(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
