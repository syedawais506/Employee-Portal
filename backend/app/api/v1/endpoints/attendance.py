import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.attendance import (
    AttendanceRecordResponse,
    AttendanceShiftConfigResponse,
    AttendanceShiftConfigUpdateRequest,
    TodayAttendanceEntry,
)
from app.schemas.common import Page
from app.services.attendance_service import attendance_service
from app.services.employee_service import employee_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _current_employee_id(current_user: User, db: Session) -> uuid.UUID:
    return employee_service.get_employee_by_user_id(db, current_user.id).id


@router.get("/settings", response_model=AttendanceShiftConfigResponse)
def get_settings(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance", "view")),
):
    return attendance_service.get_shift_config(db, company_id)


@router.patch("/settings", response_model=AttendanceShiftConfigResponse)
def update_settings(
    payload: AttendanceShiftConfigUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("attendance", "configure")),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    return attendance_service.update_shift_config(db, company_id, actor_user_id=current_user.id, **updates)


@router.post("/check-in", response_model=AttendanceRecordResponse, status_code=201)
def check_in(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return attendance_service.check_in(db, company_id, employee_id)


@router.post("/check-out", response_model=AttendanceRecordResponse)
def check_out(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return attendance_service.check_out(db, company_id, employee_id)


@router.get("/mine", response_model=list[AttendanceRecordResponse])
def list_my_records(
    date_from: date = Query(...),
    date_to: date = Query(...),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return attendance_service.list_my_records(db, company_id, employee_id, date_from, date_to)


@router.get("/today", response_model=list[TodayAttendanceEntry])
def today_dashboard(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance", "view")),
):
    return attendance_service.today_dashboard(db, company_id)


@router.get("", response_model=Page[AttendanceRecordResponse])
def list_records(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance", "view")),
):
    return attendance_service.list_records(
        db, company_id, date_from=date_from, date_to=date_to, employee_id=employee_id, page=page, page_size=page_size
    )


@router.get("/export")
def export_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("attendance", "export")),
):
    csv_text = attendance_service.export_csv(
        db, company_id, date_from=date_from, date_to=date_to, employee_id=employee_id
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendance-export.csv"'},
    )
