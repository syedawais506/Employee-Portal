import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.employee import Employee
from app.models.user import User
from app.schemas.onboarding import (
    DocumentReviewRequest,
    EmployeeDocumentResponse,
    OnboardingCompleteRequest,
    OnboardingContextResponse,
    OnboardingQueueEntry,
)
from app.services.onboarding_service import onboarding_service

onboarding_router = APIRouter(prefix="/onboarding", tags=["onboarding"])
management_router = APIRouter(prefix="/employees", tags=["onboarding"])


def _to_response(document) -> EmployeeDocumentResponse:  # noqa: ANN001
    return EmployeeDocumentResponse(
        id=document.id,
        document_type_id=document.document_type_id,
        document_type_name=document.document_type.name,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=document.status,
        review_notes=document.review_notes,
        uploaded_at=document.uploaded_at,
        reviewed_at=document.reviewed_at,
        expiry_date=document.expiry_date,
    )


@onboarding_router.get("/queue", response_model=list[OnboardingQueueEntry])
def onboarding_queue(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    stmt = (
        select(Employee)
        .where(
            Employee.company_id == company_id,
            Employee.onboarding_status.in_(["invited", "submitted", "hr_approved"]),
        )
        .order_by(Employee.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@onboarding_router.get("/{token}", response_model=OnboardingContextResponse)
def get_onboarding_context(token: str, db: Session = Depends(get_db)):
    return onboarding_service.get_context(db, token)


@onboarding_router.post("/{token}/password", status_code=204)
def set_onboarding_password(token: str, payload: OnboardingCompleteRequest, db: Session = Depends(get_db)):
    onboarding_service.set_password(db, token, payload.password)


@onboarding_router.post("/{token}/documents", response_model=list[EmployeeDocumentResponse], status_code=201)
async def upload_onboarding_documents(
    token: str,
    document_type_id: uuid.UUID = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    file_payloads = [
        (file.filename or "document", file.content_type or "application/octet-stream", await file.read())
        for file in files
    ]
    documents = onboarding_service.upload_documents(
        db, token, document_type_id=document_type_id, files=file_payloads
    )
    return [_to_response(document) for document in documents]


@management_router.get("/{employee_id}/documents", response_model=list[EmployeeDocumentResponse])
def list_employee_documents(
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    documents = onboarding_service.employee_document_repo.list_for_employee(db, company_id, employee_id)
    return [_to_response(d) for d in documents]


@management_router.post("/{employee_id}/documents/{document_id}/review", response_model=EmployeeDocumentResponse)
def review_employee_document(
    employee_id: uuid.UUID,  # noqa: ARG001 - part of the resource path, ownership enforced via company_id
    document_id: uuid.UUID,
    payload: DocumentReviewRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("onboarding", "review")),
):
    document = onboarding_service.review_document(
        db,
        company_id,
        document_id,
        approve=payload.approve,
        notes=payload.notes,
        actor_user_id=current_user.id,
        expiry_date=payload.expiry_date,
    )
    return _to_response(document)


@management_router.get("/{employee_id}/documents/{document_id}/download")
def download_employee_document(
    employee_id: uuid.UUID,  # noqa: ARG001
    document_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    return {"url": onboarding_service.document_download_url(db, company_id, document_id)}


@management_router.post("/{employee_id}/onboarding/hr-approve")
def hr_approve_onboarding(
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("onboarding", "review")),
):
    employee = onboarding_service.hr_approve(db, company_id, employee_id, actor_user_id=current_user.id)
    return {"onboarding_status": employee.onboarding_status}


@management_router.post("/{employee_id}/onboarding/approve")
def admin_approve_onboarding(
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("onboarding", "approve")),
):
    employee = onboarding_service.admin_approve(db, company_id, employee_id, actor_user_id=current_user.id)
    return {"onboarding_status": employee.onboarding_status}
