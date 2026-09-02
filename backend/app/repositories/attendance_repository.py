from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.attendance import AttendanceRecord, AttendanceShiftConfig
from app.models.employee import Employee
from app.repositories.base import TenantScopedRepository


class AttendanceShiftConfigRepository(TenantScopedRepository[AttendanceShiftConfig]):
    model = AttendanceShiftConfig

    def get_for_company(self, db: Session, company_id: uuid.UUID) -> AttendanceShiftConfig | None:
        stmt = select(AttendanceShiftConfig).where(AttendanceShiftConfig.company_id == company_id)
        return db.execute(stmt).scalar_one_or_none()


class AttendanceRecordRepository(TenantScopedRepository[AttendanceRecord]):
    model = AttendanceRecord

    def get_by_employee_date(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, attendance_date: date
    ) -> AttendanceRecord | None:
        stmt = select(AttendanceRecord).where(
            AttendanceRecord.company_id == company_id,
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.attendance_date == attendance_date,
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_employee_range(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[AttendanceRecord]:
        stmt = (
            select(AttendanceRecord)
            .options(joinedload(AttendanceRecord.employee))
            .where(
                AttendanceRecord.company_id == company_id,
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.attendance_date >= date_from,
                AttendanceRecord.attendance_date <= date_to,
            )
            .order_by(AttendanceRecord.attendance_date.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def search(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
        skip: int,
        limit: int,
    ) -> tuple[list[AttendanceRecord], int]:
        conditions = [AttendanceRecord.company_id == company_id]
        if date_from is not None:
            conditions.append(AttendanceRecord.attendance_date >= date_from)
        if date_to is not None:
            conditions.append(AttendanceRecord.attendance_date <= date_to)
        if employee_id is not None:
            conditions.append(AttendanceRecord.employee_id == employee_id)

        count_stmt = select(func.count()).select_from(AttendanceRecord).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(AttendanceRecord)
            .options(joinedload(AttendanceRecord.employee))
            .where(*conditions)
            .order_by(AttendanceRecord.attendance_date.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).unique().scalars().all())
        return items, total

    def list_for_export(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
    ) -> list[AttendanceRecord]:
        conditions = [AttendanceRecord.company_id == company_id]
        if date_from is not None:
            conditions.append(AttendanceRecord.attendance_date >= date_from)
        if date_to is not None:
            conditions.append(AttendanceRecord.attendance_date <= date_to)
        if employee_id is not None:
            conditions.append(AttendanceRecord.employee_id == employee_id)

        stmt = (
            select(AttendanceRecord)
            .options(joinedload(AttendanceRecord.employee))
            .where(*conditions)
            .order_by(AttendanceRecord.attendance_date.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def today_status(
        self, db: Session, company_id: uuid.UUID, today: date
    ) -> list[tuple[Employee, AttendanceRecord | None]]:
        stmt = (
            select(Employee, AttendanceRecord)
            .outerjoin(
                AttendanceRecord,
                and_(
                    AttendanceRecord.employee_id == Employee.id,
                    AttendanceRecord.attendance_date == today,
                ),
            )
            .where(
                Employee.company_id == company_id,
                Employee.status == "active",
                Employee.deleted_at.is_(None),
            )
            .order_by(Employee.first_name, Employee.last_name)
        )
        return [(row[0], row[1]) for row in db.execute(stmt).all()]
