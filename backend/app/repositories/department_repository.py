import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.department import Department
from app.repositories.base import TenantScopedRepository


class DepartmentRepository(TenantScopedRepository[Department]):
    model = Department

    def list_for_export(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None,
        parent_department_id: uuid.UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> list[Department]:
        conditions = [Department.company_id == company_id]
        if search:
            conditions.append(Department.name.ilike(f"%{search}%"))
        if parent_department_id:
            conditions.append(Department.parent_department_id == parent_department_id)
        if created_from:
            conditions.append(Department.created_at >= created_from)
        if created_to:
            conditions.append(Department.created_at <= created_to)

        stmt = (
            select(Department)
            .options(joinedload(Department.parent))
            .where(*conditions)
            .order_by(Department.name)
        )
        return list(db.execute(stmt).unique().scalars().all())
