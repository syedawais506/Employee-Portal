import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk

if TYPE_CHECKING:
    from app.models.employee import Employee


class AttendanceShiftConfig(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "attendance_shift_config"

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    shift_start: Mapped[time] = mapped_column(Time, default=time(9, 0), nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, default=time(18, 0), nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(default=15, nullable=False)


class AttendanceRecord(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "attendance_record"
    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_record_employee_date"),
    )

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_late: Mapped[bool] = mapped_column(default=False, nullable=False)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0"), nullable=False)

    employee: Mapped["Employee"] = relationship()

    @property
    def employee_name(self) -> str:
        return self.employee.full_name

    @property
    def status(self) -> str:
        return "checked_out" if self.check_out_at is not None else "checked_in"
