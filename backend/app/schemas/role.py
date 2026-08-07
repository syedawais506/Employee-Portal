import uuid

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PermissionGrant(BaseModel):
    module: str
    action: str
    granted: bool


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class RoleUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class RolePermissionsUpdateRequest(BaseModel):
    permissions: list[PermissionGrant]


class RoleResponse(ORMModel):
    id: uuid.UUID
    name: str
    is_system: bool
    permissions: list[PermissionGrant] = []


class PermissionCatalogEntry(BaseModel):
    module: str
    actions: list[str]
