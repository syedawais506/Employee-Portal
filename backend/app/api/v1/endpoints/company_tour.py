import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.onboarding import CompanyTourStep
from app.models.user import User
from app.schemas.onboarding import CompanyTourStepResponse, CompanyTourStepUpdateRequest
from app.services.company_tour_service import company_tour_service

router = APIRouter(prefix="/company-tour", tags=["onboarding"])


def _to_response(step: CompanyTourStep) -> CompanyTourStepResponse:
    return CompanyTourStepResponse(
        id=step.id,
        title=step.title,
        body=step.body,
        image_url=company_tour_service.image_url(step),
        sort_order=step.sort_order,
    )


@router.get("", response_model=list[CompanyTourStepResponse])
def list_steps(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("onboarding", "view")),
):
    return [_to_response(step) for step in company_tour_service.list_steps(db, company_id)]


@router.post("", response_model=CompanyTourStepResponse, status_code=201)
async def create_step(
    title: str = Form(...),
    body: str = Form(...),
    sort_order: int = Form(default=0),
    image: UploadFile | None = File(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("onboarding", "configure")),
    db: Session = Depends(get_db),
):
    image_payload = None
    if image is not None and image.filename:
        content = await image.read()
        image_payload = (content, image.filename, image.content_type or "application/octet-stream")

    step = company_tour_service.create_step(
        db,
        company_id,
        title=title,
        body=body,
        sort_order=sort_order,
        image=image_payload,
        actor_user_id=current_user.id,
    )
    return _to_response(step)


@router.patch("/{step_id}", response_model=CompanyTourStepResponse)
def update_step(
    step_id: uuid.UUID,
    payload: CompanyTourStepUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("onboarding", "configure")),
    db: Session = Depends(get_db),
):
    step = company_tour_service.update_step(
        db,
        company_id,
        step_id,
        title=payload.title,
        body=payload.body,
        sort_order=payload.sort_order,
        actor_user_id=current_user.id,
    )
    return _to_response(step)


@router.delete("/{step_id}", status_code=204)
def delete_step(
    step_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("onboarding", "configure")),
    db: Session = Depends(get_db),
):
    company_tour_service.delete_step(db, company_id, step_id, actor_user_id=current_user.id)
