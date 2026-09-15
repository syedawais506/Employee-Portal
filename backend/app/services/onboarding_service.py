from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, TokenError, ValidationAppError
from app.core.security import hash_password
from app.db.rls import set_tenant_context
from app.models.employee import Employee
from app.models.onboarding import EmployeeDocument, OnboardingInvite
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.onboarding_repository import (
    DocumentTypeRepository,
    EmployeeDocumentRepository,
    OnboardingInviteRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.company import CompanyBrandingResponse
from app.schemas.onboarding import CompanyTourStepResponse, OnboardingContextResponse, OnboardingEmployeeInfo
from app.services.audit_service import audit_service
from app.services.branding_service import branding_service
from app.services.company_tour_service import company_tour_service
from app.services.notification_service import notification_service
from app.tasks.email_tasks import send_onboarding_invite_email
from app.utils.storage import (
    ALLOWED_CONTENT_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    build_document_key,
    generate_download_url,
    upload_document,
)

INVITE_VALIDITY_DAYS = 7


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


class OnboardingService:
    def __init__(self) -> None:
        self.invite_repo = OnboardingInviteRepository()
        self.document_type_repo = DocumentTypeRepository()
        self.employee_document_repo = EmployeeDocumentRepository()
        self.employee_repo = EmployeeRepository()
        self.user_repo = UserRepository()

    # -- HR/Admin side: creating the invite -----------------------------

    def create_invite(self, db: Session, *, company_id: uuid.UUID, employee: Employee) -> str:
        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_VALIDITY_DAYS)
        self.invite_repo.create(
            db,
            company_id=company_id,
            employee_id=employee.id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
        )
        send_onboarding_invite_email.delay(employee.email, raw_token)
        return raw_token

    # -- Public, token-authenticated side --------------------------------

    def _resolve_invite(self, db: Session, raw_token: str) -> tuple[OnboardingInvite, Employee]:
        # onboarding_invite itself is exempt from RLS (see migration 0019) —
        # it's looked up by its unguessable token hash before we know a
        # company_id at all, so there's nothing to scope this first query by.
        # Every RLS-protected table queried from here on (employee,
        # document_type, employee_document, company_tour_step) does need
        # tenant context, so it's set the moment we learn the invite's
        # company_id, before any of those follow-on queries run.
        invite = self.invite_repo.get_by_token_hash(db, _hash_token(raw_token))
        if invite is None:
            raise TokenError("This onboarding link is invalid.")
        set_tenant_context(db, str(invite.company_id))
        if invite.expires_at < datetime.now(timezone.utc):
            raise TokenError("This onboarding link has expired. Ask HR to resend an invite.")
        employee = self.employee_repo.get(db, invite.company_id, invite.employee_id)
        if employee is None:
            raise NotFoundError("Employee record not found")
        return invite, employee

    def get_context(self, db: Session, raw_token: str) -> OnboardingContextResponse:
        invite, employee = self._resolve_invite(db, raw_token)
        document_types = self.document_type_repo.list_all(db, employee.company_id)
        documents = self.employee_document_repo.list_for_employee(db, employee.company_id, employee.id)
        company = branding_service.get_branding(db, employee.company_id)
        tour_steps = company_tour_service.list_steps(db, employee.company_id)
        return OnboardingContextResponse(
            company_branding=CompanyBrandingResponse(
                name=company.name,
                logo_url=branding_service.logo_url(company),
                primary_color=company.primary_color,
            ),
            tour_steps=[
                CompanyTourStepResponse(
                    id=step.id,
                    title=step.title,
                    body=step.body,
                    image_url=company_tour_service.image_url(step),
                    sort_order=step.sort_order,
                )
                for step in tour_steps
            ],
            employee=OnboardingEmployeeInfo(
                first_name=employee.first_name,
                last_name=employee.last_name,
                email=employee.email,
                company_name=employee.company.name,
                onboarding_status=employee.onboarding_status,
            ),
            document_types=document_types,
            uploaded_documents=[
                {
                    "id": d.id,
                    "document_type_id": d.document_type_id,
                    "document_type_name": d.document_type.name,
                    "original_filename": d.original_filename,
                    "content_type": d.content_type,
                    "size_bytes": d.size_bytes,
                    "status": d.status,
                    "review_notes": d.review_notes,
                    "uploaded_at": d.uploaded_at,
                    "reviewed_at": d.reviewed_at,
                }
                for d in documents
            ],
            password_already_set=invite.used_at is not None,
            expires_at=invite.expires_at,
        )

    def set_password(self, db: Session, raw_token: str, password: str) -> None:
        invite, employee = self._resolve_invite(db, raw_token)
        if employee.onboarding_status != "invited":
            raise ValidationAppError("Onboarding has already moved past this step.")
        employee.user.password_hash = hash_password(password)
        invite.used_at = datetime.now(timezone.utc)
        db.flush()
        self._maybe_advance_to_submitted(db, employee)
        db.commit()

    def upload_document(
        self,
        db: Session,
        raw_token: str,
        *,
        document_type_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> EmployeeDocument:
        invite, employee = self._resolve_invite(db, raw_token)
        if employee.onboarding_status not in ("invited", "submitted"):
            raise ValidationAppError("Documents can no longer be updated at this onboarding stage.")

        document_type = self.document_type_repo.get(db, employee.company_id, document_type_id)
        if document_type is None:
            raise ValidationAppError("Unknown document type")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationAppError("Only PDF, PNG, and JPEG files are accepted.")
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise ValidationAppError("File exceeds the 10 MB upload limit.")

        key = build_document_key(
            company_id=employee.company_id,
            employee_id=employee.id,
            document_type_id=document_type_id,
            filename=filename,
        )
        upload_document(key=key, content=content)

        document = self.employee_document_repo.upsert(
            db,
            company_id=employee.company_id,
            employee_id=employee.id,
            document_type_id=document_type_id,
            file_key=key,
            original_filename=filename,
            content_type=content_type,
            size_bytes=len(content),
        )
        self._maybe_advance_to_submitted(db, employee)
        db.commit()
        return document

    def _maybe_advance_to_submitted(self, db: Session, employee: Employee) -> None:
        if employee.onboarding_status != "invited":
            return
        invite = self.invite_repo.get_by_employee_id(db, employee.id)
        if invite is None or invite.used_at is None:
            return
        required_types = self.document_type_repo.list_required(db, employee.company_id)
        uploaded = self.employee_document_repo.list_for_employee(db, employee.company_id, employee.id)
        uploaded_type_ids = {d.document_type_id for d in uploaded}
        if all(rt.id in uploaded_type_ids for rt in required_types):
            employee.onboarding_status = "submitted"
            db.flush()
            notification_service.notify_users_with_permission(
                db,
                employee.company_id,
                module="onboarding",
                action="review",
                type="onboarding.submitted",
                title=f"{employee.full_name} submitted onboarding documents",
                body="Ready for HR review",
                entity_type="employee",
                entity_id=employee.id,
            )

    # -- HR review ---------------------------------------------------------

    def review_document(
        self,
        db: Session,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        approve: bool,
        notes: str | None,
        actor_user_id: uuid.UUID,
        expiry_date: date | None = None,
    ) -> EmployeeDocument:
        document = self.employee_document_repo.get(db, company_id, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        document.status = "approved" if approve else "rejected"
        document.review_notes = notes
        document.reviewed_by = actor_user_id
        document.reviewed_at = datetime.now(timezone.utc)
        if expiry_date is not None:
            document.expiry_date = expiry_date
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="employee_document",
            entity_id=document.id,
            action="update",
            after={
                "status": document.status,
                "expiry_date": str(document.expiry_date) if document.expiry_date else None,
            },
        )
        db.commit()
        return document

    def hr_approve(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> Employee:
        employee = self.employee_repo.get(db, company_id, employee_id)
        if employee is None:
            raise NotFoundError("Employee not found")
        if employee.onboarding_status != "submitted":
            raise ValidationAppError("Employee has not submitted onboarding yet.")

        documents = self.employee_document_repo.list_for_employee(db, company_id, employee_id)
        required_types = self.document_type_repo.list_required(db, company_id)
        approved_type_ids = {d.document_type_id for d in documents if d.status == "approved"}
        if not all(rt.id in approved_type_ids for rt in required_types):
            raise ValidationAppError("All required documents must be approved before continuing.")

        employee.onboarding_status = "hr_approved"
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="employee",
            entity_id=employee.id,
            action="update",
            after={"onboarding_status": "hr_approved"},
        )
        db.commit()
        return employee

    # -- Admin final approval ----------------------------------------------

    def admin_approve(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> Employee:
        employee = self.employee_repo.get(db, company_id, employee_id)
        if employee is None:
            raise NotFoundError("Employee not found")
        if employee.onboarding_status != "hr_approved":
            raise ValidationAppError("Onboarding must be HR-approved before it can be activated.")

        employee.onboarding_status = "completed"
        employee.user.is_active = True
        employee.user.is_verified = True
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="employee",
            entity_id=employee.id,
            action="update",
            after={"onboarding_status": "completed"},
        )
        db.commit()
        return employee

    def document_download_url(self, db: Session, company_id: uuid.UUID, document_id: uuid.UUID) -> str:
        document = self.employee_document_repo.get(db, company_id, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        return generate_download_url(key=document.file_key)


onboarding_service = OnboardingService()
