from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.department import Department
from app.repositories.department_repository import DepartmentRepository
from app.schemas.common import Page
from app.services.audit_service import audit_service
from app.utils.csv_export import build_csv


class DepartmentService:
    def __init__(self) -> None:
        self.repo = DepartmentRepository()

    def list_departments(self, db: Session, company_id: uuid.UUID, *, page: int, page_size: int) -> Page[Department]:
        skip = (page - 1) * page_size
        items, total = self.repo.list(db, company_id, skip=skip, limit=page_size)
        return Page(items=items, total=total, page=page, page_size=page_size)

    def get_department(self, db: Session, company_id: uuid.UUID, department_id: uuid.UUID) -> Department:
        department = self.repo.get(db, company_id, department_id)
        if department is None:
            raise NotFoundError("Department not found")
        return department

    def create_department(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str,
        parent_department_id: uuid.UUID | None,
        cost_center_code: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> Department:
        if parent_department_id is not None:
            self.get_department(db, company_id, parent_department_id)  # raises if cross-tenant/missing
        department = self.repo.create(
            db,
            company_id,
            name=name,
            parent_department_id=parent_department_id,
            cost_center_code=cost_center_code,
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="department",
            entity_id=department.id,
            action="create",
            after={"name": name},
        )
        db.commit()
        return department

    def update_department(
        self,
        db: Session,
        company_id: uuid.UUID,
        department_id: uuid.UUID,
        *,
        name: str | None,
        parent_department_id: uuid.UUID | None,
        cost_center_code: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> Department:
        department = self.get_department(db, company_id, department_id)
        if parent_department_id is not None:
            if parent_department_id == department_id:
                raise ValidationAppError("A department cannot be its own parent")
            self.get_department(db, company_id, parent_department_id)
        before = {
            "name": department.name,
            "parent_department_id": str(department.parent_department_id) if department.parent_department_id else None,
        }
        if name is not None:
            department.name = name
        if parent_department_id is not None:
            department.parent_department_id = parent_department_id
        if cost_center_code is not None:
            department.cost_center_code = cost_center_code
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="department",
            entity_id=department.id,
            action="update",
            before=before,
            after={"name": department.name},
        )
        db.commit()
        return department

    def delete_department(
        self, db: Session, company_id: uuid.UUID, department_id: uuid.UUID, *, actor_user_id: uuid.UUID | None
    ) -> None:
        department = self.get_department(db, company_id, department_id)
        self.repo.delete(db, company_id, department_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="department",
            entity_id=department_id,
            action="delete",
            before={"name": department.name},
        )
        db.commit()

    def report_rows(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None = None,
        parent_department_id: uuid.UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[str], list[list]]:
        departments = self.repo.list_for_export(
            db,
            company_id,
            search=search,
            parent_department_id=parent_department_id,
            created_from=created_from,
            created_to=created_to,
        )
        header = ["Name", "Parent Department", "Cost Center Code", "Created At"]
        rows = [
            [
                dept.name,
                dept.parent.name if dept.parent else "",
                dept.cost_center_code or "",
                dept.created_at.isoformat(),
            ]
            for dept in departments
        ]
        return header, rows

    def export_csv(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None,
        parent_department_id: uuid.UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> str:
        header, rows = self.report_rows(
            db,
            company_id,
            search=search,
            parent_department_id=parent_department_id,
            created_from=created_from,
            created_to=created_to,
        )
        return build_csv(header, rows)


department_service = DepartmentService()
