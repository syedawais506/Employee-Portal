import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AttendanceShiftConfigResponse(ORMModel):
    shift_start: time
    shift_end: time
    grace_period_minutes: int


class AttendanceShiftConfigUpdateRequest(BaseModel):
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
