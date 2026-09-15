from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.core.redis_client import get_redis
from app.db.rls import set_tenant_context
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.employee import Employee
from app.models.onboarding import EmployeeDocument
from app.models.project import Project, ProjectMember
from app.models.timesheet import TimesheetPeriodConfig, TimesheetReminderRule, TimesheetSubmission
from app.services.notification_service import notification_service
from app.tasks.celery_app import celery_app
from app.tasks.email_tasks import send_timesheet_reminder_email

# Notify exactly once, N days before expiry, rather than on every day within a
# lookahead window — avoids re-notifying the same document daily until it expires.
DOCUMENT_EXPIRY_LEAD_DAYS = 7

# 25h, not 24h: a small buffer past one calendar day so a slightly-delayed
# retry can't slip past the lock right at the boundary.
DAILY_DIGEST_LOCK_TTL_SECONDS = 25 * 60 * 60


@celery_app.task(name="run_daily_digest")
def run_daily_digest() -> None:
    today = date.today()
    # celery-beat has nothing today stopping it from being scaled to 2+
    # replicas, which would otherwise fire this same scheduled job twice and
    # double-send every anniversary/expiry/reminder notification and email
    # for the day. This lock makes a second concurrent (or retried) run for
    # the same calendar day a safe, silent no-op instead.
    lock_key = f"daily_digest_lock:{today.isoformat()}"
    if not get_redis().set(lock_key, "1", nx=True, ex=DAILY_DIGEST_LOCK_TTL_SECONDS):
        return

    db = SessionLocal()
    try:
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


def _last_completed_week(today: date, week_start_day: int) -> tuple[date, date]:
    """The most recent fully-elapsed week, using the company's configured
    `week_start_day` (0=Monday..6=Sunday) — same convention as
    TimesheetPeriodConfig.week_start_day.
    """
    current_week_start = today - timedelta(days=(today.weekday() - week_start_day) % 7)
    last_week_start = current_week_start - timedelta(days=7)
    last_week_end = current_week_start - timedelta(days=1)
    return last_week_start, last_week_end


def _last_completed_month(today: date) -> tuple[date, date]:
    """The most recent fully-elapsed calendar month — always the month
    before whatever month `today` falls in, since the current month is
    never "complete" until it ends.
    """
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start, last_month_end


def _notify_stale_timesheets(db: Session, company_id: uuid.UUID, today: date) -> None:
    """Reminders are per-location (TimesheetReminderRule, location=None is the
    default/fallback rule — same nullable convention as HolidayCalendar) and
    calendar-anchored: "weekly" checks whether the most recently fully-elapsed
    week has a submission overlapping it, "monthly" the most recently
    fully-elapsed calendar month. Unlike the other two digest checks, this one
    is intentionally NOT exactly-once — the digest re-evaluates the same
    (still-uncovered) period every day past `grace_days`, so it keeps nagging
    until a submission overlapping that period actually gets created.
    """
    rules = db.execute(
        select(TimesheetReminderRule).where(TimesheetReminderRule.company_id == company_id)
    ).scalars().all()
    if not rules:
        return
    rules_by_location = {rule.location: rule for rule in rules}

    config = db.execute(
        select(TimesheetPeriodConfig).where(TimesheetPeriodConfig.company_id == company_id)
    ).scalar_one_or_none()
    week_start_day = config.week_start_day if config is not None else 0

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

        rule = rules_by_location.get(employee.location) or rules_by_location.get(None)
        if rule is None or not rule.enabled:
            continue

        if rule.cadence == "weekly":
            period_start, period_end = _last_completed_week(today, week_start_day)
            period_label = f"the week of {period_start.isoformat()} – {period_end.isoformat()}"
        else:
            period_start, period_end = _last_completed_month(today)
            period_label = period_end.strftime("%B %Y")

        if employee.joining_date is not None:
            period_start = max(period_start, employee.joining_date)
        if period_start > period_end:
            continue  # employee wasn't employed yet during this period

        nag_start = period_end + timedelta(days=1 + rule.grace_days)
        if today < nag_start:
            continue

        overlapping_submission = db.execute(
            select(TimesheetSubmission)
            .where(
                TimesheetSubmission.company_id == company_id,
                TimesheetSubmission.employee_id == employee.id,
                TimesheetSubmission.period_start <= period_end,
                TimesheetSubmission.period_end >= period_start,
            )
            .limit(1)
        ).scalar_one_or_none()
        if overlapping_submission is not None:
            continue  # already covered — nothing to nag about for this period

        notification_service.notify(
            db,
            company_id,
            employee.user_id,
            type="timesheet.reminder",
            title="Please submit your timesheet",
            body=f"You haven't submitted a timesheet for {period_label} yet.",
            entity_type="employee",
            entity_id=employee.id,
        )
        send_timesheet_reminder_email.delay(employee.email, employee.first_name, period_label)
