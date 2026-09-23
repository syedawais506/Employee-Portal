import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

AttendanceMode = Literal["check_in_out", "timesheet"]


class AttendanceShiftConfigResponse(BaseModel):
    enabled: bool
    mode: AttendanceMode
    shift_start: time
    shift_end: time
    grace_period_minutes: int


class AttendanceShiftConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    mode: AttendanceMode | None = None
    shift_start: time | None = None
    shift_end: time | None = None
    grace_period_minutes: int | None = Field(default=None, ge=0, le=180)


class AttendanceRecordResponse(ORMModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    attendance_date: date
    check_in_at: datetime | None
    check_out_at: datetime | None
    is_late: bool
    overtime_hours: Decimal
    status: str


class TodayAttendanceEntry(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    check_in_at: datetime | None
    check_out_at: datetime | None
    is_late: bool
    status: str
