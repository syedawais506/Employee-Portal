import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk


class DocumentType(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "document_type"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_document_type_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk()
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EmployeeDocument(UUIDPkMixin, Base):
    __tablename__ = "employee_document"
    __table_args__ = (
        UniqueConstraint("employee_id", "document_type_id", name="uq_employee_document_type"),
    )

    company_id: Mapped[uuid.UUID] = company_fk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_type.id", ondelete="CASCADE"), nullable=False
    )
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    review_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    document_type: Mapped["DocumentType"] = relationship()


class CompanyTourStep(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "company_tour_step"

    company_id: Mapped[uuid.UUID] = company_fk()
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OnboardingInvite(UUIDPkMixin, Base):
    __tablename__ = "onboarding_invite"

    company_id: Mapped[uuid.UUID] = company_fk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
