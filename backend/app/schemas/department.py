import uuid

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_department_id: uuid.UUID | None = None
    cost_center_code: str | None = None


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_department_id: uuid.UUID | None = None
    cost_center_code: str | None = None


class DepartmentResponse(ORMModel):
    id: uuid.UUID
    name: str
    parent_department_id: uuid.UUID | None
    cost_center_code: str | None
