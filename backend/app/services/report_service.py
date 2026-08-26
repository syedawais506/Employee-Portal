from __future__ import annotations

import uuid

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.report import SavedReport
from app.repositories.report_repository import SavedReportRepository
from app.schemas.report import (
    AssetReportFilters,
    DepartmentReportFilters,
    EmployeeReportFilters,
    LeaveReportFilters,
    ProjectReportFilters,
    TimesheetReportFilters,
)
from app.services.asset_service import asset_service
from app.services.audit_service import audit_service
from app.services.department_service import department_service
from app.services.employee_service import employee_service
from app.services.leave_service import leave_service
from app.services.project_service import project_service
from app.services.timesheet_service import timesheet_service
from app.utils.csv_export import build_csv

PREVIEW_LIMIT = 200

MODULE_FILTER_SCHEMAS: dict[str, type[BaseModel]] = {
    "employee": EmployeeReportFilters,
    "department": DepartmentReportFilters,
    "project": ProjectReportFilters,
    "timesheet": TimesheetReportFilters,
    "leave": LeaveReportFilters,
    "asset": AssetReportFilters,
}


class ReportService:
    def __init__(self) -> None:
        self.saved_report_repo = SavedReportRepository()

    def _validate_filters(self, module: str, filters: dict) -> BaseModel:
        schema = MODULE_FILTER_SCHEMAS.get(module)
        if schema is None:
            raise ValidationAppError(f"Unknown report module: {module}")
        try:
            return schema(**filters)
        except ValidationError as exc:
            raise ValidationAppError("Invalid filters for this report module") from exc

    def _rows_for_module(
        self, db: Session, company_id: uuid.UUID, module: str, parsed_filters: BaseModel
    ) -> tuple[list[str], list[list]]:
        kwargs = parsed_filters.model_dump()
        if module == "employee":
            return employee_service.report_rows(db, company_id, **kwargs)
        if module == "department":
            return department_service.report_rows(db, company_id, **kwargs)
        if module == "project":
            return project_service.report_rows(db, company_id, **kwargs)
        if module == "timesheet":
            return timesheet_service.report_rows(db, company_id, **kwargs)
        if module == "leave":
            return leave_service.report_rows(db, company_id, **kwargs)
        if module == "asset":
            return asset_service.report_rows(db, company_id, **kwargs)
        raise ValidationAppError(f"Unknown report module: {module}")

    def preview(self, db: Session, company_id: uuid.UUID, *, module: str, filters: dict) -> dict:
        parsed = self._validate_filters(module, filters)
        header, rows = self._rows_for_module(db, company_id, module, parsed)
        total = len(rows)
        return {"header": header, "rows": rows[:PREVIEW_LIMIT], "total": total, "truncated": total > PREVIEW_LIMIT}

    def export_csv(self, db: Session, company_id: uuid.UUID, *, module: str, filters: dict) -> str:
        parsed = self._validate_filters(module, filters)
        header, rows = self._rows_for_module(db, company_id, module, parsed)
        return build_csv(header, rows)

    # -- Saved reports -----------------------------------------------------

    def list_saved_reports(self, db: Session, company_id: uuid.UUID) -> list[SavedReport]:
        return self.saved_report_repo.list_all(db, company_id)

    def get_saved_report(self, db: Session, company_id: uuid.UUID, report_id: uuid.UUID) -> SavedReport:
        report = self.saved_report_repo.get(db, company_id, report_id)
        if report is None:
            raise NotFoundError("Saved report not found")
        return report

    def create_saved_report(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str,
        module: str,
        filters: dict,
        actor_user_id: uuid.UUID,
    ) -> SavedReport:
        if self.saved_report_repo.get_by_name(db, company_id, name) is not None:
            raise ConflictError("A saved report with this name already exists")
        self._validate_filters(module, filters)
        report = self.saved_report_repo.create(
            db, company_id, name=name, module=module, filters=filters, created_by=actor_user_id
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="saved_report",
            entity_id=report.id,
            action="create",
            after={"name": name, "module": module},
        )
        db.commit()
        return report

    def update_saved_report(
        self, db: Session, company_id: uuid.UUID, report_id: uuid.UUID, *, actor_user_id: uuid.UUID, **updates
    ) -> SavedReport:
        report = self.get_saved_report(db, company_id, report_id)
        if updates.get("filters") is not None:
            self._validate_filters(report.module, updates["filters"])
        before = {"name": report.name}
        for field, value in updates.items():
            if value is not None:
                setattr(report, field, value)
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="saved_report",
            entity_id=report.id,
            action="update",
            before=before,
            after={"name": report.name},
        )
        db.commit()
        return report

    def delete_saved_report(
        self, db: Session, company_id: uuid.UUID, report_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        report = self.get_saved_report(db, company_id, report_id)
        self.saved_report_repo.delete(db, company_id, report_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="saved_report",
            entity_id=report_id,
            action="delete",
            before={"name": report.name},
        )
        db.commit()

    def run_saved_report(self, db: Session, company_id: uuid.UUID, report_id: uuid.UUID) -> dict:
        report = self.get_saved_report(db, company_id, report_id)
        return self.preview(db, company_id, module=report.module, filters=report.filters)

    def export_saved_report(self, db: Session, company_id: uuid.UUID, report_id: uuid.UUID) -> str:
        report = self.get_saved_report(db, company_id, report_id)
        return self.export_csv(db, company_id, module=report.module, filters=report.filters)


report_service = ReportService()
