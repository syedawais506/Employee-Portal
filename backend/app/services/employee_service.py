from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.security import hash_password
from app.models.employee import Employee
from app.repositories.company_repository import CompanyRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.services.audit_service import audit_service
from app.services.onboarding_service import onboarding_service
from app.utils.csv_export import build_csv


class EmployeeService:
    def __init__(self) -> None:
        self.employee_repo = EmployeeRepository()
        self.department_repo = DepartmentRepository()
        self.user_repo = UserRepository()
        self.company_repo = CompanyRepository()

    def search_employees(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None,
        department_id: uuid.UUID | None,
        status: str | None,
        manager_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> Page[Employee]:
        skip = (page - 1) * page_size
        items, total = self.employee_repo.search(
            db,
            company_id,
            search=search,
            department_id=department_id,
            status=status,
            manager_id=manager_id,
            skip=skip,
            limit=page_size,
        )
        return Page(items=items, total=total, page=page, page_size=page_size)

    def get_employee(self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID) -> Employee:
        employee = self.employee_repo.get(db, company_id, employee_id)
        if employee is None:
            raise NotFoundError("Employee not found")
        return employee

    def get_employee_by_user_id(self, db: Session, user_id: uuid.UUID) -> Employee:
        employee = self.employee_repo.get_by_user_id(db, user_id)
        if employee is None:
            raise NotFoundError("Employee profile not found")
        return employee

    def _validate_same_company(
        self, db: Session, company_id: uuid.UUID, department_id: uuid.UUID | None, manager_id: uuid.UUID | None
    ) -> None:
        if department_id is not None and self.department_repo.get(db, company_id, department_id) is None:
            raise ValidationAppError("Department does not belong to this company")
        if manager_id is not None and self.employee_repo.get(db, company_id, manager_id) is None:
            raise ValidationAppError("Manager does not belong to this company")

    def create_employee(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        email: str,
        first_name: str,
        last_name: str,
        phone: str | None,
        department_id: uuid.UUID | None,
        designation: str | None,
        manager_id: uuid.UUID | None,
        employment_type: str,
        location: str | None,
        joining_date: date | None,
        role_ids: list[uuid.UUID],
        actor_user_id: uuid.UUID | None,
        birth_date: date | None = None,
    ) -> Employee:
        if self.user_repo.get_by_email(db, email) is not None:
            raise ConflictError("A user with this email already exists")
        self._validate_same_company(db, company_id, department_id, manager_id)

        company = self.company_repo.get(db, company_id)
        prefix = company.slug.upper()[:6] if company else "EMP"

        user = self.user_repo.create(
            db,
            company_id=company_id,
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            is_active=False,  # gated until Admin completes onboarding approval
            is_verified=False,
        )
        if role_ids:
            self.user_repo.assign_roles(db, user.id, role_ids)

        employee = self.employee_repo.create(
            db,
            company_id,
            user_id=user.id,
            employee_code=self.employee_repo.next_employee_code(db, company_id, prefix),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            department_id=department_id,
            designation=designation,
            manager_id=manager_id,
            employment_type=employment_type,
            location=location,
            joining_date=joining_date,
            birth_date=birth_date,
            status="active",
            onboarding_status="invited",
        )

        onboarding_service.create_invite(db, company_id=company_id, employee=employee)

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="employee",
            entity_id=employee.id,
            action="create",
            after={"email": email, "employee_code": employee.employee_code},
        )
        db.commit()
        return self.get_employee(db, company_id, employee.id)

    def update_employee(
        self,
        db: Session,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID | None,
        **updates,
    ) -> Employee:
        employee = self.get_employee(db, company_id, employee_id)
        department_id = updates.get("department_id")
        manager_id = updates.get("manager_id")
        if manager_id == employee_id:
            raise ValidationAppError("An employee cannot be their own manager")
        self._validate_same_company(db, company_id, department_id, manager_id)

        before = {"status": employee.status, "designation": employee.designation}
        for field, value in updates.items():
            if value is not None:
                setattr(employee, field, value)

        deactivating = updates.get("status") == "exited"
        db.flush()
        if deactivating:
            employee.user.is_active = False

        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="employee",
            entity_id=employee.id,
            action="update",
            before=before,
            after={"status": employee.status, "designation": employee.designation},
        )
        db.commit()
        return self.get_employee(db, company_id, employee_id)

    def update_self(self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, phone: str | None) -> Employee:
        employee = self.get_employee(db, company_id, employee_id)
        if phone is not None:
            employee.phone = phone
        db.commit()
        return self.get_employee(db, company_id, employee_id)

    def delete_employee(
        self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, *, actor_user_id: uuid.UUID | None
    ) -> None:
        employee = self.get_employee(db, company_id, employee_id)
        employee.deleted_at = datetime.now(timezone.utc)
        employee.status = "exited"
        employee.user.is_active = False
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="employee",
            entity_id=employee_id,
            action="delete",
        )
        db.commit()

    def report_rows(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None = None,
        department_id: uuid.UUID | None = None,
        status: str | None = None,
        manager_id: uuid.UUID | None = None,
        employment_type: str | None = None,
        location: str | None = None,
        joining_date_from: date | None = None,
        joining_date_to: date | None = None,
    ) -> tuple[list[str], list[list]]:
        employees = self.employee_repo.list_for_export(
            db,
            company_id,
            search=search,
            department_id=department_id,
            status=status,
            manager_id=manager_id,
            employment_type=employment_type,
            location=location,
            joining_date_from=joining_date_from,
            joining_date_to=joining_date_to,
        )
        header = [
            "Employee Code", "First Name", "Last Name", "Email", "Department", "Designation",
            "Manager", "Employment Type", "Location", "Joining Date", "Status", "Onboarding Status",
        ]
        rows = [
            [
                e.employee_code,
                e.first_name,
                e.last_name,
                e.email,
                e.department.name if e.department else "",
                e.designation or "",
                e.manager.full_name if e.manager else "",
                e.employment_type,
                e.location or "",
                e.joining_date.isoformat() if e.joining_date else "",
                e.status,
                e.onboarding_status,
            ]
            for e in employees
        ]
        return header, rows

    def export_csv(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None,
        department_id: uuid.UUID | None,
        status: str | None,
        manager_id: uuid.UUID | None,
        employment_type: str | None,
        location: str | None,
        joining_date_from: date | None,
        joining_date_to: date | None,
    ) -> str:
        header, rows = self.report_rows(
            db,
            company_id,
            search=search,
            department_id=department_id,
            status=status,
            manager_id=manager_id,
            employment_type=employment_type,
            location=location,
            joining_date_from=joining_date_from,
            joining_date_to=joining_date_to,
        )
        return build_csv(header, rows)


employee_service = EmployeeService()
