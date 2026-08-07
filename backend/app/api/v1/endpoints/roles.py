import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.role import (
    PermissionCatalogEntry,
    RoleCreateRequest,
    RolePermissionsUpdateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.services.role_service import role_service

router = APIRouter(tags=["roles"])


def _to_role_response(role) -> RoleResponse:
    permissions = [
        {"module": rp.permission.module, "action": rp.permission.action, "granted": True}
        for rp in role.role_permissions
    ]
    return RoleResponse(id=role.id, name=role.name, is_system=role.is_system, permissions=permissions)


@router.get("/permissions/catalog", response_model=list[PermissionCatalogEntry])
def get_permission_catalog(_: User = Depends(get_current_user)):
    return role_service.get_permission_catalog()


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role", "view")),
):
    return [_to_role_response(r) for r in role_service.list_roles(db, company_id)]


@router.post("/roles", response_model=RoleResponse, status_code=201)
def create_role(
    payload: RoleCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role", "create")),
):
    role = role_service.create_role(db, company_id, payload.name)
    return _to_role_response(role)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role", "update")),
):
    role = role_service.update_role_name(db, company_id, role_id, payload.name)
    return _to_role_response(role)


@router.put("/roles/{role_id}/permissions", response_model=RoleResponse)
def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role", "update")),
):
    role = role_service.update_permissions(
        db, company_id, role_id, [grant.model_dump() for grant in payload.permissions]
    )
    return _to_role_response(role)


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(
    role_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("role", "delete")),
):
    role_service.delete_role(db, company_id, role_id)
