import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.repositories.base import TenantScopedRepository


class NotificationRepository(TenantScopedRepository[Notification]):
    model = Notification

    def list_for_user(
        self,
        db: Session,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 25,
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.company_id == company_id, Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))

        count_stmt = select(func.count()).select_from(Notification).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
        return items, total

    def count_unread(self, db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Notification.company_id == company_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        return db.execute(stmt).scalar_one()

    def mark_read(
        self, db: Session, company_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Notification | None:
        notification = db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.company_id == company_id,
                Notification.user_id == user_id,
            )
        ).scalar_one_or_none()
        if notification is None:
            return None
        notification.is_read = True
        db.flush()
        return notification

    def mark_all_read(self, db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.company_id == company_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        result = db.execute(stmt)
        db.flush()
        return result.rowcount
