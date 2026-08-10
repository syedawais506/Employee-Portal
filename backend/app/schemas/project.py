import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class ClientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class ClientResponse(ORMModel):
    id: uuid.UUID
    name: str
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None


class ProjectMemberInput(BaseModel):
    employee_id: uuid.UUID
    role_on_project: str = "member"


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_id: uuid.UUID | None = None
    budget: Decimal | None = None
    is_billable: bool = True
    start_date: date | None = None
    end_date: date | None = None
    member_ids: list[ProjectMemberInput] = []


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    client_id: uuid.UUID | None = None
    budget: Decimal | None = None
    is_billable: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class ProjectMemberResponse(ORMModel):
    employee_id: uuid.UUID
    first_name: str
    last_name: str
    role_on_project: str


class ProjectSummaryResponse(ORMModel):
    id: uuid.UUID
    name: str
    status: str
    is_billable: bool
    start_date: date | None
    end_date: date | None
    member_count: int
    client: ClientResponse | None


class ProjectDetailResponse(ORMModel):
    id: uuid.UUID
    name: str
    client: ClientResponse | None
    budget: Decimal | None
    is_billable: bool
    start_date: date | None
    end_date: date | None
    status: str
    members: list[ProjectMemberResponse]


class MyProjectResponse(ORMModel):
    id: uuid.UUID
    name: str
    status: str
    role_on_project: str
    start_date: date | None
    end_date: date | None
