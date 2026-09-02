from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.attendance import AttendanceRecord, AttendanceShiftConfig
from app.repositories.attendance_repository import AttendanceRecordRepository, AttendanceShiftConfigRepository
from app.schemas.attendance import TodayAttendanceEntry
from app.schemas.common import Page
from app.services.audit_service import audit_service
from app.utils.csv_export import build_csv


def _time_plus_minutes(value: time, minutes: int) -> time:
    return (datetime.combine(date.min, value) + timedelta(minutes=minutes)).time()


def _hours_between(start: time, end: time) -> Decimal:
    delta = datetime.combine(date.min, end) - datetime.combine(date.min, start)
    return Decimal(delta.total_seconds() / 3600)


class AttendanceService:
    def __init__(self) -> None:
        self.shift_config_repo = AttendanceShiftConfigRepository()
        self.record_repo = AttendanceRecordRepository()

    # -- Shift settings ------------------------------------------------------

    def get_shift_config(self, db: Session, company_id: uuid.UUID) -> AttendanceShiftConfig:
        config = self.shift_config_repo.get_for_company(db, company_id)
        if config is None:
            config = self.shift_config_repo.create(db, company_id)
            db.commit()
        return config

    def update_shift_config(
        self, db: Session, company_id: uuid.UUID, *, actor_user_id: uuid.UUID, **updates
    ) -> AttendanceShiftConfig:
        config = self.get_shift_config(db, company_id)
        before = {
            "shift_start": config.shift_start.isoformat(),
            "shift_end": config.shift_end.isoformat(),
            "grace_period_minutes": config.grace_period_minutes,
        }
        for field, value in updates.items():
            if value is not None:
                setattr(config, field, value)
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="attendance_shift_config",
            entity_id=config.id,
            action="update",
            before=before,
            after={
                "shift_start": config.shift_start.isoformat(),
                "shift_end": config.shift_end.isoformat(),
                "grace_period_minutes": config.grace_period_minutes,
            },
        )
        db.commit()
        return config

    # -- Self-service check-in/check-out -------------------------------------
    # NOTE: check_in_at/check_out_at are stored as UTC-aware timestamps, but
    # shift_start/shift_end are plain wall-clock times entered by the Admin
    # with no company-timezone field anywhere in this app to convert against
    # (the same gap Timesheets/Leave already have — no module does per-company
    # timezone conversion). Late/overtime here are computed by comparing raw
    # UTC wall-clock time against that plain shift time, so this is only
    # accurate for companies operating in UTC until a real timezone field is
    # added company-wide.

    def check_in(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, now: datetime | None = None
    ) -> AttendanceRecord:
        now = now or datetime.now(timezone.utc)
        today = now.date()
        existing = self.record_repo.get_by_employee_date(db, company_id, employee_id, today)
        if existing is not None:
            raise ConflictError("Already checked in today")

        shift_config = self.get_shift_config(db, company_id)
        grace_cutoff = _time_plus_minutes(shift_config.shift_start, shift_config.grace_period_minutes)
        is_late = now.time() > grace_cutoff

        record = self.record_repo.create(
            db,
            company_id,
            employee_id=employee_id,
            attendance_date=today,
            check_in_at=now,
            is_late=is_late,
        )
        db.commit()
        return record

    def check_out(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, now: datetime | None = None
    ) -> AttendanceRecord:
        now = now or datetime.now(timezone.utc)
        today = now.date()
        record = self.record_repo.get_by_employee_date(db, company_id, employee_id, today)
        if record is None:
            raise ConflictError("You haven't checked in today")
        if record.check_out_at is not None:
            raise ConflictError("Already checked out today")

        shift_config = self.get_shift_config(db, company_id)
        assert record.check_in_at is not None  # guaranteed by check_in always setting it
        worked_hours = Decimal((now - record.check_in_at).total_seconds() / 3600)
        shift_hours = _hours_between(shift_config.shift_start, shift_config.shift_end)
        overtime = worked_hours - shift_hours
        record.check_out_at = now
        record.overtime_hours = overtime.quantize(Decimal("0.01")) if overtime > 0 else Decimal("0")
        db.commit()
        return record

    def list_my_records(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[AttendanceRecord]:
        return self.record_repo.list_for_employee_range(db, company_id, employee_id, date_from, date_to)

    # -- Company-wide view ----------------------------------------------------

    def list_records(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> Page[AttendanceRecord]:
        skip = (page - 1) * page_size
        items, total = self.record_repo.search(
            db, company_id, date_from=date_from, date_to=date_to, employee_id=employee_id, skip=skip, limit=page_size
        )
        return Page(items=items, total=total, page=page, page_size=page_size)

    def today_dashboard(self, db: Session, company_id: uuid.UUID) -> list[TodayAttendanceEntry]:
        rows = self.record_repo.today_status(db, company_id, date.today())
        entries = []
        for employee, record in rows:
            if record is None:
                status = "not_checked_in"
            else:
                status = record.status
            entries.append(
                TodayAttendanceEntry(
                    employee_id=employee.id,
                    employee_name=employee.full_name,
                    check_in_at=record.check_in_at if record else None,
                    check_out_at=record.check_out_at if record else None,
                    is_late=record.is_late if record else False,
                    status=status,
                )
            )
        return entries

    # -- Report/export ---------------------------------------------------------

    def report_rows(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        employee_id: uuid.UUID | None = None,
    ) -> tuple[list[str], list[list]]:
        records = self.record_repo.list_for_export(
            db, company_id, date_from=date_from, date_to=date_to, employee_id=employee_id
        )
        header = ["Employee", "Date", "Check In", "Check Out", "Late", "Overtime Hours", "Status"]
        rows = [
            [
                r.employee.full_name,
                r.attendance_date.isoformat(),
                r.check_in_at.isoformat() if r.check_in_at else "",
                r.check_out_at.isoformat() if r.check_out_at else "",
                "Yes" if r.is_late else "No",
                str(r.overtime_hours),
                r.status,
            ]
            for r in records
        ]
        return header, rows

    def export_csv(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
    ) -> str:
        header, rows = self.report_rows(db, company_id, date_from=date_from, date_to=date_to, employee_id=employee_id)
        return build_csv(header, rows)


attendance_service = AttendanceService()
