import uuid
from datetime import date as _date
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class LeaveTypeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_paid: bool = True
    annual_quota_days: int | None = Field(default=None, ge=0)
    max_carry_forward_days: int = Field(default=0, ge=0)
    requires_attachment: bool = False


class LeaveTypeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_paid: bool | None = None
    annual_quota_days: int | None = Field(default=None, ge=0)
    max_carry_forward_days: int | None = Field(default=None, ge=0)
    requires_attachment: bool | None = None


class LeaveTypeResponse(ORMModel):
    id: uuid.UUID
    name: str
    is_paid: bool
    annual_quota_days: int | None
    max_carry_forward_days: int
    requires_attachment: bool


class HolidayCreateRequest(BaseModel):
    date: _date
    name: str = Field(min_length=1, max_length=150)
    location: str | None = Field(default=None, max_length=100)


class HolidayUpdateRequest(BaseModel):
    date: _date | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    location: str | None = None
    clear_location: bool = False


class HolidayResponse(ORMModel):
    id: uuid.UUID
    date: _date
    name: str
    location: str | None


class LeaveSettingsResponse(BaseModel):
    require_hr_leave_approval: bool


class LeaveSettingsUpdateRequest(BaseModel):
    require_hr_leave_approval: bool


class LeaveBalanceResponse(BaseModel):
    employee_id: uuid.UUID | None = None
    employee_name: str | None = None
    leave_type_id: uuid.UUID
    leave_type_name: str
    year: int
    granted: str | None
    carried_forward: str
    adjustment: str
    used: str
    available: str | None


class LeaveRequestResponse(ORMModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    leave_type_id: uuid.UUID
    leave_type_name: str
    start_date: _date
    end_date: _date
    days_count: int
    reason: str | None
    attachment_original_filename: str | None
    status: str
    manager_approved_at: datetime | None
    hr_approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    cancelled_at: datetime | None
    created_at: datetime


class RejectLeaveRequestPayload(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CarryForwardRequest(BaseModel):
    from_year: int
    employee_id: uuid.UUID | None = None


class LeaveDashboardResponse(BaseModel):
    pending_count: int
    on_leave_today_count: int
