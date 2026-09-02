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


class IntegrationSettingsResponse(ORMModel):
    slack_webhook_url: str | None


class IntegrationSettingsUpdateRequest(BaseModel):
    slack_webhook_url: str | None = Field(default=None, max_length=500)


class WebhookTestResponse(BaseModel):
    sent: bool


class CompanyBrandingResponse(BaseModel):
    name: str
    logo_url: str | None
    primary_color: str | None


class CompanyBrandingColorUpdateRequest(BaseModel):
    primary_color: str | None = Field(default=None, max_length=20, pattern=r"^#[0-9a-fA-F]{6}$")
