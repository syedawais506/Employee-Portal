from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.project import Project
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.project_repository import ClientRepository, ProjectMemberRepository, ProjectRepository
from app.schemas.common import Page
from app.services.audit_service import audit_service

VALID_PROJECT_ROLES = {"manager", "member"}


class ProjectService:
    def __init__(self) -> None:
        self.repo = ProjectRepository()
        self.client_repo = ClientRepository()
        self.employee_repo = EmployeeRepository()
        self.member_repo = ProjectMemberRepository()

    def list_projects(
        self, db: Session, company_id: uuid.UUID, *, status: str | None, page: int, page_size: int
    ) -> Page[Project]:
        skip = (page - 1) * page_size
        items, total = self.repo.search(db, company_id, status=status, skip=skip, limit=page_size)
        return Page(items=items, total=total, page=page, page_size=page_size)

    def get_project(self, db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = self.repo.get(db, company_id, project_id)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    def _validate_members(self, db: Session, company_id: uuid.UUID, member_ids: list[dict]) -> None:
        for member in member_ids:
            if member["role_on_project"] not in VALID_PROJECT_ROLES:
                raise ValidationAppError(f"Invalid project role: {member['role_on_project']}")
            if self.employee_repo.get(db, company_id, member["employee_id"]) is None:
                raise ValidationAppError("A member does not belong to this company")

    def create_project(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str,
        client_id: uuid.UUID | None,
        budget: Decimal | None,
        is_billable: bool,
        start_date: date | None,
        end_date: date | None,
        member_ids: list[dict],
        actor_user_id: uuid.UUID,
    ) -> Project:
        if self.repo.get_by_name(db, company_id, name) is not None:
            raise ConflictError("A project with this name already exists")
        if client_id is not None and self.client_repo.get(db, company_id, client_id) is None:
            raise ValidationAppError("Client does not belong to this company")
        self._validate_members(db, company_id, member_ids)

        project = self.repo.create(
            db,
            company_id,
            name=name,
            client_id=client_id,
            budget=budget,
            is_billable=is_billable,
            start_date=start_date,
            end_date=end_date,
            status="active",
        )
        for member in member_ids:
            self.member_repo.add(db, project.id, member["employee_id"], member["role_on_project"])

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="project",
            entity_id=project.id,
            action="create",
            after={"name": name},
        )
        db.commit()
        return self.get_project(db, company_id, project.id)

    def update_project(
        self,
        db: Session,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        **updates,
    ) -> Project:
        project = self.get_project(db, company_id, project_id)
        client_id = updates.get("client_id")
        if client_id is not None and self.client_repo.get(db, company_id, client_id) is None:
            raise ValidationAppError("Client does not belong to this company")

        before = {"status": project.status, "name": project.name}
        for field, value in updates.items():
            if value is not None:
                setattr(project, field, value)
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="project",
            entity_id=project.id,
            action="update",
            before=before,
            after={"status": project.status, "name": project.name},
        )
        db.commit()
        return self.get_project(db, company_id, project_id)

    def delete_project(
        self, db: Session, company_id: uuid.UUID, project_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        project = self.get_project(db, company_id, project_id)
        before = {"name": project.name}
        self.repo.delete(db, company_id, project_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="project",
            entity_id=project_id,
            action="delete",
            before=before,
        )
        db.commit()

    def add_member(
        self,
        db: Session,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        employee_id: uuid.UUID,
        role_on_project: str,
        actor_user_id: uuid.UUID,
    ) -> Project:
        self.get_project(db, company_id, project_id)  # 404s if cross-tenant
        self._validate_members(db, company_id, [{"employee_id": employee_id, "role_on_project": role_on_project}])
        self.member_repo.add(db, project_id, employee_id, role_on_project)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="project_member",
            entity_id=project_id,
            action="update",
            after={"employee_id": str(employee_id), "role_on_project": role_on_project},
        )
        db.commit()
        return self.get_project(db, company_id, project_id)

    def remove_member(
        self,
        db: Session,
        company_id: uuid.UUID,
        project_id: uuid.UUID,
        employee_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> Project:
        self.get_project(db, company_id, project_id)  # 404s if cross-tenant
        self.member_repo.remove(db, project_id, employee_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="project_member",
            entity_id=project_id,
            action="delete",
            before={"employee_id": str(employee_id)},
        )
        db.commit()
        return self.get_project(db, company_id, project_id)

    def get_my_projects(self, db: Session, employee_id: uuid.UUID) -> list[dict]:
        memberships = self.member_repo.list_for_employee(db, employee_id)
        return [
            {
                "id": m.project.id,
                "name": m.project.name,
                "status": m.project.status,
                "role_on_project": m.role_on_project,
                "start_date": m.project.start_date,
                "end_date": m.project.end_date,
            }
            for m in memberships
        ]


project_service = ProjectService()
