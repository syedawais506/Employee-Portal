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
from app.services.notification_service import notification_service
from app.tasks.celery_app import celery_app

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
