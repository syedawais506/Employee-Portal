import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.user import User
from app.schemas.common import Page
from app.schemas.department import DepartmentCreateRequest, DepartmentResponse, DepartmentUpdateRequest
from app.services.department_service import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/export")
def export_departments(
    search: str | None = Query(default=None),
    parent_department_id: uuid.UUID | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("department", "export")),
):
    csv_text = department_service.export_csv(
        db,
        company_id,
        search=search,
        parent_department_id=parent_department_id,
        created_from=created_from,
        created_to=created_to,
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="departments-export.csv"'},
    )


@router.get("", response_model=Page[DepartmentResponse])
def list_departments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("department", "view")),
):
    return department_service.list_departments(db, company_id, page=page, page_size=page_size)


@router.post("", response_model=DepartmentResponse, status_code=201)
def create_department(
    payload: DepartmentCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("department", "create")),
):
    return department_service.create_department(
        db,
        company_id,
        name=payload.name,
        parent_department_id=payload.parent_department_id,
        cost_center_code=payload.cost_center_code,
        actor_user_id=current_user.id,
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("department", "view")),
):
    return department_service.get_department(db, company_id, department_id)


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("department", "update")),
):
    return department_service.update_department(
        db,
        company_id,
        department_id,
        name=payload.name,
        parent_department_id=payload.parent_department_id,
        cost_center_code=payload.cost_center_code,
        actor_user_id=current_user.id,
    )


@router.delete("/{department_id}", status_code=204)
def delete_department(
    department_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("department", "delete")),
):
    department_service.delete_department(db, company_id, department_id, actor_user_id=current_user.id)
