from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.leave import HolidayCalendar, LeaveBalance, LeaveRequest, LeaveType
from app.repositories.base import TenantScopedRepository

OPEN_LEAVE_STATUSES = ("pending", "manager_approved", "approved")


class LeaveTypeRepository(TenantScopedRepository[LeaveType]):
    model = LeaveType

    def list_all(self, db: Session, company_id: uuid.UUID) -> list[LeaveType]:
        stmt = select(LeaveType).where(LeaveType.company_id == company_id).order_by(LeaveType.name)
        return list(db.execute(stmt).scalars().all())

    def get_by_name(self, db: Session, company_id: uuid.UUID, name: str) -> LeaveType | None:
        stmt = select(LeaveType).where(LeaveType.company_id == company_id, LeaveType.name == name)
        return db.execute(stmt).scalar_one_or_none()


class HolidayRepository(TenantScopedRepository[HolidayCalendar]):
    model = HolidayCalendar

    def list_all(self, db: Session, company_id: uuid.UUID, *, year: int | None = None) -> list[HolidayCalendar]:
        conditions = [HolidayCalendar.company_id == company_id]
        if year is not None:
            conditions.append(func.extract("year", HolidayCalendar.date) == year)
        stmt = select(HolidayCalendar).where(*conditions).order_by(HolidayCalendar.date)
        return list(db.execute(stmt).scalars().all())

    def get_by_date(self, db: Session, company_id: uuid.UUID, holiday_date: date) -> HolidayCalendar | None:
        stmt = select(HolidayCalendar).where(
            HolidayCalendar.company_id == company_id, HolidayCalendar.date == holiday_date
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_dates_in_range(
        self, db: Session, company_id: uuid.UUID, start: date, end: date
    ) -> set[date]:
        stmt = select(HolidayCalendar.date).where(
            HolidayCalendar.company_id == company_id,
            HolidayCalendar.date >= start,
            HolidayCalendar.date <= end,
        )
        return set(db.execute(stmt).scalars().all())


class LeaveBalanceRepository(TenantScopedRepository[LeaveBalance]):
    model = LeaveBalance

    def get_for(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, leave_type_id: uuid.UUID, year: int
    ) -> LeaveBalance | None:
        stmt = select(LeaveBalance).where(
            LeaveBalance.company_id == company_id,
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_employee(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, year: int
    ) -> list[LeaveBalance]:
        stmt = (
            select(LeaveBalance)
            .options(joinedload(LeaveBalance.leave_type))
            .where(
                LeaveBalance.company_id == company_id,
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year,
            )
        )
        return list(db.execute(stmt).unique().scalars().all())

    def list_for_company(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        year: int,
        employee_id: uuid.UUID | None = None,
    ) -> list[LeaveBalance]:
        conditions = [LeaveBalance.company_id == company_id, LeaveBalance.year == year]
        if employee_id is not None:
            conditions.append(LeaveBalance.employee_id == employee_id)
        stmt = (
            select(LeaveBalance)
            .options(joinedload(LeaveBalance.leave_type))
            .where(*conditions)
        )
        return list(db.execute(stmt).unique().scalars().all())


class LeaveRequestRepository(TenantScopedRepository[LeaveRequest]):
    model = LeaveRequest

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> LeaveRequest | None:
        stmt = (
            select(LeaveRequest)
            .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
            .where(LeaveRequest.id == id, LeaveRequest.company_id == company_id)
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def list_for_employee(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, status: str | None = None
    ) -> list[LeaveRequest]:
        conditions = [LeaveRequest.company_id == company_id, LeaveRequest.employee_id == employee_id]
        if status:
            conditions.append(LeaveRequest.status == status)
        stmt = (
            select(LeaveRequest)
            .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
            .where(*conditions)
            .order_by(LeaveRequest.start_date.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def search(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        employee_id: uuid.UUID | None,
        leave_type_id: uuid.UUID | None,
        status: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[LeaveRequest], int]:
        conditions = [LeaveRequest.company_id == company_id]
        if employee_id:
            conditions.append(LeaveRequest.employee_id == employee_id)
        if leave_type_id:
            conditions.append(LeaveRequest.leave_type_id == leave_type_id)
        if status:
            conditions.append(LeaveRequest.status == status)

        count_stmt = select(func.count()).select_from(LeaveRequest).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(LeaveRequest)
            .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
            .where(*conditions)
            .order_by(LeaveRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).unique().scalars().all())
        return items, total

    def list_overlapping(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        start_date: date,
        end_date: date,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> list[LeaveRequest]:
        conditions = [
            LeaveRequest.company_id == company_id,
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(OPEN_LEAVE_STATUSES),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        ]
        if exclude_id is not None:
            conditions.append(LeaveRequest.id != exclude_id)
        stmt = select(LeaveRequest).where(*conditions)
        return list(db.execute(stmt).scalars().all())

    def sum_days_for_year(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        year: int,
        *,
        statuses: tuple[str, ...] = OPEN_LEAVE_STATUSES,
    ) -> int:
        stmt = select(func.coalesce(func.sum(LeaveRequest.days_count), 0)).where(
            LeaveRequest.company_id == company_id,
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type_id,
            func.extract("year", LeaveRequest.start_date) == year,
            LeaveRequest.status.in_(statuses),
        )
        return db.execute(stmt).scalar_one()

    def count_pending(self, db: Session, company_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            LeaveRequest.company_id == company_id,
            LeaveRequest.status.in_(("pending", "manager_approved")),
        )
        return db.execute(stmt).scalar_one()

    def count_on_leave_on(self, db: Session, company_id: uuid.UUID, on_date: date) -> int:
        stmt = select(func.count()).where(
            LeaveRequest.company_id == company_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= on_date,
            LeaveRequest.end_date >= on_date,
        )
        return db.execute(stmt).scalar_one()

    def list_for_export(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
        leave_type_id: uuid.UUID | None,
        status: str | None,
    ) -> list[LeaveRequest]:
        conditions = [LeaveRequest.company_id == company_id]
        if date_from is not None:
            conditions.append(LeaveRequest.end_date >= date_from)
        if date_to is not None:
            conditions.append(LeaveRequest.start_date <= date_to)
        if employee_id is not None:
            conditions.append(LeaveRequest.employee_id == employee_id)
        if leave_type_id is not None:
            conditions.append(LeaveRequest.leave_type_id == leave_type_id)
        if status is not None:
            conditions.append(LeaveRequest.status == status)
        stmt = (
            select(LeaveRequest)
            .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
            .where(*conditions)
            .order_by(LeaveRequest.start_date)
        )
        return list(db.execute(stmt).unique().scalars().all())
