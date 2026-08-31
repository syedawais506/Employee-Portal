import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.company_repository import CompanyRepository
from app.services.audit_service import audit_service
from app.services.webhook_service import webhook_service


class IntegrationService:
    def __init__(self) -> None:
        self.company_repo = CompanyRepository()

    def get_settings(self, db: Session, company_id: uuid.UUID) -> str | None:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company.slack_webhook_url

    def update_settings(
        self, db: Session, company_id: uuid.UUID, *, slack_webhook_url: str | None, actor_user_id: uuid.UUID
    ) -> str | None:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        before = company.slack_webhook_url
        company.slack_webhook_url = slack_webhook_url
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="integration_settings",
            entity_id=company_id,
            action="update",
            before={"slack_webhook_url": before},
            after={"slack_webhook_url": slack_webhook_url},
        )
        db.commit()
        return company.slack_webhook_url

    def send_test_message(self, db: Session, company_id: uuid.UUID) -> bool:
        return webhook_service.send_test_message(db, company_id)


integration_service = IntegrationService()
