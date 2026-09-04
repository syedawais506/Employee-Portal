from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.db.rls import set_tenant_context
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.employee import Employee
from app.models.onboarding import EmployeeDocument
from app.models.project import Project, ProjectMember
from app.models.timesheet import TimesheetPeriodConfig, TimesheetSubmission
from app.services.notification_service import notification_service
from app.tasks.celery_app import celery_app
from app.tasks.email_tasks import send_timesheet_reminder_email

# Notify exactly once, N days before expiry, rather than on every day within a
# lookahead window — avoids re-notifying the same document daily until it expires.
DOCUMENT_EXPIRY_LEAD_DAYS = 7


@celery_app.task(name="run_daily_digest")
def run_daily_digest() -> None:
    db = SessionLocal()
    try:
        today = date.today()
        company_ids = (
            db.execute(select(Company.id).where(Company.status == "active", Company.deleted_at.is_(None)))
            .scalars()
            .all()
        )
        for company_id in company_ids:
            set_tenant_context(db, str(company_id))
            _notify_anniversaries(db, company_id, today)
            _notify_expiring_documents(db, company_id, today)
            _notify_stale_timesheets(db, company_id, today)
            db.commit()
    finally:
        db.close()


def _notify_anniversaries(db: Session, company_id: uuid.UUID, today: date) -> None:
    stmt = select(Employee).where(
        Employee.company_id == company_id,
        Employee.status == "active",
        Employee.joining_date.is_not(None),
        extract("month", Employee.joining_date) == today.month,
        extract("day", Employee.joining_date) == today.day,
        extract("year", Employee.joining_date) < today.year,
    )
    for employee in db.execute(stmt).scalars().all():
        if employee.joining_date is None:
            continue
        years = today.year - employee.joining_date.year
        notification_service.notify(
            db,
            company_id,
            employee.user_id,
            type="employee.anniversary",
            title=f"Happy {years}-year work anniversary, {employee.first_name}!",
            body=f"Today marks {years} year{'s' if years != 1 else ''} since you joined.",
            entity_type="employee",
            entity_id=employee.id,
        )


def _notify_expiring_documents(db: Session, company_id: uuid.UUID, today: date) -> None:
    target_date = today + timedelta(days=DOCUMENT_EXPIRY_LEAD_DAYS)
    stmt = select(EmployeeDocument).where(
        EmployeeDocument.company_id == company_id,
        EmployeeDocument.expiry_date == target_date,
    )
    for document in db.execute(stmt).scalars().all():
        employee = db.get(Employee, document.employee_id)
        employee_name = employee.full_name if employee else "An employee"
        notification_service.notify_users_with_permission(
            db,
            company_id,
            module="onboarding",
            action="review",
            type="document.expiring",
            title=f"{document.original_filename} for {employee_name} expires in {DOCUMENT_EXPIRY_LEAD_DAYS} days",
            body=f"Expiry date: {target_date.isoformat()}",
            entity_type="employee_document",
            entity_id=document.id,
        )


def _notify_stale_timesheets(db: Session, company_id: uuid.UUID, today: date) -> None:
    """Unlike the other two digest checks, this one is intentionally NOT
    exactly-once: it re-fires every day a submission stays stale past the
    configured threshold, so the reminder keeps nagging until the employee
    actually submits again — per the admin-configurable "remind until
    resolved" behavior this was built for, opt-in via
    TimesheetPeriodConfig.reminder_enabled (off by default).
    """
    config = db.execute(
        select(TimesheetPeriodConfig).where(TimesheetPeriodConfig.company_id == company_id)
    ).scalar_one_or_none()
    if config is None or not config.reminder_enabled:
        return

    member_employee_ids = set(
        db.execute(
            select(ProjectMember.employee_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(Project.company_id == company_id)
        )
        .scalars()
        .all()
    )
    if not member_employee_ids:
        return

    stmt = select(Employee).where(Employee.company_id == company_id, Employee.status == "active")
    for employee in db.execute(stmt).scalars().all():
        if employee.id not in member_employee_ids:
            continue  # can't log time against any project, so nothing to remind about

        last_submission = db.execute(
            select(TimesheetSubmission)
            .where(TimesheetSubmission.company_id == company_id, TimesheetSubmission.employee_id == employee.id)
            .order_by(TimesheetSubmission.submitted_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if last_submission is not None:
            reference_date = last_submission.submitted_at.date()
        elif employee.joining_date is not None:
            reference_date = employee.joining_date
        else:
            continue  # nothing to measure staleness against

        days_stale = (today - reference_date).days
        if days_stale < config.reminder_after_days:
            continue

        if last_submission is not None:
            body = (
                f"It's been {days_stale} day(s) since your last timesheet submission "
                f"({last_submission.period_start.isoformat()} – {last_submission.period_end.isoformat()})."
            )
        else:
            body = f"You haven't submitted a timesheet yet — it's been {days_stale} day(s) since you joined."

        notification_service.notify(
            db,
            company_id,
            employee.user_id,
            type="timesheet.reminder",
            title="Please submit your timesheet",
            body=body,
            entity_type="employee",
            entity_id=employee.id,
        )
        send_timesheet_reminder_email.delay(employee.email, employee.first_name, days_stale)
