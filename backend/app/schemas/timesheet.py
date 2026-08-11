import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

VALID_PERIOD_TYPES = {"daily", "weekly", "monthly"}
VALID_WORK_TYPES = {"office", "remote", "client_site"}


class TimesheetPeriodConfigResponse(ORMModel):
    id: uuid.UUID
    period_type: str
    week_start_day: int
    min_hours_per_day: Decimal | None
    max_hours_per_day: Decimal | None
    require_description: bool
    warn_on_weekend: bool
    require_finance_approval: bool


class TimesheetPeriodConfigUpdateRequest(BaseModel):
    period_type: str | None = None
    week_start_day: int | None = Field(default=None, ge=0, le=6)
    min_hours_per_day: Decimal | None = None
    max_hours_per_day: Decimal | None = None
    require_description: bool | None = None
    warn_on_weekend: bool | None = None
    require_finance_approval: bool | None = None


class TimesheetEntryCreateRequest(BaseModel):
    project_id: uuid.UUID
    entry_date: date
    hours: Decimal = Field(gt=0, le=24)
    is_billable: bool = True
    work_type: str = "office"
    description: str | None = Field(default=None, max_length=500)


class TimesheetEntryUpdateRequest(BaseModel):
    project_id: uuid.UUID | None = None
    hours: Decimal | None = Field(default=None, gt=0, le=24)
    is_billable: bool | None = None
    work_type: str | None = None
    description: str | None = Field(default=None, max_length=500)


class TimesheetEntryResponse(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    entry_date: date
    hours: Decimal
    is_billable: bool
    work_type: str
    description: str | None
    status: str
    is_weekend: bool
    submission_id: uuid.UUID | None


class TimesheetSubmitRequest(BaseModel):
    ref_date: date


class TimesheetRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class TimesheetBulkApproveRequest(BaseModel):
    submission_ids: list[uuid.UUID]


class BulkApproveFailure(BaseModel):
    id: uuid.UUID
    reason: str


class TimesheetBulkApproveResponse(BaseModel):
    approved: list[uuid.UUID]
    failed: list[BulkApproveFailure]


class TimesheetSubmissionResponse(ORMModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    period_start: date
    period_end: date
    status: str
    submitted_at: datetime
    manager_approved_at: datetime | None
    finance_approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    total_hours: Decimal
    entries: list[TimesheetEntryResponse]


class HoursByBucket(BaseModel):
    id: uuid.UUID
    name: str
    hours: Decimal


class TimesheetDashboardResponse(BaseModel):
    pending_count: int
    rejected_count: int
    late_count: int
    billable_percentage: float
    hours_by_project: list[HoursByBucket]
    hours_by_employee: list[HoursByBucket]
