import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import new_uuid


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantMixin:
    """Adds a NOT NULL company_id FK. Every tenant-scoped model uses this."""

    @property
    def company_id_column(self):  # pragma: no cover - documentation helper
        return "company_id"


def company_fk(nullable: bool = False):
    return mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=nullable, index=True
    )
