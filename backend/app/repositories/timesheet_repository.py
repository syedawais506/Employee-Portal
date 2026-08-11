from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, case, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.models.project import Project
from app.models.timesheet import TimesheetEntry, TimesheetPeriodConfig, TimesheetSubmission
from app.repositories.base import TenantScopedRepository


class TimesheetPeriodConfigRepository(TenantScopedRepository[TimesheetPeriodConfig]):
    model = TimesheetPeriodConfig

    def get_for_company(self, db: Session, company_id: uuid.UUID) -> TimesheetPeriodConfig | None:
        stmt = select(TimesheetPeriodConfig).where(TimesheetPeriodConfig.company_id == company_id)
        return db.execute(stmt).scalar_one_or_none()


class TimesheetEntryRepository(TenantScopedRepository[TimesheetEntry]):
    model = TimesheetEntry

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> TimesheetEntry | None:
        stmt = (
            select(TimesheetEntry)
            .options(joinedload(TimesheetEntry.project), joinedload(TimesheetEntry.submission))
            .where(TimesheetEntry.id == id, TimesheetEntry.company_id == company_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_natural_key(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, entry_date: date, project_id: uuid.UUID
    ) -> TimesheetEntry | None:
        stmt = select(TimesheetEntry).where(
            TimesheetEntry.company_id == company_id,
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.entry_date == entry_date,
            TimesheetEntry.project_id == project_id,
        )
        return db.execute(stmt).scalar_one_or_none()

    def sum_hours_for_day(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        entry_date: date,
        *,
        exclude_entry_id: uuid.UUID | None = None,
    ) -> Decimal:
        conditions = [
            TimesheetEntry.company_id == company_id,
            TimesheetEntry.employee_id == employee_id,
            TimesheetEntry.entry_date == entry_date,
        ]
        if exclude_entry_id is not None:
            conditions.append(TimesheetEntry.id != exclude_entry_id)
        stmt = select(func.coalesce(func.sum(TimesheetEntry.hours), 0)).where(*conditions)
        return db.execute(stmt).scalar_one()

    def list_for_employee_range(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> list[TimesheetEntry]:
        stmt = (
            select(TimesheetEntry)
            .options(joinedload(TimesheetEntry.project), joinedload(TimesheetEntry.submission))
            .where(
                TimesheetEntry.company_id == company_id,
                TimesheetEntry.employee_id == employee_id,
                TimesheetEntry.entry_date >= date_from,
                TimesheetEntry.entry_date <= date_to,
            )
            .order_by(TimesheetEntry.entry_date)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def list_unsubmitted_in_range(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> list[TimesheetEntry]:
        # Eligible for a (re)submission if never submitted, or if the submission
        # it's currently attached to was rejected — regardless of that rejected
        # submission's own date range, so a free-form resubmit range always
        # picks up rejected entries alongside fresh drafts in the same window.
        stmt = (
            select(TimesheetEntry)
            .outerjoin(TimesheetSubmission, TimesheetSubmission.id == TimesheetEntry.submission_id)
            .where(
                TimesheetEntry.company_id == company_id,
                TimesheetEntry.employee_id == employee_id,
                TimesheetEntry.entry_date >= date_from,
                TimesheetEntry.entry_date <= date_to,
                or_(TimesheetEntry.submission_id.is_(None), TimesheetSubmission.status == "rejected"),
            )
        )
        return list(db.execute(stmt).scalars().all())

    def search(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
        location: str | None = None,
    ) -> list[TimesheetEntry]:
        conditions = [TimesheetEntry.company_id == company_id]
        if date_from is not None:
            conditions.append(TimesheetEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(TimesheetEntry.entry_date <= date_to)
        if employee_id is not None:
            conditions.append(TimesheetEntry.employee_id == employee_id)
        if project_id is not None:
            conditions.append(TimesheetEntry.project_id == project_id)
        if location is not None:
            conditions.append(Employee.location == location)

        stmt = (
            select(TimesheetEntry)
            .join(Employee, Employee.id == TimesheetEntry.employee_id)
            .options(
                joinedload(TimesheetEntry.project),
                joinedload(TimesheetEntry.employee),
                joinedload(TimesheetEntry.submission),
            )
            .where(*conditions)
            .order_by(TimesheetEntry.entry_date)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def hours_by_project(
        self, db: Session, company_id: uuid.UUID, *, date_from: date | None, date_to: date | None
    ) -> list[tuple[uuid.UUID, str, Decimal]]:
        conditions = [TimesheetEntry.company_id == company_id]
        if date_from is not None:
            conditions.append(TimesheetEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(TimesheetEntry.entry_date <= date_to)
        stmt = (
            select(Project.id, Project.name, func.sum(TimesheetEntry.hours))
            .join(Project, Project.id == TimesheetEntry.project_id)
            .where(*conditions)
            .group_by(Project.id, Project.name)
            .order_by(func.sum(TimesheetEntry.hours).desc())
        )
        return [(row[0], row[1], row[2]) for row in db.execute(stmt).all()]

    def hours_by_employee(
        self, db: Session, company_id: uuid.UUID, *, date_from: date | None, date_to: date | None
    ) -> list[tuple[uuid.UUID, str, str, Decimal]]:
        conditions = [TimesheetEntry.company_id == company_id]
        if date_from is not None:
            conditions.append(TimesheetEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(TimesheetEntry.entry_date <= date_to)
        stmt = (
            select(Employee.id, Employee.first_name, Employee.last_name, func.sum(TimesheetEntry.hours))
            .join(Employee, Employee.id == TimesheetEntry.employee_id)
            .where(*conditions)
            .group_by(Employee.id, Employee.first_name, Employee.last_name)
            .order_by(func.sum(TimesheetEntry.hours).desc())
        )
        return [(row[0], row[1], row[2], row[3]) for row in db.execute(stmt).all()]

    def billable_totals(
        self, db: Session, company_id: uuid.UUID, *, date_from: date | None, date_to: date | None
    ) -> tuple[Decimal, Decimal]:
        conditions = [TimesheetEntry.company_id == company_id]
        if date_from is not None:
            conditions.append(TimesheetEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(TimesheetEntry.entry_date <= date_to)
        billable_sum = func.coalesce(
            func.sum(case((TimesheetEntry.is_billable.is_(True), TimesheetEntry.hours), else_=0)), 0
        )
        total_sum = func.coalesce(func.sum(TimesheetEntry.hours), 0)
        stmt = select(billable_sum, total_sum).where(*conditions)
        result = db.execute(stmt).one()
        return Decimal(result[0]), Decimal(result[1])


class TimesheetSubmissionRepository(TenantScopedRepository[TimesheetSubmission]):
    model = TimesheetSubmission

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> TimesheetSubmission | None:
        stmt = (
            select(TimesheetSubmission)
            .options(
                joinedload(TimesheetSubmission.employee),
                joinedload(TimesheetSubmission.entries).joinedload(TimesheetEntry.project),
            )
            .where(TimesheetSubmission.id == id, TimesheetSubmission.company_id == company_id)
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_by_employee_period(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, period_start: date, period_end: date
    ) -> TimesheetSubmission | None:
        stmt = select(TimesheetSubmission).where(
            TimesheetSubmission.company_id == company_id,
            TimesheetSubmission.employee_id == employee_id,
            TimesheetSubmission.period_start == period_start,
            TimesheetSubmission.period_end == period_end,
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_employee(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, statuses: list[str] | None = None
    ) -> list[TimesheetSubmission]:
        conditions = [TimesheetSubmission.company_id == company_id, TimesheetSubmission.employee_id == employee_id]
        if statuses:
            conditions.append(TimesheetSubmission.status.in_(statuses))
        stmt = (
            select(TimesheetSubmission)
            .options(joinedload(TimesheetSubmission.entries))
            .where(*conditions)
            .order_by(TimesheetSubmission.period_start.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def search(
        self, db: Session, company_id: uuid.UUID, *, statuses: list[str] | None, skip: int, limit: int
    ) -> tuple[list[TimesheetSubmission], int]:
        conditions = [TimesheetSubmission.company_id == company_id]
        if statuses:
            conditions.append(TimesheetSubmission.status.in_(statuses))

        count_stmt = select(func.count()).select_from(TimesheetSubmission).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(TimesheetSubmission)
            .options(joinedload(TimesheetSubmission.employee), joinedload(TimesheetSubmission.entries))
            .where(*conditions)
            .order_by(TimesheetSubmission.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).unique().scalars().all())
        return items, total

    def counts_by_status(self, db: Session, company_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(TimesheetSubmission.status, func.count())
            .where(TimesheetSubmission.company_id == company_id)
            .group_by(TimesheetSubmission.status)
        )
        return {row[0]: row[1] for row in db.execute(stmt).all()}

    def late_count(self, db: Session, company_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            TimesheetSubmission.company_id == company_id,
            cast(TimesheetSubmission.submitted_at, Date) > TimesheetSubmission.period_end,
        )
        return db.execute(stmt).scalar_one()
