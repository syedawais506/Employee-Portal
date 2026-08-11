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


@onboarding_router.post("/{token}/documents", response_model=EmployeeDocumentResponse, status_code=201)
async def upload_onboarding_document(
    token: str,
    document_type_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    document = onboarding_service.upload_document(
        db,
        token,
        document_type_id=document_type_id,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
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
    )


@management_router.get("/{employee_id}/documents", response_model=list[EmployeeDocumentResponse])
def list_employee_documents(
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    documents = onboarding_service.employee_document_repo.list_for_employee(db, company_id, employee_id)
    return [
        EmployeeDocumentResponse(
            id=d.id,
            document_type_id=d.document_type_id,
            document_type_name=d.document_type.name,
            original_filename=d.original_filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            status=d.status,
            review_notes=d.review_notes,
            uploaded_at=d.uploaded_at,
            reviewed_at=d.reviewed_at,
        )
        for d in documents
    ]


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
    )
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
    )


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
