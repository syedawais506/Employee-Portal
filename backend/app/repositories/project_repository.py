from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.project import Client, Project, ProjectMember
from app.repositories.base import TenantScopedRepository


class ClientRepository(TenantScopedRepository[Client]):
    model = Client

    def list_all(self, db: Session, company_id: uuid.UUID) -> list[Client]:
        stmt = select(Client).where(Client.company_id == company_id).order_by(Client.name)
        return list(db.execute(stmt).scalars().all())


class ProjectRepository(TenantScopedRepository[Project]):
    model = Project

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> Project | None:
        stmt = (
            select(Project)
            .options(
                joinedload(Project.client),
                joinedload(Project.members).joinedload(ProjectMember.employee),
            )
            .where(Project.id == id, Project.company_id == company_id)
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_by_name(self, db: Session, company_id: uuid.UUID, name: str) -> Project | None:
        stmt = select(Project).where(Project.company_id == company_id, Project.name == name)
        return db.execute(stmt).scalar_one_or_none()

    def search(
        self, db: Session, company_id: uuid.UUID, *, status: str | None, skip: int, limit: int
    ) -> tuple[list[Project], int]:
        conditions = [Project.company_id == company_id]
        if status:
            conditions.append(Project.status == status)

        count_stmt = select(func.count()).select_from(Project).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(Project)
            .options(joinedload(Project.client), joinedload(Project.members))
            .where(*conditions)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).unique().scalars().all())
        return items, total


class ProjectMemberRepository:
    """A pure join table (like role_permission/user_role) — no company_id of
    its own; tenant isolation comes from always resolving the project via
    ProjectRepository (company-scoped) before touching membership rows.
    """

    def add(self, db: Session, project_id: uuid.UUID, employee_id: uuid.UUID, role_on_project: str) -> ProjectMember:
        existing = db.get(ProjectMember, (project_id, employee_id))
        if existing is not None:
            existing.role_on_project = role_on_project
            db.flush()
            return existing
        member = ProjectMember(project_id=project_id, employee_id=employee_id, role_on_project=role_on_project)
        db.add(member)
        db.flush()
        return member

    def remove(self, db: Session, project_id: uuid.UUID, employee_id: uuid.UUID) -> None:
        member = db.get(ProjectMember, (project_id, employee_id))
        if member is not None:
            db.delete(member)
            db.flush()

    def list_for_employee(self, db: Session, employee_id: uuid.UUID) -> list[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .options(joinedload(ProjectMember.project))
            .where(ProjectMember.employee_id == employee_id)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def is_member(self, db: Session, project_id: uuid.UUID, employee_id: uuid.UUID) -> bool:
        return db.get(ProjectMember, (project_id, employee_id)) is not None
