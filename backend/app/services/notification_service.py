from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.notification import NotificationResponse
from app.services.notification_ws import connection_manager
from app.services.webhook_service import webhook_service


class NotificationService:
    def __init__(self) -> None:
        self.repo = NotificationRepository()
        self.user_repo = UserRepository()

    def notify(
        self,
        db: Session,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        type: str,
        title: str,
        body: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Notification:
        notification = self._create_and_push(
            db, company_id, user_id,
            type=type, title=title, body=body, entity_type=entity_type, entity_id=entity_id,
        )
        webhook_service.dispatch(db, company_id, f"{title}\n{body}" if body else title)
        return notification

    def notify_users_with_permission(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        module: str,
        action: str,
        type: str,
        title: str,
        body: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> list[Notification]:
        users = self.user_repo.list_by_permission(db, company_id, module, action)
        notifications = [
            self._create_and_push(
                db, company_id, user.id,
                type=type, title=title, body=body, entity_type=entity_type, entity_id=entity_id,
            )
            for user in users
        ]
        # One webhook message per event, not one per fanned-out recipient.
        if notifications:
            webhook_service.dispatch(db, company_id, f"{title}\n{body}" if body else title)
        return notifications

    def _create_and_push(
        self,
        db: Session,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        type: str,
        title: str,
        body: str | None,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
    ) -> Notification:
        notification = self.repo.create(
            db,
            company_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.flush()
        payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
        connection_manager.push(user_id, {"type": "notification", "data": payload})
        return notification

    def list_my_notifications(
        self,
        db: Session,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool,
        page: int,
        page_size: int,
    ) -> Page[Notification]:
        skip = (page - 1) * page_size
        items, total = self.repo.list_for_user(
            db, company_id, user_id, unread_only=unread_only, skip=skip, limit=page_size
        )
        return Page(items=items, total=total, page=page, page_size=page_size)

    def get_unread_count(self, db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return self.repo.count_unread(db, company_id, user_id)

    def mark_read(
        self, db: Session, company_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Notification | None:
        notification = self.repo.mark_read(db, company_id, user_id, notification_id)
        if notification is not None:
            db.commit()
        return notification

    def mark_all_read(self, db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
        count = self.repo.mark_all_read(db, company_id, user_id)
        db.commit()
        return count


notification_service = NotificationService()
