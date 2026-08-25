from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationAppError
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType
from app.repositories.company_repository import CompanyRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.leave_repository import (
    HolidayRepository,
    LeaveBalanceRepository,
    LeaveRequestRepository,
    LeaveTypeRepository,
)
from app.schemas.common import Page
from app.services.audit_service import audit_service
from app.utils.csv_export import build_csv
from app.utils.storage import upload_document

OPEN_STATUSES = ("pending", "manager_approved", "approved")


def compute_business_days(start: date, end: date, holidays: set[date]) -> int:
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            count += 1
        current += timedelta(days=1)
    return count


class LeaveService:
    def __init__(self) -> None:
        self.type_repo = LeaveTypeRepository()
        self.holiday_repo = HolidayRepository()
        self.balance_repo = LeaveBalanceRepository()
        self.request_repo = LeaveRequestRepository()
        self.employee_repo = EmployeeRepository()
        self.company_repo = CompanyRepository()

    # -- Leave types ---------------------------------------------------

    def list_leave_types(self, db: Session, company_id: uuid.UUID) -> list[LeaveType]:
        return self.type_repo.list_all(db, company_id)

    def get_leave_type(self, db: Session, company_id: uuid.UUID, leave_type_id: uuid.UUID) -> LeaveType:
        leave_type = self.type_repo.get(db, company_id, leave_type_id)
        if leave_type is None:
            raise NotFoundError("Leave type not found")
        return leave_type

    def create_leave_type(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str,
        is_paid: bool,
        annual_quota_days: int | None,
        max_carry_forward_days: int,
        requires_attachment: bool,
        actor_user_id: uuid.UUID,
    ) -> LeaveType:
        if self.type_repo.get_by_name(db, company_id, name) is not None:
            raise ConflictError("A leave type with this name already exists")
        leave_type = self.type_repo.create(
            db,
            company_id,
            name=name,
            is_paid=is_paid,
            annual_quota_days=annual_quota_days,
            max_carry_forward_days=max_carry_forward_days,
            requires_attachment=requires_attachment,
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_type",
            entity_id=leave_type.id,
            action="create",
            after={"name": name},
        )
        db.commit()
        return leave_type

    def update_leave_type(
        self, db: Session, company_id: uuid.UUID, leave_type_id: uuid.UUID, *, actor_user_id: uuid.UUID, **updates
    ) -> LeaveType:
        leave_type = self.get_leave_type(db, company_id, leave_type_id)
        before = {"name": leave_type.name}
        for field, value in updates.items():
            if value is not None:
                setattr(leave_type, field, value)
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_type",
            entity_id=leave_type.id,
            action="update",
            before=before,
            after={"name": leave_type.name},
        )
        db.commit()
        return leave_type

    def delete_leave_type(
        self, db: Session, company_id: uuid.UUID, leave_type_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        leave_type = self.get_leave_type(db, company_id, leave_type_id)
        in_use = db.execute(
            select(LeaveRequest.id).where(LeaveRequest.leave_type_id == leave_type_id).limit(1)
        ).first()
        if in_use is not None:
            raise ConflictError("Cannot delete a leave type that has requests logged against it")
        self.type_repo.delete(db, company_id, leave_type_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_type",
            entity_id=leave_type_id,
            action="delete",
            before={"name": leave_type.name},
        )
        db.commit()

    # -- Holidays --------------------------------------------------------

    def list_holidays(self, db: Session, company_id: uuid.UUID, *, year: int | None = None) -> list:
        return self.holiday_repo.list_all(db, company_id, year=year)

    def create_holiday(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date: date,
        name: str,
        location: str | None,
        actor_user_id: uuid.UUID,
    ):
        if self.holiday_repo.get_by_date(db, company_id, date, location) is not None:
            raise ConflictError("A holiday is already defined for this date and location")
        holiday = self.holiday_repo.create(db, company_id, date=date, name=name, location=location)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="holiday",
            entity_id=holiday.id,
            action="create",
            after={"date": str(date), "name": name, "location": location},
        )
        db.commit()
        return holiday

    def update_holiday(
        self,
        db: Session,
        company_id: uuid.UUID,
        holiday_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        clear_location: bool = False,
        **updates,
    ):
        holiday = self.holiday_repo.get(db, company_id, holiday_id)
        if holiday is None:
            raise NotFoundError("Holiday not found")
        for field, value in updates.items():
            if value is not None:
                setattr(holiday, field, value)
        if clear_location:
            holiday.location = None
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="holiday",
            entity_id=holiday.id,
            action="update",
            after={"name": holiday.name},
        )
        db.commit()
        return holiday

    def delete_holiday(
        self, db: Session, company_id: uuid.UUID, holiday_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        holiday = self.holiday_repo.get(db, company_id, holiday_id)
        if holiday is None:
            raise NotFoundError("Holiday not found")
        self.holiday_repo.delete(db, company_id, holiday_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="holiday",
            entity_id=holiday_id,
            action="delete",
            before={"name": holiday.name},
        )
        db.commit()

    # -- Settings ---------------------------------------------------------

    def get_settings(self, db: Session, company_id: uuid.UUID) -> bool:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company.require_hr_leave_approval

    def update_settings(
        self, db: Session, company_id: uuid.UUID, *, require_hr_leave_approval: bool, actor_user_id: uuid.UUID
    ) -> bool:
        company = self.company_repo.get(db, company_id)
        if company is None:
            raise NotFoundError("Company not found")
        before = company.require_hr_leave_approval
        company.require_hr_leave_approval = require_hr_leave_approval
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_settings",
            entity_id=company_id,
            action="update",
            before={"require_hr_leave_approval": before},
            after={"require_hr_leave_approval": require_hr_leave_approval},
        )
        db.commit()
        return company.require_hr_leave_approval

    # -- Balances ----------------------------------------------------------

    def _get_or_create_balance(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, leave_type: LeaveType, year: int
    ) -> LeaveBalance:
        existing = self.balance_repo.get_for(db, company_id, employee_id, leave_type.id, year)
        if existing is not None:
            return existing
        if leave_type.annual_quota_days is not None:
            granted = Decimal(leave_type.annual_quota_days)
        else:
            granted = Decimal("0")
        balance = self.balance_repo.create(
            db,
            company_id,
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            year=year,
            granted=granted,
            carried_forward=Decimal("0"),
            adjustment=Decimal("0"),
        )
        db.flush()
        return balance

    def _balance_summary(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, leave_type: LeaveType, year: int
    ) -> dict:
        used = self.request_repo.sum_days_for_year(
            db, company_id, employee_id, leave_type.id, year, statuses=("approved",)
        )
        if leave_type.annual_quota_days is None:
            return {
                "leave_type_id": leave_type.id,
                "leave_type_name": leave_type.name,
                "year": year,
                "granted": None,
                "carried_forward": "0",
                "adjustment": "0",
                "used": str(used),
                "available": None,
            }
        balance = self._get_or_create_balance(db, company_id, employee_id, leave_type, year)
        available = balance.granted + balance.carried_forward + balance.adjustment - Decimal(used)
        return {
            "leave_type_id": leave_type.id,
            "leave_type_name": leave_type.name,
            "year": year,
            "granted": str(balance.granted),
            "carried_forward": str(balance.carried_forward),
            "adjustment": str(balance.adjustment),
            "used": str(used),
            "available": str(available),
        }

    def list_my_balances(self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, year: int) -> list[dict]:
        leave_types = self.type_repo.list_all(db, company_id)
        return [self._balance_summary(db, company_id, employee_id, lt, year) for lt in leave_types]

    def list_company_balances(
        self, db: Session, company_id: uuid.UUID, *, year: int, employee_id: uuid.UUID | None
    ) -> list[dict]:
        if employee_id is not None:
            return self.list_my_balances(db, company_id, employee_id, year)
        leave_types = self.type_repo.list_all(db, company_id)
        employees = self.employee_repo.list(db, company_id, limit=1000)[0]
        summaries = []
        for emp in employees:
            for lt in leave_types:
                summary = self._balance_summary(db, company_id, emp.id, lt, year)
                summaries.append({**summary, "employee_id": emp.id, "employee_name": emp.full_name})
        return summaries

    def _held_days(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, leave_type_id: uuid.UUID, year: int
    ) -> int:
        return self.request_repo.sum_days_for_year(
            db, company_id, employee_id, leave_type_id, year, statuses=OPEN_STATUSES
        )

    # -- Requests ------------------------------------------------------------

    def _resolve_target_employee(
        self,
        db: Session,
        company_id: uuid.UUID,
        caller_employee_id: uuid.UUID,
        requested_employee_id: uuid.UUID | None,
        can_act_for_others: bool,
    ) -> uuid.UUID:
        if requested_employee_id is None or requested_employee_id == caller_employee_id:
            return caller_employee_id
        if not can_act_for_others:
            raise PermissionDeniedError("You cannot file leave on behalf of another employee")
        if self.employee_repo.get(db, company_id, requested_employee_id) is None:
            raise ValidationAppError("Employee does not belong to this company")
        return requested_employee_id

    def create_request(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        caller_employee_id: uuid.UUID,
        requested_employee_id: uuid.UUID | None,
        can_act_for_others: bool,
        leave_type_id: uuid.UUID,
        start_date: date,
        end_date: date,
        reason: str | None,
        attachment: tuple[bytes, str, str] | None,
        actor_user_id: uuid.UUID,
    ) -> LeaveRequest:
        if end_date < start_date:
            raise ValidationAppError("end_date must be on or after start_date")
        employee_id = self._resolve_target_employee(
            db, company_id, caller_employee_id, requested_employee_id, can_act_for_others
        )
        employee = self.employee_repo.get(db, company_id, employee_id)
        leave_type = self.get_leave_type(db, company_id, leave_type_id)

        if leave_type.requires_attachment and attachment is None:
            raise ValidationAppError(f"{leave_type.name} requires a supporting document to be attached")

        holidays = self.holiday_repo.list_dates_in_range(
            db, company_id, start_date, end_date, location=employee.location if employee else None
        )
        days_count = compute_business_days(start_date, end_date, holidays)
        if days_count == 0:
            raise ValidationAppError("The selected range has no working days")

        if self.request_repo.list_overlapping(db, company_id, employee_id, start_date, end_date):
            raise ConflictError("This employee already has a leave request overlapping these dates")

        if leave_type.annual_quota_days is not None:
            year = start_date.year
            balance = self._get_or_create_balance(db, company_id, employee_id, leave_type, year)
            held = self._held_days(db, company_id, employee_id, leave_type_id, year)
            available = balance.granted + balance.carried_forward + balance.adjustment - Decimal(held)
            if Decimal(days_count) > available:
                raise ValidationAppError(
                    f"This request needs {days_count} day(s) but only {available} are available"
                )

        attachment_file_key = None
        attachment_original_filename = None
        if attachment is not None:
            content, filename, content_type = attachment
            attachment_file_key = (
                f"{company_id}/employees/{employee_id}/leave-requests/{uuid.uuid4().hex}_{filename}"
            )
            upload_document(key=attachment_file_key, content=content, content_type=content_type)
            attachment_original_filename = filename

        request = self.request_repo.create(
            db,
            company_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            days_count=days_count,
            reason=reason,
            attachment_file_key=attachment_file_key,
            attachment_original_filename=attachment_original_filename,
            status="pending",
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_request",
            entity_id=request.id,
            action="create",
            after={"start_date": str(start_date), "end_date": str(end_date), "days_count": days_count},
        )
        db.commit()
        return self.get_request(db, company_id, request.id)

    def get_request(self, db: Session, company_id: uuid.UUID, request_id: uuid.UUID) -> LeaveRequest:
        request = self.request_repo.get(db, company_id, request_id)
        if request is None:
            raise NotFoundError("Leave request not found")
        return request

    def _authorize_touch(
        self, request: LeaveRequest, caller_employee_id: uuid.UUID, can_act_for_others: bool
    ) -> None:
        if request.employee_id != caller_employee_id and not can_act_for_others:
            raise NotFoundError("Leave request not found")

    def cancel_request(
        self,
        db: Session,
        company_id: uuid.UUID,
        request_id: uuid.UUID,
        *,
        caller_employee_id: uuid.UUID,
        can_act_for_others: bool,
        actor_user_id: uuid.UUID,
    ) -> LeaveRequest:
        request = self.get_request(db, company_id, request_id)
        self._authorize_touch(request, caller_employee_id, can_act_for_others)
        if request.status not in OPEN_STATUSES:
            raise ConflictError("This request can no longer be cancelled")
        before = {"status": request.status}
        request.status = "cancelled"
        request.cancelled_at = datetime.now(timezone.utc)
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_request",
            entity_id=request.id,
            action="update",
            before=before,
            after={"status": "cancelled"},
        )
        db.commit()
        return self.get_request(db, company_id, request_id)

    def delete_request(
        self, db: Session, company_id: uuid.UUID, request_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        request = self.get_request(db, company_id, request_id)
        self.request_repo.delete(db, company_id, request_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_request",
            entity_id=request_id,
            action="delete",
            before={"start_date": str(request.start_date), "end_date": str(request.end_date)},
        )
        db.commit()

    def list_my_requests(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, status: str | None
    ) -> list[LeaveRequest]:
        return self.request_repo.list_for_employee(db, company_id, employee_id, status=status)

    def list_requests(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        employee_id: uuid.UUID | None,
        leave_type_id: uuid.UUID | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> Page[LeaveRequest]:
        skip = (page - 1) * page_size
        items, total = self.request_repo.search(
            db,
            company_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            status=status,
            skip=skip,
            limit=page_size,
        )
        return Page(items=items, total=total, page=page, page_size=page_size)

    def approve_request(
        self, db: Session, company_id: uuid.UUID, request_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> LeaveRequest:
        request = self.get_request(db, company_id, request_id)
        require_hr = self.get_settings(db, company_id)
        now = datetime.now(timezone.utc)

        if request.status == "pending":
            request.manager_approved_by = actor_user_id
            request.manager_approved_at = now
            request.status = "manager_approved" if require_hr else "approved"
        elif request.status == "manager_approved" and require_hr:
            request.hr_approved_by = actor_user_id
            request.hr_approved_at = now
            request.status = "approved"
        else:
            raise ConflictError("This request is not awaiting approval")
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_request",
            entity_id=request.id,
            action="update",
            after={"status": request.status},
        )
        db.commit()
        return self.get_request(db, company_id, request_id)

    def reject_request(
        self, db: Session, company_id: uuid.UUID, request_id: uuid.UUID, *, reason: str, actor_user_id: uuid.UUID
    ) -> LeaveRequest:
        request = self.get_request(db, company_id, request_id)
        if request.status not in ("pending", "manager_approved"):
            raise ConflictError("This request is not awaiting approval")
        before = {"status": request.status}
        request.status = "rejected"
        request.rejected_by = actor_user_id
        request.rejected_at = datetime.now(timezone.utc)
        request.rejection_reason = reason
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_request",
            entity_id=request.id,
            action="update",
            before=before,
            after={"status": "rejected", "reason": reason},
        )
        db.commit()
        return self.get_request(db, company_id, request_id)

    # -- Carry forward --------------------------------------------------------

    def run_carry_forward(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        from_year: int,
        employee_id: uuid.UUID | None,
        actor_user_id: uuid.UUID,
    ) -> dict:
        to_year = from_year + 1
        leave_types = [lt for lt in self.type_repo.list_all(db, company_id) if lt.annual_quota_days is not None]
        if employee_id is not None:
            employee = self.employee_repo.get(db, company_id, employee_id)
            if employee is None:
                raise ValidationAppError("Employee does not belong to this company")
            employees = [employee]
        else:
            employees = self.employee_repo.list(db, company_id, limit=1000)[0]

        carried_count = 0
        for employee in employees:
            for leave_type in leave_types:
                old_balance = self.balance_repo.get_for(db, company_id, employee.id, leave_type.id, from_year)
                if old_balance is None:
                    continue
                used = self.request_repo.sum_days_for_year(
                    db, company_id, employee.id, leave_type.id, from_year, statuses=("approved",)
                )
                remaining = (
                    old_balance.granted + old_balance.carried_forward + old_balance.adjustment - Decimal(used)
                )
                carry_amount = max(Decimal("0"), min(remaining, Decimal(leave_type.max_carry_forward_days)))
                new_balance = self._get_or_create_balance(db, company_id, employee.id, leave_type, to_year)
                new_balance.carried_forward = carry_amount
                if carry_amount > 0:
                    carried_count += 1
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="leave_carry_forward",
            entity_id=company_id,
            action="create",
            after={"from_year": from_year, "to_year": to_year, "balances_updated": carried_count},
        )
        db.commit()
        return {"from_year": from_year, "to_year": to_year, "balances_updated": carried_count}

    # -- Dashboard & export -----------------------------------------------------

    def get_dashboard(self, db: Session, company_id: uuid.UUID) -> dict:
        return {
            "pending_count": self.request_repo.count_pending(db, company_id),
            "on_leave_today_count": self.request_repo.count_on_leave_on(db, company_id, date.today()),
        }

    def export_csv(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        employee_id: uuid.UUID | None,
        leave_type_id: uuid.UUID | None,
        status: str | None,
    ) -> str:
        requests = self.request_repo.list_for_export(
            db,
            company_id,
            date_from=date_from,
            date_to=date_to,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            status=status,
        )
        header = ["Employee", "Leave Type", "Start Date", "End Date", "Days", "Status", "Reason"]
        rows = [
            [
                r.employee.full_name,
                r.leave_type.name,
                r.start_date.isoformat(),
                r.end_date.isoformat(),
                r.days_count,
                r.status,
                r.reason or "",
            ]
            for r in requests
        ]
        return build_csv(header, rows)


leave_service = LeaveService()
