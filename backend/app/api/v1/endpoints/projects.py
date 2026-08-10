import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.common import Page
from app.schemas.project import (
    MyProjectResponse,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectMemberInput,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
)
from app.services.employee_service import employee_service
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _summary(project) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        is_billable=project.is_billable,
        start_date=project.start_date,
        end_date=project.end_date,
        member_count=len(project.members),
        client=project.client,
    )


@router.get("", response_model=Page[ProjectSummaryResponse])
def list_projects(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project", "view")),
):
    result = project_service.list_projects(db, company_id, status=status, page=page, page_size=page_size)
    return Page(
        items=[_summary(p) for p in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.post("", response_model=ProjectDetailResponse, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "create")),
):
    return project_service.create_project(
        db,
        company_id,
        name=payload.name,
        client_id=payload.client_id,
        budget=payload.budget,
        is_billable=payload.is_billable,
        start_date=payload.start_date,
        end_date=payload.end_date,
        member_ids=[m.model_dump() for m in payload.member_ids],
        actor_user_id=current_user.id,
    )


@router.get("/mine", response_model=list[MyProjectResponse])
def list_my_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    employee = employee_service.get_employee_by_user_id(db, current_user.id)
    return project_service.get_my_projects(db, employee.id)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project", "view")),
):
    return project_service.get_project(db, company_id, project_id)


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "update")),
):
    updates = payload.model_dump(exclude_unset=True)
    return project_service.update_project(db, company_id, project_id, actor_user_id=current_user.id, **updates)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "delete")),
):
    project_service.delete_project(db, company_id, project_id, actor_user_id=current_user.id)


@router.post("/{project_id}/members", response_model=ProjectDetailResponse)
def add_project_member(
    project_id: uuid.UUID,
    payload: ProjectMemberInput,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "update")),
):
    return project_service.add_member(
        db,
        company_id,
        project_id,
        employee_id=payload.employee_id,
        role_on_project=payload.role_on_project,
        actor_user_id=current_user.id,
    )


@router.delete("/{project_id}/members/{employee_id}", response_model=ProjectDetailResponse)
def remove_project_member(
    project_id: uuid.UUID,
    employee_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "update")),
):
    return project_service.remove_member(db, company_id, project_id, employee_id, actor_user_id=current_user.id)
