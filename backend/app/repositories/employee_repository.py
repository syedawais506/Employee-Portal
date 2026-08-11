import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.repositories.base import TenantScopedRepository


class EmployeeRepository(TenantScopedRepository[Employee]):
    model = Employee

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> Employee | None:
        stmt = (
            select(Employee)
            .options(joinedload(Employee.department), joinedload(Employee.manager), joinedload(Employee.user))
            .where(Employee.id == id, Employee.company_id == company_id)
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_by_user_id(self, db: Session, user_id: uuid.UUID) -> Employee | None:
        stmt = select(Employee).options(joinedload(Employee.department), joinedload(Employee.manager)).where(
            Employee.user_id == user_id
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def search(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None,
        department_id: uuid.UUID | None,
        status: str | None,
        manager_id: uuid.UUID | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Employee], int]:
        conditions = [Employee.company_id == company_id, Employee.deleted_at.is_(None)]
        if search:
            like = f"%{search}%"
            conditions.append(
                or_(
                    Employee.first_name.ilike(like),
                    Employee.last_name.ilike(like),
                    Employee.employee_code.ilike(like),
                )
            )
        if department_id:
            conditions.append(Employee.department_id == department_id)
        if status:
            conditions.append(Employee.status == status)
        if manager_id:
            conditions.append(Employee.manager_id == manager_id)

        count_stmt = select(func.count()).select_from(Employee).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(Employee)
            .options(joinedload(Employee.department))
            .where(*conditions)
            .order_by(Employee.created_at.desc())
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
        search: str | None,
        department_id: uuid.UUID | None,
        status: str | None,
        manager_id: uuid.UUID | None,
        employment_type: str | None,
        location: str | None,
        joining_date_from: date | None,
        joining_date_to: date | None,
    ) -> list[Employee]:
        conditions = [Employee.company_id == company_id, Employee.deleted_at.is_(None)]
        if search:
            like = f"%{search}%"
            conditions.append(
                or_(
                    Employee.first_name.ilike(like),
                    Employee.last_name.ilike(like),
                    Employee.employee_code.ilike(like),
                )
            )
        if department_id:
            conditions.append(Employee.department_id == department_id)
        if status:
            conditions.append(Employee.status == status)
        if manager_id:
            conditions.append(Employee.manager_id == manager_id)
        if employment_type:
            conditions.append(Employee.employment_type == employment_type)
        if location:
            conditions.append(Employee.location == location)
        if joining_date_from:
            conditions.append(Employee.joining_date >= joining_date_from)
        if joining_date_to:
            conditions.append(Employee.joining_date <= joining_date_to)

        stmt = (
            select(Employee)
            .options(joinedload(Employee.department), joinedload(Employee.manager), joinedload(Employee.user))
            .where(*conditions)
            .order_by(Employee.employee_code)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def next_employee_code(self, db: Session, company_id: uuid.UUID, prefix: str) -> str:
        count_stmt = select(func.count()).select_from(Employee).where(Employee.company_id == company_id)
        count = db.execute(count_stmt).scalar_one()
        return f"{prefix}-{count + 1:04d}"
