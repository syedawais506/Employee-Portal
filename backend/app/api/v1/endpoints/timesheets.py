import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_any_permission, require_permission
from app.models.user import User
from app.schemas.common import Page
from app.schemas.timesheet import (
    TimesheetBulkApproveRequest,
    TimesheetBulkApproveResponse,
    TimesheetDashboardResponse,
    TimesheetEntryCreateRequest,
    TimesheetEntryResponse,
    TimesheetEntryUpdateRequest,
    TimesheetPeriodConfigResponse,
    TimesheetPeriodConfigUpdateRequest,
    TimesheetRejectRequest,
    TimesheetSubmissionResponse,
    TimesheetSubmitRequest,
)
from app.services.employee_service import employee_service
from app.services.timesheet_service import timesheet_service

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


def _current_employee_id(current_user: User, db: Session) -> uuid.UUID:
    return employee_service.get_employee_by_user_id(db, current_user.id).id


@router.get("/config", response_model=TimesheetPeriodConfigResponse)
def get_config(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("timesheet", "view")),
):
    return timesheet_service.get_config(db, company_id)


@router.patch("/config", response_model=TimesheetPeriodConfigResponse)
def update_config(
    payload: TimesheetPeriodConfigUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("timesheet", "configure")),
):
    updates = payload.model_dump(exclude_unset=True)
    return timesheet_service.update_config(db, company_id, actor_user_id=current_user.id, **updates)


@router.get("/entries", response_model=list[TimesheetEntryResponse])
def list_my_entries(
    date_from: date = Query(...),
    date_to: date = Query(...),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "view")),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return timesheet_service.list_my_entries(db, company_id, employee_id, date_from, date_to)


@router.post("/entries", response_model=TimesheetEntryResponse, status_code=201)
def create_entry(
    payload: TimesheetEntryCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "create")),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return timesheet_service.create_entry(
        db,
        company_id,
        employee_id,
        project_id=payload.project_id,
        entry_date=payload.entry_date,
        hours=payload.hours,
        is_billable=payload.is_billable,
        work_type=payload.work_type,
        description=payload.description,
        actor_user_id=current_user.id,
    )


@router.patch("/entries/{entry_id}", response_model=TimesheetEntryResponse)
def update_entry(
    entry_id: uuid.UUID,
    payload: TimesheetEntryUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "update")),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    updates = payload.model_dump(exclude_unset=True)
    return timesheet_service.update_entry(
        db, company_id, employee_id, entry_id, actor_user_id=current_user.id, **updates
    )


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "update")),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    timesheet_service.delete_entry(db, company_id, employee_id, entry_id, actor_user_id=current_user.id)


@router.post("/submissions", response_model=TimesheetSubmissionResponse, status_code=201)
def submit_period(
    payload: TimesheetSubmitRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "update")),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return timesheet_service.submit_period(db, company_id, employee_id, payload.ref_date, actor_user_id=current_user.id)


@router.get("/submissions/mine", response_model=list[TimesheetSubmissionResponse])
def list_my_submissions(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _current_employee_id(current_user, db)
    return timesheet_service.list_my_submissions(db, company_id, employee_id)


@router.get("/submissions", response_model=Page[TimesheetSubmissionResponse])
def list_submissions(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("timesheet", "approve")),
):
    return timesheet_service.list_submissions(db, company_id, status=status, page=page, page_size=page_size)


@router.post("/submissions/bulk-approve", response_model=TimesheetBulkApproveResponse)
def bulk_approve(
    payload: TimesheetBulkApproveRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "approve")),
    db: Session = Depends(get_db),
):
    return timesheet_service.bulk_approve(db, company_id, payload.submission_ids, actor_user_id=current_user.id)


@router.post("/submissions/{submission_id}/approve", response_model=TimesheetSubmissionResponse)
def approve_submission(
    submission_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "approve")),
    db: Session = Depends(get_db),
):
    return timesheet_service.approve_submission(db, company_id, submission_id, actor_user_id=current_user.id)


@router.post("/submissions/{submission_id}/reject", response_model=TimesheetSubmissionResponse)
def reject_submission(
    submission_id: uuid.UUID,
    payload: TimesheetRejectRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "reject")),
    db: Session = Depends(get_db),
):
    return timesheet_service.reject_submission(
        db, company_id, submission_id, reason=payload.reason, actor_user_id=current_user.id
    )


@router.post("/submissions/{submission_id}/reopen", response_model=TimesheetSubmissionResponse)
def reopen_submission(
    submission_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("timesheet", "delete")),
    db: Session = Depends(get_db),
):
    return timesheet_service.reopen_submission(db, company_id, submission_id, actor_user_id=current_user.id)


@router.get("/dashboard", response_model=TimesheetDashboardResponse)
def get_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission(("timesheet", "approve"), ("timesheet", "export"))),
):
    return timesheet_service.get_dashboard(db, company_id, date_from=date_from, date_to=date_to)


@router.get("/export")
def export_csv(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    project_id: uuid.UUID | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("timesheet", "export")),
):
    csv_text = timesheet_service.export_csv(
        db, company_id, date_from=date_from, date_to=date_to, employee_id=employee_id, project_id=project_id
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="timesheet-export.csv"'},
    )
