import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk


class SavedReport(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "saved_report"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_saved_report_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # employee | department | project | timesheet | leave | asset
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
