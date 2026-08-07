from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.onboarding import DocumentType, EmployeeDocument, OnboardingInvite
from app.repositories.base import TenantScopedRepository


class DocumentTypeRepository(TenantScopedRepository[DocumentType]):
    model = DocumentType

    def list_all(self, db: Session, company_id: uuid.UUID) -> list[DocumentType]:
        stmt = (
            select(DocumentType)
            .where(DocumentType.company_id == company_id)
            .order_by(DocumentType.sort_order, DocumentType.name)
        )
        return list(db.execute(stmt).scalars().all())

    def list_required(self, db: Session, company_id: uuid.UUID) -> list[DocumentType]:
        stmt = select(DocumentType).where(
            DocumentType.company_id == company_id, DocumentType.is_required.is_(True)
        )
        return list(db.execute(stmt).scalars().all())


class EmployeeDocumentRepository:
    def list_for_employee(self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID) -> list[EmployeeDocument]:
        stmt = (
            select(EmployeeDocument)
            .options(joinedload(EmployeeDocument.document_type))
            .where(EmployeeDocument.company_id == company_id, EmployeeDocument.employee_id == employee_id)
        )
        return list(db.execute(stmt).scalars().all())

    def get(self, db: Session, company_id: uuid.UUID, document_id: uuid.UUID) -> EmployeeDocument | None:
        stmt = select(EmployeeDocument).where(
            EmployeeDocument.id == document_id, EmployeeDocument.company_id == company_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_type(
        self, db: Session, employee_id: uuid.UUID, document_type_id: uuid.UUID
    ) -> EmployeeDocument | None:
        stmt = select(EmployeeDocument).where(
            EmployeeDocument.employee_id == employee_id, EmployeeDocument.document_type_id == document_type_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def upsert(
        self,
        db: Session,
        *,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        document_type_id: uuid.UUID,
        file_key: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
    ) -> EmployeeDocument:
        existing = self.get_by_type(db, employee_id, document_type_id)
        if existing is not None:
            existing.file_key = file_key
            existing.original_filename = original_filename
            existing.content_type = content_type
            existing.size_bytes = size_bytes
            existing.status = "pending"
            existing.review_notes = None
            existing.reviewed_by = None
            existing.reviewed_at = None
            db.flush()
            return existing

        document = EmployeeDocument(
            company_id=company_id,
            employee_id=employee_id,
            document_type_id=document_type_id,
            file_key=file_key,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            status="pending",
        )
        db.add(document)
        db.flush()
        return document


class OnboardingInviteRepository:
    def create(
        self, db: Session, *, company_id: uuid.UUID, employee_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> OnboardingInvite:
        invite = OnboardingInvite(
            company_id=company_id, employee_id=employee_id, token_hash=token_hash, expires_at=expires_at
        )
        db.add(invite)
        db.flush()
        return invite

    def get_by_token_hash(self, db: Session, token_hash: str) -> OnboardingInvite | None:
        stmt = select(OnboardingInvite).where(OnboardingInvite.token_hash == token_hash)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_employee_id(self, db: Session, employee_id: uuid.UUID) -> OnboardingInvite | None:
        stmt = select(OnboardingInvite).where(OnboardingInvite.employee_id == employee_id)
        return db.execute(stmt).scalar_one_or_none()
