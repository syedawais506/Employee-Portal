from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.company import Company
from app.tasks.webhook_tasks import deliver_webhook


class WebhookService:
    def dispatch(self, db: Session, company_id: uuid.UUID, text: str) -> None:
        company = db.get(Company, company_id)
        if company is not None and company.slack_webhook_url:
            deliver_webhook.delay(company.slack_webhook_url, text)

    def send_test_message(self, db: Session, company_id: uuid.UUID) -> bool:
        company = db.get(Company, company_id)
        if company is None or not company.slack_webhook_url:
            return False
        deliver_webhook.delay(
            company.slack_webhook_url,
            "Test message from Employee Portal — your webhook is configured correctly.",
        )
        return True


webhook_service = WebhookService()
