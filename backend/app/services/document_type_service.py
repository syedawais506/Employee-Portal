from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.onboarding import DocumentType
from app.repositories.onboarding_repository import DocumentTypeRepository
from app.services.audit_service import audit_service


class DocumentTypeService:
    def __init__(self) -> None:
        self.repo = DocumentTypeRepository()

    def list_document_types(self, db: Session, company_id: uuid.UUID) -> list[DocumentType]:
        return self.repo.list_all(db, company_id)

    def get_document_type(self, db: Session, company_id: uuid.UUID, document_type_id: uuid.UUID) -> DocumentType:
        document_type = self.repo.get(db, company_id, document_type_id)
        if document_type is None:
            raise NotFoundError("Document type not found")
        return document_type

    def create_document_type(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str,
        is_required: bool,
        sort_order: int,
        actor_user_id: uuid.UUID,
    ) -> DocumentType:
        if any(dt.name == name for dt in self.repo.list_all(db, company_id)):
            raise ConflictError("A document type with this name already exists")
        document_type = self.repo.create(db, company_id, name=name, is_required=is_required, sort_order=sort_order)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="document_type",
            entity_id=document_type.id,
            action="create",
            after={"name": name},
        )
        db.commit()
        return document_type

    def update_document_type(
        self,
        db: Session,
        company_id: uuid.UUID,
        document_type_id: uuid.UUID,
        *,
        name: str | None,
        is_required: bool | None,
        sort_order: int | None,
        actor_user_id: uuid.UUID,
    ) -> DocumentType:
        document_type = self.get_document_type(db, company_id, document_type_id)
        before = {"name": document_type.name, "is_required": document_type.is_required}
        if name is not None:
            document_type.name = name
        if is_required is not None:
            document_type.is_required = is_required
        if sort_order is not None:
            document_type.sort_order = sort_order
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="document_type",
            entity_id=document_type.id,
            action="update",
            before=before,
            after={"name": document_type.name, "is_required": document_type.is_required},
        )
        db.commit()
        return document_type

    def delete_document_type(
        self, db: Session, company_id: uuid.UUID, document_type_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        document_type = self.get_document_type(db, company_id, document_type_id)
        self.repo.delete(db, company_id, document_type_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="document_type",
            entity_id=document_type_id,
            action="delete",
            before={"name": document_type.name},
        )
        db.commit()


document_type_service = DocumentTypeService()
