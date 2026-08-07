import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def record(
        self,
        db: Session,
        *,
        company_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        entity_type: str,
        entity_id: uuid.UUID | None,
        action: str,
        before: dict | None = None,
        after: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        db.add(
            AuditLog(
                company_id=company_id,
                actor_user_id=actor_user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                before=before,
                after=after,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        db.flush()


audit_service = AuditService()
