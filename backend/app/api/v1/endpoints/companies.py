import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_super_admin
from app.models.user import User
from app.schemas.common import Page
from app.schemas.company import CompanyCreateRequest, CompanyResponse, CompanyUpdateRequest
from app.services.company_service import company_service

router = APIRouter(prefix="/companies", tags=["companies"], dependencies=[Depends(require_super_admin)])


@router.get("", response_model=Page[CompanyResponse])
def list_companies(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = company_service.list_companies(db, search=search, page=page, page_size=page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=CompanyResponse, status_code=201)
def create_company(
    payload: CompanyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return company_service.create_company(
        db,
        name=payload.name,
        slug=payload.slug,
        admin_email=payload.admin_email,
        admin_first_name=payload.admin_first_name,
        admin_last_name=payload.admin_last_name,
        actor_user_id=current_user.id,
    )


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return company_service.get_company(db, company_id)


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    return company_service.update_company(
        db, company_id, name=payload.name, status=payload.status, actor_user_id=current_user.id
    )


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin),
):
    company_service.delete_company(db, company_id, actor_user_id=current_user.id)
