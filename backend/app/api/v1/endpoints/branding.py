import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyBrandingColorUpdateRequest, CompanyBrandingResponse
from app.services.branding_service import branding_service

router = APIRouter(prefix="/branding", tags=["branding"])


def _to_response(company: Company) -> CompanyBrandingResponse:
    return CompanyBrandingResponse(
        name=company.name, logo_url=branding_service.logo_url(company), primary_color=company.primary_color
    )


@router.get("", response_model=CompanyBrandingResponse)
def get_branding(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    return _to_response(branding_service.get_branding(db, company_id))


@router.patch("/color", response_model=CompanyBrandingResponse)
def update_color(
    payload: CompanyBrandingColorUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("onboarding", "configure")),
    db: Session = Depends(get_db),
):
    company = branding_service.update_color(
        db, company_id, primary_color=payload.primary_color, actor_user_id=current_user.id
    )
    return _to_response(company)


@router.post("/logo", response_model=CompanyBrandingResponse)
async def upload_logo(
    file: UploadFile = File(...),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("onboarding", "configure")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    company = branding_service.upload_logo(
        db,
        company_id,
        filename=file.filename or "logo.png",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        actor_user_id=current_user.id,
    )
    return _to_response(company)
