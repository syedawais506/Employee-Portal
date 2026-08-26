import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.user import User
from app.schemas.report import (
    ReportPreviewResponse,
    RunReportRequest,
    SavedReportCreateRequest,
    SavedReportResponse,
    SavedReportUpdateRequest,
)
from app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/preview", response_model=ReportPreviewResponse)
def preview_report(
    payload: RunReportRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("report", "view")),
):
    return report_service.preview(db, company_id, module=payload.module, filters=payload.filters)


@router.post("/export")
def export_report(
    payload: RunReportRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("report", "export")),
):
    csv_text = report_service.export_csv(db, company_id, module=payload.module, filters=payload.filters)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{payload.module}-report.csv"'},
    )


@router.get("/saved", response_model=list[SavedReportResponse])
def list_saved_reports(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("report", "view")),
):
    return report_service.list_saved_reports(db, company_id)


@router.post("/saved", response_model=SavedReportResponse, status_code=201)
def create_saved_report(
    payload: SavedReportCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("report", "configure")),
    db: Session = Depends(get_db),
):
    return report_service.create_saved_report(
        db,
        company_id,
        name=payload.name,
        module=payload.module,
        filters=payload.filters,
        actor_user_id=current_user.id,
    )


@router.patch("/saved/{report_id}", response_model=SavedReportResponse)
def update_saved_report(
    report_id: uuid.UUID,
    payload: SavedReportUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("report", "configure")),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    return report_service.update_saved_report(db, company_id, report_id, actor_user_id=current_user.id, **updates)


@router.delete("/saved/{report_id}", status_code=204)
def delete_saved_report(
    report_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("report", "configure")),
    db: Session = Depends(get_db),
):
    report_service.delete_saved_report(db, company_id, report_id, actor_user_id=current_user.id)


@router.post("/saved/{report_id}/run", response_model=ReportPreviewResponse)
def run_saved_report(
    report_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("report", "view")),
):
    return report_service.run_saved_report(db, company_id, report_id)


@router.get("/saved/{report_id}/export")
def export_saved_report(
    report_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("report", "export")),
):
    csv_text = report_service.export_saved_report(db, company_id, report_id)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="saved-report-export.csv"'},
    )
