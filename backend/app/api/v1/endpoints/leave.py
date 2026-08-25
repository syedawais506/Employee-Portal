import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_permission
from app.core.exceptions import ValidationAppError
from app.models.user import User
from app.schemas.common import Page
from app.schemas.leave import (
    CarryForwardRequest,
    HolidayCreateRequest,
    HolidayResponse,
    HolidayUpdateRequest,
    LeaveBalanceResponse,
    LeaveDashboardResponse,
    LeaveRequestResponse,
    LeaveSettingsResponse,
    LeaveSettingsUpdateRequest,
    LeaveTypeCreateRequest,
    LeaveTypeResponse,
    LeaveTypeUpdateRequest,
    RejectLeaveRequestPayload,
)
from app.services.auth_service import auth_service
from app.services.employee_service import employee_service
from app.services.leave_service import leave_service
from app.utils.storage import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_SIZE_BYTES

router = APIRouter(tags=["leave"])


def _employee_id(current_user: User, db: Session) -> uuid.UUID:
    return employee_service.get_employee_by_user_id(db, current_user.id).id


def _can_act_for_others(current_user: User, db: Session) -> bool:
    if current_user.is_super_admin:
        return True
    return "leave.approve" in auth_service.get_effective_permissions(db, current_user.id)


# -- Leave types -------------------------------------------------------------


@router.get("/leave-types", response_model=list[LeaveTypeResponse])
def list_leave_types(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "view")),
):
    return leave_service.list_leave_types(db, company_id)


@router.post("/leave-types", response_model=LeaveTypeResponse, status_code=201)
def create_leave_type(
    payload: LeaveTypeCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    return leave_service.create_leave_type(db, company_id, **payload.model_dump(), actor_user_id=current_user.id)


@router.patch("/leave-types/{leave_type_id}", response_model=LeaveTypeResponse)
def update_leave_type(
    leave_type_id: uuid.UUID,
    payload: LeaveTypeUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    return leave_service.update_leave_type(db, company_id, leave_type_id, actor_user_id=current_user.id, **updates)


@router.delete("/leave-types/{leave_type_id}", status_code=204)
def delete_leave_type(
    leave_type_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    leave_service.delete_leave_type(db, company_id, leave_type_id, actor_user_id=current_user.id)


# -- Holidays -----------------------------------------------------------------


@router.get("/holidays", response_model=list[HolidayResponse])
def list_holidays(
    year: int | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "view")),
):
    return leave_service.list_holidays(db, company_id, year=year)


@router.post("/holidays", response_model=HolidayResponse, status_code=201)
def create_holiday(
    payload: HolidayCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    return leave_service.create_holiday(
        db,
        company_id,
        date=payload.date,
        name=payload.name,
        location=payload.location,
        actor_user_id=current_user.id,
    )


@router.patch("/holidays/{holiday_id}", response_model=HolidayResponse)
def update_holiday(
    holiday_id: uuid.UUID,
    payload: HolidayUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    return leave_service.update_holiday(db, company_id, holiday_id, actor_user_id=current_user.id, **updates)


@router.delete("/holidays/{holiday_id}", status_code=204)
def delete_holiday(
    holiday_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    leave_service.delete_holiday(db, company_id, holiday_id, actor_user_id=current_user.id)


# -- Settings -----------------------------------------------------------------


@router.get("/leave/settings", response_model=LeaveSettingsResponse)
def get_leave_settings(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "view")),
):
    return LeaveSettingsResponse(require_hr_leave_approval=leave_service.get_settings(db, company_id))


@router.patch("/leave/settings", response_model=LeaveSettingsResponse)
def update_leave_settings(
    payload: LeaveSettingsUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    value = leave_service.update_settings(
        db, company_id, require_hr_leave_approval=payload.require_hr_leave_approval, actor_user_id=current_user.id
    )
    return LeaveSettingsResponse(require_hr_leave_approval=value)


# -- Balances -----------------------------------------------------------------


@router.get("/leave/balances/mine", response_model=list[LeaveBalanceResponse])
def list_my_balances(
    year: int | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _employee_id(current_user, db)
    return leave_service.list_my_balances(db, company_id, employee_id, year or date.today().year)


@router.get("/leave/balances", response_model=list[LeaveBalanceResponse])
def list_company_balances(
    year: int | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "approve")),
):
    return leave_service.list_company_balances(db, company_id, year=year or date.today().year, employee_id=employee_id)


# -- Requests -----------------------------------------------------------------


@router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=201)
async def create_leave_request(
    leave_type_id: uuid.UUID = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    reason: str | None = Form(default=None),
    employee_id: uuid.UUID | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "create")),
    db: Session = Depends(get_db),
):
    attachment = None
    if file is not None and file.filename:
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise ValidationAppError("Attachment exceeds the 10 MB limit")
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationAppError("Attachment must be a PDF, PNG, or JPEG")
        attachment = (content, file.filename, content_type)

    caller_employee_id = _employee_id(current_user, db)
    return leave_service.create_request(
        db,
        company_id,
        caller_employee_id=caller_employee_id,
        requested_employee_id=employee_id,
        can_act_for_others=_can_act_for_others(current_user, db),
        leave_type_id=leave_type_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        attachment=attachment,
        actor_user_id=current_user.id,
    )


@router.get("/leave-requests/mine", response_model=list[LeaveRequestResponse])
def list_my_leave_requests(
    status: str | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _employee_id(current_user, db)
    return leave_service.list_my_requests(db, company_id, employee_id, status=status)


@router.get("/leave-requests", response_model=Page[LeaveRequestResponse])
def list_leave_requests(
    employee_id: uuid.UUID | None = Query(default=None),
    leave_type_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "approve")),
):
    return leave_service.list_requests(
        db,
        company_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("/leave-requests/{request_id}/cancel", response_model=LeaveRequestResponse)
def cancel_leave_request(
    request_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "update")),
    db: Session = Depends(get_db),
):
    caller_employee_id = _employee_id(current_user, db)
    return leave_service.cancel_request(
        db, company_id, request_id,
        caller_employee_id=caller_employee_id,
        can_act_for_others=_can_act_for_others(current_user, db),
        actor_user_id=current_user.id,
    )


@router.delete("/leave-requests/{request_id}", status_code=204)
def delete_leave_request(
    request_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "delete")),
    db: Session = Depends(get_db),
):
    leave_service.delete_request(db, company_id, request_id, actor_user_id=current_user.id)


@router.post("/leave-requests/{request_id}/approve", response_model=LeaveRequestResponse)
def approve_leave_request(
    request_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "approve")),
    db: Session = Depends(get_db),
):
    return leave_service.approve_request(db, company_id, request_id, actor_user_id=current_user.id)


@router.post("/leave-requests/{request_id}/reject", response_model=LeaveRequestResponse)
def reject_leave_request(
    request_id: uuid.UUID,
    payload: RejectLeaveRequestPayload,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "reject")),
    db: Session = Depends(get_db),
):
    return leave_service.reject_request(
        db, company_id, request_id, reason=payload.reason, actor_user_id=current_user.id
    )


# -- Carry forward, dashboard, export -----------------------------------------


@router.post("/leave/carry-forward")
def run_carry_forward(
    payload: CarryForwardRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("leave", "configure")),
    db: Session = Depends(get_db),
):
    return leave_service.run_carry_forward(
        db, company_id, from_year=payload.from_year, employee_id=payload.employee_id, actor_user_id=current_user.id
    )


@router.get("/leave/dashboard", response_model=LeaveDashboardResponse)
def get_leave_dashboard(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "approve")),
):
    return leave_service.get_dashboard(db, company_id)


@router.get("/leave/export")
def export_leave_requests(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    leave_type_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("leave", "export")),
):
    csv_text = leave_service.export_csv(
        db, company_id, date_from=date_from, date_to=date_to,
        employee_id=employee_id, leave_type_id=leave_type_id, status=status,
    )
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leave-export.csv"'},
    )
