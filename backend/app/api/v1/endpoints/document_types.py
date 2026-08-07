import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.user import User
from app.schemas.onboarding import DocumentTypeCreateRequest, DocumentTypeResponse, DocumentTypeUpdateRequest
from app.services.document_type_service import document_type_service

router = APIRouter(prefix="/document-types", tags=["onboarding"])


@router.get("", response_model=list[DocumentTypeResponse])
def list_document_types(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    return document_type_service.list_document_types(db, company_id)


@router.post("", response_model=DocumentTypeResponse, status_code=201)
def create_document_type(
    payload: DocumentTypeCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("onboarding", "configure")),
):
    return document_type_service.create_document_type(
        db,
        company_id,
        name=payload.name,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
        actor_user_id=current_user.id,
    )


@router.patch("/{document_type_id}", response_model=DocumentTypeResponse)
def update_document_type(
    document_type_id: uuid.UUID,
    payload: DocumentTypeUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("onboarding", "configure")),
):
    return document_type_service.update_document_type(
        db,
        company_id,
        document_type_id,
        name=payload.name,
        is_required=payload.is_required,
        sort_order=payload.sort_order,
        actor_user_id=current_user.id,
    )


@router.delete("/{document_type_id}", status_code=204)
def delete_document_type(
    document_type_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("onboarding", "configure")),
):
    document_type_service.delete_document_type(db, company_id, document_type_id, actor_user_id=current_user.id)
