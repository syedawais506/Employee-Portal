from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.role import Permission, Role, RolePermission, UserRole


class RoleRepository:
    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .options(joinedload(Role.role_permissions).joinedload(RolePermission.permission))
            .where(Role.id == id, Role.company_id == company_id)
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def list_roles(self, db: Session, company_id: uuid.UUID) -> list[Role]:
        stmt = (
            select(Role)
            .options(joinedload(Role.role_permissions).joinedload(RolePermission.permission))
            .where(Role.company_id == company_id)
            .order_by(Role.name)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def create(self, db: Session, company_id: uuid.UUID, name: str, is_system: bool = False) -> Role:
        role = Role(company_id=company_id, name=name, is_system=is_system)
        db.add(role)
        db.flush()
        return role

    def get_permission_catalog(self, db: Session) -> list[Permission]:
        return list(db.execute(select(Permission).order_by(Permission.module, Permission.action)).scalars().all())

    def get_permission_by_module_action(self, db: Session, module: str, action: str) -> Permission | None:
        stmt = select(Permission).where(Permission.module == module, Permission.action == action)
        return db.execute(stmt).scalar_one_or_none()

    def set_role_permissions(self, db: Session, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for permission_id in permission_ids:
            db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        db.flush()

    def set_user_roles(self, db: Session, user_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        for role_id in role_ids:
            db.add(UserRole(user_id=user_id, role_id=role_id))
        db.flush()

    def list_user_ids_with_role(self, db: Session, role_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(UserRole.user_id).where(UserRole.role_id == role_id)
        return list(db.execute(stmt).scalars().all())

    def get_effective_permission_codes(self, db: Session, user_id: uuid.UUID) -> set[str]:
        stmt = (
            select(Permission.module, Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return {f"{module}.{action}" for module, action in db.execute(stmt).all()}
