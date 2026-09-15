import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk

if TYPE_CHECKING:
    from app.models.employee import Employee


class LeaveType(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "leave_type"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_leave_type_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_paid: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Null = unlimited/untracked (e.g. unpaid leave) — no balance enforcement for this type.
    annual_quota_days: Mapped[int | None] = mapped_column(nullable=True)
    max_carry_forward_days: Mapped[int] = mapped_column(default=0, nullable=False)
    requires_attachment: Mapped[bool] = mapped_column(default=False, nullable=False)


class HolidayCalendar(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "holiday_calendar"
    __table_args__ = (
        UniqueConstraint("company_id", "date", "location", name="uq_holiday_company_date_location"),
    )

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # Null = applies to every employee regardless of location (a company-wide
    # holiday); set = only excluded from business-day math and shown on the
    # calendar for employees whose employee.location matches exactly.
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)


class LeaveBalance(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "leave_balance"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance_employee_type_year"),
    )

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_type.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(nullable=False)
    granted: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0"), nullable=False)
    carried_forward: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0"), nullable=False)
    adjustment: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0"), nullable=False)

    leave_type: Mapped["LeaveType"] = relationship()


class LeaveRequest(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "leave_request"

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_type.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_count: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_file_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attachment_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    manager_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    manager_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hr_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    hr_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship()
    leave_type: Mapped["LeaveType"] = relationship()

    @property
    def employee_name(self) -> str:
        return self.employee.full_name

    @property
    def leave_type_name(self) -> str:
        return self.leave_type.name
