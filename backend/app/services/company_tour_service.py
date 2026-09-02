from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.onboarding import CompanyTourStep
from app.repositories.onboarding_repository import CompanyTourStepRepository
from app.services.audit_service import audit_service
from app.utils.storage import (
    MAX_UPLOAD_SIZE_BYTES,
    build_tour_step_image_key,
    generate_download_url,
    upload_document,
)

ALLOWED_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg"}
TOUR_IMAGE_URL_EXPIRY_SECONDS = 3600


class CompanyTourService:
    def __init__(self) -> None:
        self.repo = CompanyTourStepRepository()

    def image_url(self, step: CompanyTourStep) -> str | None:
        if step.image_key is None:
            return None
        return generate_download_url(key=step.image_key, expires_in_seconds=TOUR_IMAGE_URL_EXPIRY_SECONDS)

    def list_steps(self, db: Session, company_id: uuid.UUID) -> list[CompanyTourStep]:
        return self.repo.list_all(db, company_id)

    def get_step(self, db: Session, company_id: uuid.UUID, step_id: uuid.UUID) -> CompanyTourStep:
        step = self.repo.get(db, company_id, step_id)
        if step is None:
            raise NotFoundError("Company tour step not found")
        return step

    def create_step(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        title: str,
        body: str,
        sort_order: int,
        image: tuple[bytes, str, str] | None,
        actor_user_id: uuid.UUID,
    ) -> CompanyTourStep:
        image_key = None
        if image is not None:
            content, filename, content_type = image
            if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                raise ValidationAppError("Only PNG and JPEG images are accepted.")
            if len(content) > MAX_UPLOAD_SIZE_BYTES:
                raise ValidationAppError("File exceeds the 10 MB upload limit.")
            image_key = build_tour_step_image_key(company_id=company_id, filename=filename)
            upload_document(key=image_key, content=content, content_type=content_type)

        step = self.repo.create(db, company_id, title=title, body=body, sort_order=sort_order, image_key=image_key)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="company_tour_step",
            entity_id=step.id,
            action="create",
            after={"title": title},
        )
        db.commit()
        return step

    def update_step(
        self,
        db: Session,
        company_id: uuid.UUID,
        step_id: uuid.UUID,
        *,
        title: str | None,
        body: str | None,
        sort_order: int | None,
        actor_user_id: uuid.UUID,
    ) -> CompanyTourStep:
        step = self.get_step(db, company_id, step_id)
        before = {"title": step.title}
        if title is not None:
            step.title = title
        if body is not None:
            step.body = body
        if sort_order is not None:
            step.sort_order = sort_order
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="company_tour_step",
            entity_id=step.id,
            action="update",
            before=before,
            after={"title": step.title},
        )
        db.commit()
        return step

    def delete_step(self, db: Session, company_id: uuid.UUID, step_id: uuid.UUID, *, actor_user_id: uuid.UUID) -> None:
        step = self.get_step(db, company_id, step_id)
        self.repo.delete(db, company_id, step_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="company_tour_step",
            entity_id=step_id,
            action="delete",
            before={"title": step.title},
        )
        db.commit()


company_tour_service = CompanyTourService()
