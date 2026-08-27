import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk


class Notification(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "notification"

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # e.g. "leave.submitted", "leave.approved", "timesheet.rejected", "asset.assigned"
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # what the notification is about, for the frontend to link to — not a
    # real FK (the target could be any module), just a loose reference
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
