from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.timesheet import TimesheetEntry, TimesheetPeriodConfig, TimesheetSubmission
from app.repositories.project_repository import ProjectMemberRepository, ProjectRepository
from app.repositories.timesheet_repository import (
    TimesheetEntryRepository,
    TimesheetPeriodConfigRepository,
    TimesheetSubmissionRepository,
)
from app.schemas.common import Page
from app.schemas.timesheet import VALID_PERIOD_TYPES, VALID_WORK_TYPES
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.utils.csv_export import build_csv

OPEN_SUBMISSION_STATUSES = {"submitted", "manager_approved"}

# Submission date ranges are free-form (chosen by the employee at submit time,
# not snapped to timesheet_period_config) — config's period_type/week_start_day
# only drive the rule engine and dashboard now, not what a submission covers.
BUCKET_STATUSES: dict[str, list[str]] = {
    "pending": ["submitted", "manager_approved"],
    "approved": ["approved"],
    "rejected": ["rejected"],
}


class TimesheetService:
    def __init__(self) -> None:
        self.config_repo = TimesheetPeriodConfigRepository()
        self.entry_repo = TimesheetEntryRepository()
        self.submission_repo = TimesheetSubmissionRepository()
        self.project_repo = ProjectRepository()
        self.member_repo = ProjectMemberRepository()

    # -- Config -----------------------------------------------------------

    def get_config(self, db: Session, company_id: uuid.UUID) -> TimesheetPeriodConfig:
        config = self.config_repo.get_for_company(db, company_id)
        if config is None:
            config = self.config_repo.create(db, company_id)
            db.commit()
        return config

    def update_config(
        self, db: Session, company_id: uuid.UUID, *, actor_user_id: uuid.UUID, **updates
    ) -> TimesheetPeriodConfig:
        config = self.get_config(db, company_id)
        period_type = updates.get("period_type")
        if period_type is not None and period_type not in VALID_PERIOD_TYPES:
            raise ValidationAppError(f"Invalid period type: {period_type}")

        before = {
            "period_type": config.period_type,
            "require_finance_approval": config.require_finance_approval,
        }
        for field, value in updates.items():
            if value is not None:
                setattr(config, field, value)
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_period_config",
            entity_id=config.id,
            action="update",
            before=before,
            after={
                "period_type": config.period_type,
                "require_finance_approval": config.require_finance_approval,
            },
        )
        db.commit()
        return self.get_config(db, company_id)

    # -- Entries (always self-scoped to the acting employee) --------------

    def _validate_project_membership(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        project = self.project_repo.get(db, company_id, project_id)
        if project is None:
            raise ValidationAppError("Project does not belong to this company")
        if not self.member_repo.is_member(db, project_id, employee_id):
            raise ValidationAppError("You are not assigned to this project")

    def list_my_entries(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[TimesheetEntry]:
        return self.entry_repo.list_for_employee_range(db, company_id, employee_id, date_from, date_to)

    def create_entry(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        *,
        project_id: uuid.UUID,
        entry_date: date,
        hours: Decimal,
        is_billable: bool,
        work_type: str,
        description: str | None,
        actor_user_id: uuid.UUID,
    ) -> TimesheetEntry:
        if work_type not in VALID_WORK_TYPES:
            raise ValidationAppError(f"Invalid work type: {work_type}")
        config = self.get_config(db, company_id)
        self._validate_project_membership(db, company_id, employee_id, project_id)

        if config.require_description and not description:
            raise ValidationAppError("A description is required for timesheet entries")
        if self.entry_repo.get_by_natural_key(db, company_id, employee_id, entry_date, project_id) is not None:
            raise ConflictError("An entry for this project and date already exists")

        day_total = self.entry_repo.sum_hours_for_day(db, company_id, employee_id, entry_date)
        if config.max_hours_per_day is not None and day_total + hours > config.max_hours_per_day:
            raise ValidationAppError(
                f"Total hours for {entry_date} would exceed the daily maximum of {config.max_hours_per_day}"
            )

        entry = self.entry_repo.create(
            db,
            company_id,
            employee_id=employee_id,
            project_id=project_id,
            entry_date=entry_date,
            hours=hours,
            is_billable=is_billable,
            work_type=work_type,
            description=description,
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_entry",
            entity_id=entry.id,
            action="create",
            after={"entry_date": str(entry_date), "hours": str(hours)},
        )
        db.commit()
        return self.entry_repo.get(db, company_id, entry.id)  # type: ignore[return-value]

    def _get_own_entry(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, entry_id: uuid.UUID
    ) -> TimesheetEntry:
        entry = self.entry_repo.get(db, company_id, entry_id)
        if entry is None or entry.employee_id != employee_id:
            raise NotFoundError("Timesheet entry not found")
        return entry

    def update_entry(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        entry_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        **updates,
    ) -> TimesheetEntry:
        entry = self._get_own_entry(db, company_id, employee_id, entry_id)
        if entry.submission is not None and entry.submission.status == "approved":
            raise ConflictError("Cannot edit an entry from an approved, locked period")

        config = self.get_config(db, company_id)
        new_project_id = updates.get("project_id")
        if new_project_id is not None:
            self._validate_project_membership(db, company_id, employee_id, new_project_id)

        new_hours = updates.get("hours")
        if new_hours is not None:
            day_total = self.entry_repo.sum_hours_for_day(
                db, company_id, employee_id, entry.entry_date, exclude_entry_id=entry.id
            )
            if config.max_hours_per_day is not None and day_total + new_hours > config.max_hours_per_day:
                raise ValidationAppError(
                    f"Total hours for {entry.entry_date} would exceed the daily maximum of {config.max_hours_per_day}"
                )

        before = {"hours": str(entry.hours), "project_id": str(entry.project_id)}
        for field, value in updates.items():
            if value is not None:
                setattr(entry, field, value)
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_entry",
            entity_id=entry.id,
            action="update",
            before=before,
            after={"hours": str(entry.hours), "project_id": str(entry.project_id)},
        )
        db.commit()
        return self.entry_repo.get(db, company_id, entry.id)  # type: ignore[return-value]

    def delete_entry(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        entry_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> None:
        entry = self._get_own_entry(db, company_id, employee_id, entry_id)
        if entry.submission is not None and entry.submission.status == "approved":
            raise ConflictError("Cannot delete an entry from an approved, locked period")
        self.entry_repo.delete(db, company_id, entry_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_entry",
            entity_id=entry_id,
            action="delete",
        )
        db.commit()

    # -- Submission / approval workflow ------------------------------------

    def submit_period(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        period_start: date,
        period_end: date,
        *,
        actor_user_id: uuid.UUID,
    ) -> TimesheetSubmission:
        if period_end < period_start:
            raise ValidationAppError("period_end must be on or after period_start")
        config = self.get_config(db, company_id)

        existing = self.submission_repo.get_by_employee_period(db, company_id, employee_id, period_start, period_end)
        if existing is not None and existing.status in OPEN_SUBMISSION_STATUSES | {"approved"}:
            raise ConflictError("This exact date range has already been submitted")

        entries = self.entry_repo.list_unsubmitted_in_range(db, company_id, employee_id, period_start, period_end)
        if not entries:
            raise ValidationAppError("There are no draft or rejected entries to submit for this date range")

        if config.min_hours_per_day is not None:
            totals: dict[date, Decimal] = {}
            for entry in entries:
                totals[entry.entry_date] = totals.get(entry.entry_date, Decimal("0")) + entry.hours
            short_days = [str(d) for d, total in totals.items() if total < config.min_hours_per_day]
            if short_days:
                raise ValidationAppError(
                    f"These days are below the minimum of {config.min_hours_per_day} hours: "
                    f"{', '.join(sorted(short_days))}"
                )

        now = datetime.now(timezone.utc)
        if existing is not None:
            submission = existing
            submission.status = "submitted"
            submission.submitted_at = now
            submission.manager_approved_by = None
            submission.manager_approved_at = None
            submission.finance_approved_by = None
            submission.finance_approved_at = None
            submission.rejected_by = None
            submission.rejected_at = None
            submission.rejection_reason = None
        else:
            submission = self.submission_repo.create(
                db, company_id,
                employee_id=employee_id,
                period_start=period_start,
                period_end=period_end,
                status="submitted",
                submitted_at=now,
            )
        for entry in entries:
            entry.submission_id = submission.id
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_submission",
            entity_id=submission.id,
            action="create",
            after={"period_start": str(period_start), "period_end": str(period_end)},
        )
        manager = submission.employee.manager
        if manager is not None:
            notification_service.notify(
                db,
                company_id,
                manager.user_id,
                type="timesheet.submitted",
                title=f"{submission.employee.full_name} submitted a timesheet",
                body=f"{period_start.isoformat()} – {period_end.isoformat()}",
                entity_type="timesheet_submission",
                entity_id=submission.id,
            )
        db.commit()
        return self.submission_repo.get(db, company_id, submission.id)  # type: ignore[return-value]

    def get_submission(self, db: Session, company_id: uuid.UUID, submission_id: uuid.UUID) -> TimesheetSubmission:
        submission = self.submission_repo.get(db, company_id, submission_id)
        if submission is None:
            raise NotFoundError("Timesheet submission not found")
        return submission

    def list_my_submissions(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, bucket: str | None = None
    ) -> list[TimesheetSubmission]:
        statuses = BUCKET_STATUSES.get(bucket) if bucket else None
        return self.submission_repo.list_for_employee(db, company_id, employee_id, statuses=statuses)

    def list_submissions(
        self, db: Session, company_id: uuid.UUID, *, bucket: str | None, page: int, page_size: int
    ) -> Page[TimesheetSubmission]:
        statuses = BUCKET_STATUSES.get(bucket) if bucket else None
        skip = (page - 1) * page_size
        items, total = self.submission_repo.search(db, company_id, statuses=statuses, skip=skip, limit=page_size)
        return Page(items=items, total=total, page=page, page_size=page_size)

    def approve_submission(
        self, db: Session, company_id: uuid.UUID, submission_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> TimesheetSubmission:
        submission = self.get_submission(db, company_id, submission_id)
        config = self.get_config(db, company_id)
        now = datetime.now(timezone.utc)

        if submission.status == "submitted":
            submission.manager_approved_by = actor_user_id
            submission.manager_approved_at = now
            submission.status = "manager_approved" if config.require_finance_approval else "approved"
        elif submission.status == "manager_approved" and config.require_finance_approval:
            submission.finance_approved_by = actor_user_id
            submission.finance_approved_at = now
            submission.status = "approved"
        else:
            raise ConflictError("This submission is not awaiting approval")
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_submission",
            entity_id=submission.id,
            action="update",
            after={"status": submission.status},
        )
        if submission.status == "approved":
            notification_service.notify(
                db,
                company_id,
                submission.employee.user_id,
                type="timesheet.approved",
                title="Your timesheet was approved",
                body=f"{submission.period_start.isoformat()} – {submission.period_end.isoformat()}",
                entity_type="timesheet_submission",
                entity_id=submission.id,
            )
        db.commit()
        return self.get_submission(db, company_id, submission_id)

    def reject_submission(
        self, db: Session, company_id: uuid.UUID, submission_id: uuid.UUID, *, reason: str, actor_user_id: uuid.UUID
    ) -> TimesheetSubmission:
        submission = self.get_submission(db, company_id, submission_id)
        if submission.status not in OPEN_SUBMISSION_STATUSES:
            raise ConflictError("This submission is not awaiting approval")

        before = {"status": submission.status}
        submission.status = "rejected"
        submission.rejected_by = actor_user_id
        submission.rejected_at = datetime.now(timezone.utc)
        submission.rejection_reason = reason
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_submission",
            entity_id=submission.id,
            action="update",
            before=before,
            after={"status": "rejected", "reason": reason},
        )
        notification_service.notify(
            db,
            company_id,
            submission.employee.user_id,
            type="timesheet.rejected",
            title="Your timesheet was rejected",
            body=reason,
            entity_type="timesheet_submission",
            entity_id=submission.id,
        )
        db.commit()
        return self.get_submission(db, company_id, submission_id)

    def bulk_approve(
        self, db: Session, company_id: uuid.UUID, submission_ids: list[uuid.UUID], *, actor_user_id: uuid.UUID
    ) -> dict:
        approved: list[uuid.UUID] = []
        failed: list[dict] = []
        for submission_id in submission_ids:
            try:
                self.approve_submission(db, company_id, submission_id, actor_user_id=actor_user_id)
                approved.append(submission_id)
            except (NotFoundError, ConflictError) as exc:
                failed.append({"id": submission_id, "reason": exc.message})
        return {"approved": approved, "failed": failed}

    def reopen_submission(
        self, db: Session, company_id: uuid.UUID, submission_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> TimesheetSubmission:
        submission = self.get_submission(db, company_id, submission_id)
        if submission.status != "approved":
            raise ValidationAppError("Only approved submissions can be reopened")

        submission.status = "submitted"
        submission.manager_approved_by = None
        submission.manager_approved_at = None
        submission.finance_approved_by = None
        submission.finance_approved_at = None
        db.flush()

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="timesheet_submission",
            entity_id=submission.id,
            action="update",
            before={"status": "approved"},
            after={"status": "submitted"},
        )
        db.commit()
        return self.get_submission(db, company_id, submission_id)

    # -- Dashboard & export -------------------------------------------------

    def get_dashboard(
        self, db: Session, company_id: uuid.UUID, *, date_from: date | None, date_to: date | None
    ) -> dict:
        counts = self.submission_repo.counts_by_status(db, company_id)
        pending = counts.get("submitted", 0) + counts.get("manager_approved", 0)
        rejected = counts.get("rejected", 0)
        late = self.submission_repo.late_count(db, company_id)

        billable_hours, total_hours = self.entry_repo.billable_totals(
            db, company_id, date_from=date_from, date_to=date_to
        )
        billable_percentage = float(billable_hours / total_hours * 100) if total_hours > 0 else 0.0

        hours_by_project = [
            {"id": pid, "name": name, "hours": hours}
            for pid, name, hours in self.entry_repo.hours_by_project(
                db, company_id, date_from=date_from, date_to=date_to
            )
        ]
        hours_by_employee = [
            {"id": eid, "name": f"{first} {last}", "hours": hours}
            for eid, first, last, hours in self.entry_repo.hours_by_employee(
                db, company_id, date_from=date_from, date_to=date_to
            )
        ]

        return {
            "pending_count": pending,
            "rejected_count": rejected,
            "late_count": late,
            "billable_percentage": round(billable_percentage, 1),
            "hours_by_project": hours_by_project,
            "hours_by_employee": hours_by_employee,
        }

    def report_rows(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        employee_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        location: str | None = None,
    ) -> tuple[list[str], list[list]]:
        entries = self.entry_repo.search(
            db,
            company_id,
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
            project_id=project_id,
            location=location,
        )
        header = ["Employee", "Location", "Project", "Date", "Hours", "Billable", "Work Type", "Status", "Description"]
        rows = [
            [
                entry.employee.full_name,
                entry.employee.location or "",
                entry.project.name,
                entry.entry_date.isoformat(),
                str(entry.hours),
                "Yes" if entry.is_billable else "No",
                entry.work_type,
                entry.status,
                entry.description or "",
            ]
            for entry in entries
        ]
        return header, rows

    def export_csv(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
        project_id: uuid.UUID | None,
        location: str | None = None,
    ) -> str:
        header, rows = self.report_rows(
            db,
            company_id,
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
            project_id=project_id,
            location=location,
        )
        return build_csv(header, rows)


timesheet_service = TimesheetService()
