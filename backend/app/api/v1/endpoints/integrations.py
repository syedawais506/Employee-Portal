import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.user import User
from app.schemas.company import (
    IntegrationSettingsResponse,
    IntegrationSettingsUpdateRequest,
    WebhookTestResponse,
)
from app.services.integration_service import integration_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/slack", response_model=IntegrationSettingsResponse)
def get_slack_integration(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("company", "configure")),
):
    return IntegrationSettingsResponse(slack_webhook_url=integration_service.get_settings(db, company_id))


@router.patch("/slack", response_model=IntegrationSettingsResponse)
def update_slack_integration(
    payload: IntegrationSettingsUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("company", "configure")),
    db: Session = Depends(get_db),
):
    value = integration_service.update_settings(
        db, company_id, slack_webhook_url=payload.slack_webhook_url, actor_user_id=current_user.id
    )
    return IntegrationSettingsResponse(slack_webhook_url=value)


@router.post("/slack/test", response_model=WebhookTestResponse)
def test_slack_integration(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("company", "configure")),
):
    return WebhookTestResponse(sent=integration_service.send_test_message(db, company_id))
