import uuid
from datetime import date as _date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

ReportModule = Literal["employee", "department", "project", "timesheet", "leave", "asset"]


class EmployeeReportFilters(BaseModel):
    search: str | None = None
    department_id: uuid.UUID | None = None
    status: str | None = None
    manager_id: uuid.UUID | None = None
    employment_type: str | None = None
    location: str | None = None
    joining_date_from: _date | None = None
    joining_date_to: _date | None = None


class DepartmentReportFilters(BaseModel):
    search: str | None = None
    parent_department_id: uuid.UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class ProjectReportFilters(BaseModel):
    status: str | None = None
    client_id: uuid.UUID | None = None
    is_billable: bool | None = None
    start_date_from: _date | None = None
    start_date_to: _date | None = None


class TimesheetReportFilters(BaseModel):
    date_from: _date | None = None
    date_to: _date | None = None
    employee_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    location: str | None = None


class LeaveReportFilters(BaseModel):
    date_from: _date | None = None
    date_to: _date | None = None
    employee_id: uuid.UUID | None = None
    leave_type_id: uuid.UUID | None = None
    status: str | None = None


class AssetReportFilters(BaseModel):
    asset_type_id: uuid.UUID | None = None
    status: str | None = None


class RunReportRequest(BaseModel):
    module: ReportModule
    filters: dict = Field(default_factory=dict)


class ReportPreviewResponse(BaseModel):
    header: list[str]
    rows: list[list]
    total: int
    truncated: bool


class SavedReportCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    module: ReportModule
    filters: dict = Field(default_factory=dict)


class SavedReportUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    filters: dict | None = None


class SavedReportResponse(ORMModel):
    id: uuid.UUID
    name: str
    module: str
    filters: dict
    created_at: datetime
