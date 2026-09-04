import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class EmployeeCreateRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = None
    department_id: uuid.UUID | None = None
    designation: str | None = None
    manager_id: uuid.UUID | None = None
    employment_type: str = "full_time"
    location: str | None = None
    joining_date: date | None = None
    role_ids: list[uuid.UUID] = []


class EmployeeUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = None
    department_id: uuid.UUID | None = None
    designation: str | None = None
    manager_id: uuid.UUID | None = None
    employment_type: str | None = None
    location: str | None = None
    status: str | None = None


class EmployeeSelfUpdateRequest(BaseModel):
    phone: str | None = None


class EmployeeRoleAssignmentRequest(BaseModel):
    role_ids: list[uuid.UUID]


class DepartmentRef(ORMModel):
    id: uuid.UUID
    name: str


class ManagerRef(ORMModel):
    id: uuid.UUID
    first_name: str
    last_name: str


class RoleRef(ORMModel):
    id: uuid.UUID
    name: str


class EmployeeSummaryResponse(ORMModel):
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    designation: str | None
    department: DepartmentRef | None
    status: str
    employment_type: str
    location: str | None
    onboarding_status: str


class EmployeeDetailResponse(ORMModel):
    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    department: DepartmentRef | None
    designation: str | None
    manager: ManagerRef | None
    employment_type: str
    location: str | None
    joining_date: date | None
    status: str
    onboarding_status: str
    roles: list[RoleRef]
