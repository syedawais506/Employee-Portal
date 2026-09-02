from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.services.audit_service import audit_service
from app.utils.storage import (
    MAX_UPLOAD_SIZE_BYTES,
    build_branding_logo_key,
    generate_download_url,
    upload_document,
)

ALLOWED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg"}
LOGO_URL_EXPIRY_SECONDS = 3600


class BrandingService:
    def __init__(self) -> None:
        self.company_repo = CompanyRepository()

    def _get_company(self, db: Session, company_id: uuid.UUID) -> Company:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    def logo_url(self, company: Company) -> str | None:
        if company.logo_key is None:
            return None
        return generate_download_url(key=company.logo_key, expires_in_seconds=LOGO_URL_EXPIRY_SECONDS)

    def get_branding(self, db: Session, company_id: uuid.UUID) -> Company:
        return self._get_company(db, company_id)

    def update_color(
        self, db: Session, company_id: uuid.UUID, *, primary_color: str | None, actor_user_id: uuid.UUID
    ) -> Company:
        company = self._get_company(db, company_id)
        before = company.primary_color
        company.primary_color = primary_color
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="company_branding",
            entity_id=company_id,
            action="update",
            before={"primary_color": before},
            after={"primary_color": primary_color},
        )
        db.commit()
        return company

    def upload_logo(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        actor_user_id: uuid.UUID,
    ) -> Company:
        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise ValidationAppError("Only PNG and JPEG images are accepted.")
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise ValidationAppError("File exceeds the 10 MB upload limit.")

        company = self._get_company(db, company_id)
        key = build_branding_logo_key(company_id=company_id, filename=filename)
        upload_document(key=key, content=content, content_type=content_type)
        company.logo_key = key
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="company_branding",
            entity_id=company_id,
            action="update",
            after={"logo_uploaded": True},
        )
        db.commit()
        return company


branding_service = BrandingService()
