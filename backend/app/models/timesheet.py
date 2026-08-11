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
    from app.models.project import Project


class TimesheetPeriodConfig(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "timesheet_period_config"

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), default="weekly", nullable=False)
    week_start_day: Mapped[int] = mapped_column(default=0, nullable=False)  # 0=Monday .. 6=Sunday
    min_hours_per_day: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    max_hours_per_day: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), default=Decimal("24"), nullable=True)
    require_description: Mapped[bool] = mapped_column(default=False, nullable=False)
    warn_on_weekend: Mapped[bool] = mapped_column(default=True, nullable=False)
    require_finance_approval: Mapped[bool] = mapped_column(default=False, nullable=False)


class TimesheetSubmission(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "timesheet_submission"
    __table_args__ = (
        UniqueConstraint("employee_id", "period_start", "period_end", name="uq_timesheet_submission_employee_period"),
    )

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="submitted", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    manager_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    manager_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finance_approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    finance_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    employee: Mapped["Employee"] = relationship()
    entries: Mapped[list["TimesheetEntry"]] = relationship(back_populates="submission")

    @property
    def employee_name(self) -> str:
        return self.employee.full_name

    @property
    def total_hours(self) -> Decimal:
        return sum((e.hours for e in self.entries), Decimal("0"))


class TimesheetEntry(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "timesheet_entry"
    __table_args__ = (
        UniqueConstraint("employee_id", "entry_date", "project_id", name="uq_timesheet_entry_employee_date_project"),
    )

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("timesheet_submission.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    is_billable: Mapped[bool] = mapped_column(default=True, nullable=False)
    work_type: Mapped[str] = mapped_column(String(20), default="office", nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    employee: Mapped["Employee"] = relationship()
    project: Mapped["Project"] = relationship()
    submission: Mapped["TimesheetSubmission | None"] = relationship(back_populates="entries")

    @property
    def project_name(self) -> str:
        return self.project.name

    @property
    def status(self) -> str:
        return self.submission.status if self.submission is not None else "draft"

    @property
    def is_weekend(self) -> bool:
        return self.entry_date.weekday() >= 5
