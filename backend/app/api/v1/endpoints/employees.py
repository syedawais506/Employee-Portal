import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.common import Page
from app.schemas.employee import (
    EmployeeCreateRequest,
    EmployeeDetailResponse,
    EmployeeSelfUpdateRequest,
    EmployeeSummaryResponse,
    EmployeeUpdateRequest,
)
from app.services.employee_service import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=Page[EmployeeSummaryResponse])
def list_employees(
    search: str | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    manager_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("employee", "view")),
):
    return employee_service.search_employees(
        db,
        company_id,
        search=search,
        department_id=department_id,
        status=status,
        manager_id=manager_id,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=EmployeeDetailResponse, status_code=201)
def create_employee(
    payload: EmployeeCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employee", "create")),
):
    return employee_service.create_employee(
        db,
        company_id,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        department_id=payload.department_id,
        designation=payload.designation,
        manager_id=payload.manager_id,
        employment_type=payload.employment_type,
        joining_date=payload.joining_date,
        role_ids=payload.role_ids,
        actor_user_id=current_user.id,
    )


@router.get("/me", response_model=EmployeeDetailResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return employee_service.get_employee_by_user_id(db, current_user.id)


@router.patch("/me", response_model=EmployeeDetailResponse)
def update_my_profile(
    payload: EmployeeSelfUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = employee_service.get_employee_by_user_id(db, current_user.id)
    return employee_service.update_self(db, current_user.company_id, employee.id, phone=payload.phone)


@router.get("/{employee_id}", response_model=EmployeeDetailResponse)
def get_employee(
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("employee", "view")),
):
    return employee_service.get_employee(db, company_id, employee_id)


@router.patch("/{employee_id}", response_model=EmployeeDetailResponse)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employee", "update")),
):
    updates = payload.model_dump(exclude_unset=True)
    return employee_service.update_employee(db, company_id, employee_id, actor_user_id=current_user.id, **updates)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employee", "delete")),
):
    employee_service.delete_employee(db, company_id, employee_id, actor_user_id=current_user.id)
