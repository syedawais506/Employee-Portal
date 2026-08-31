import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.role import Role
from app.repositories.role_repository import RoleRepository
from app.services import permission_cache

# (module, action) catalog — the single source of truth for what can be granted.
# Modules beyond employee/department/role are reserved for future phases per docs/ROADMAP.md
# but declared now so the permission-matrix UI and seed data don't need later migrations.
PERMISSION_CATALOG: dict[str, list[str]] = {
    "employee": ["view", "create", "update", "delete", "export", "import"],
    "department": ["view", "create", "update", "delete", "export"],
    "role": ["view", "create", "update", "delete"],
    "company": ["view", "create", "update", "delete", "configure"],
    "onboarding": ["view", "review", "approve", "configure"],
    "project": ["view", "create", "update", "delete", "export"],
    "timesheet": ["view", "create", "update", "delete", "approve", "reject", "export", "configure"],
    "leave": ["view", "create", "update", "delete", "approve", "reject", "export", "configure"],
    "asset": ["view", "create", "update", "delete", "export"],
    "report": ["view", "export", "configure"],
}

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Admin": [
        "employee.view", "employee.create", "employee.update", "employee.delete",
        "employee.export", "employee.import",
        "department.view", "department.create", "department.update", "department.delete", "department.export",
        "role.view", "role.create", "role.update", "role.delete",
        "company.view", "company.configure",
        "onboarding.view", "onboarding.review", "onboarding.approve", "onboarding.configure",
        "project.view", "project.create", "project.update", "project.delete", "project.export",
        "timesheet.view", "timesheet.create", "timesheet.update", "timesheet.delete",
        "timesheet.approve", "timesheet.reject", "timesheet.export", "timesheet.configure",
        "leave.view", "leave.create", "leave.update", "leave.delete",
        "leave.approve", "leave.reject", "leave.export", "leave.configure",
        "asset.view", "asset.create", "asset.update", "asset.delete", "asset.export",
        "report.view", "report.export", "report.configure",
    ],
    "HR": [
        "employee.view", "employee.create", "employee.update", "employee.export",
        "department.view",
        "onboarding.view", "onboarding.review",
        "timesheet.view", "timesheet.create", "timesheet.update",
        "leave.view", "leave.create", "leave.update", "leave.approve", "leave.reject", "leave.export",
        "asset.view", "asset.create", "asset.update", "asset.export",
        "report.view",
    ],
    "Manager": [
        "employee.view",
        "department.view",
        "project.view", "project.update",
        "timesheet.view", "timesheet.create", "timesheet.update", "timesheet.approve", "timesheet.reject",
        "leave.view", "leave.create", "leave.update", "leave.approve", "leave.reject",
        "asset.view",
        "report.view",
    ],
    "Employee": [
        "employee.view",
        "department.view",
        "timesheet.view", "timesheet.create", "timesheet.update",
        "leave.view", "leave.create", "leave.update",
    ],
    "Finance": [
        "employee.view",
        "project.view",
        "timesheet.view", "timesheet.create", "timesheet.update",
        "timesheet.approve", "timesheet.reject", "timesheet.export",
        "report.view", "report.export",
    ],
}

SYSTEM_ROLES = {"Admin"}


class RoleService:
    def __init__(self) -> None:
        self.role_repo = RoleRepository()

    def get_permission_catalog(self) -> list[dict]:
        return [{"module": module, "actions": actions} for module, actions in PERMISSION_CATALOG.items()]

    def create_default_role(self, db: Session, company_id: uuid.UUID, role_name: str) -> Role:
        role = self.role_repo.create(db, company_id, role_name, is_system=role_name in SYSTEM_ROLES)
        permission_ids = []
        for code in DEFAULT_ROLE_PERMISSIONS[role_name]:
            module, action = code.split(".")
            permission = self.role_repo.get_permission_by_module_action(db, module, action)
            if permission:
                permission_ids.append(permission.id)
        self.role_repo.set_role_permissions(db, role.id, permission_ids)
        return role

    def list_roles(self, db: Session, company_id: uuid.UUID) -> list[Role]:
        return self.role_repo.list_roles(db, company_id)

    def get_role(self, db: Session, company_id: uuid.UUID, role_id: uuid.UUID) -> Role:
        role = self.role_repo.get(db, company_id, role_id)
        if role is None:
            raise NotFoundError("Role not found")
        return role

    def create_role(self, db: Session, company_id: uuid.UUID, name: str) -> Role:
        existing = [r for r in self.role_repo.list_roles(db, company_id) if r.name == name]
        if existing:
            raise ConflictError("A role with this name already exists")
        role = self.role_repo.create(db, company_id, name, is_system=False)
        db.commit()
        return role

    def update_role_name(self, db: Session, company_id: uuid.UUID, role_id: uuid.UUID, name: str) -> Role:
        role = self.get_role(db, company_id, role_id)
        role.name = name
        db.commit()
        return role

    def update_permissions(
        self, db: Session, company_id: uuid.UUID, role_id: uuid.UUID, grants: list[dict]
    ) -> Role:
        role = self.get_role(db, company_id, role_id)
        permission_ids = []
        for grant in grants:
            if not grant["granted"]:
                continue
            if grant["module"] not in PERMISSION_CATALOG or grant["action"] not in PERMISSION_CATALOG[grant["module"]]:
                raise ValidationAppError(f"Unknown permission {grant['module']}.{grant['action']}")
            permission = self.role_repo.get_permission_by_module_action(db, grant["module"], grant["action"])
            if permission:
                permission_ids.append(permission.id)
        self.role_repo.set_role_permissions(db, role.id, permission_ids)
        db.commit()
        self._invalidate_users_with_role(db, role_id)
        return self.get_role(db, company_id, role_id)

    def delete_role(self, db: Session, company_id: uuid.UUID, role_id: uuid.UUID) -> None:
        role = self.get_role(db, company_id, role_id)
        if role.is_system:
            raise ValidationAppError("System roles cannot be deleted")
        db.delete(role)
        db.commit()

    def _invalidate_users_with_role(self, db: Session, role_id: uuid.UUID) -> None:
        from sqlalchemy import select

        from app.models.role import UserRole

        user_ids = db.execute(select(UserRole.user_id).where(UserRole.role_id == role_id)).scalars().all()
        for user_id in user_ids:
            permission_cache.invalidate(user_id)


role_service = RoleService()
