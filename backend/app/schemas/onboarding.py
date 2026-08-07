import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DocumentTypeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    is_required: bool = True
    sort_order: int = 0


class DocumentTypeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    is_required: bool | None = None
    sort_order: int | None = None


class DocumentTypeResponse(ORMModel):
    id: uuid.UUID
    name: str
    is_required: bool
    sort_order: int


class EmployeeDocumentResponse(ORMModel):
    id: uuid.UUID
    document_type_id: uuid.UUID
    document_type_name: str
    original_filename: str
    content_type: str
    size_bytes: int
    status: str
    review_notes: str | None
    uploaded_at: datetime
    reviewed_at: datetime | None


class DocumentReviewRequest(BaseModel):
    approve: bool
    notes: str | None = None


class OnboardingCompleteRequest(BaseModel):
    password: str = Field(min_length=10)


class OnboardingEmployeeInfo(BaseModel):
    first_name: str
    last_name: str
    email: str
    company_name: str
    onboarding_status: str


class OnboardingContextResponse(BaseModel):
    employee: OnboardingEmployeeInfo
    document_types: list[DocumentTypeResponse]
    uploaded_documents: list[EmployeeDocumentResponse]
    password_already_set: bool
    expires_at: datetime


class OnboardingQueueEntry(ORMModel):
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    onboarding_status: str
