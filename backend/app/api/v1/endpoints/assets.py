import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.asset import (
    AssetAssignmentResponse,
    AssetCreateRequest,
    AssetResponse,
    AssetSummaryResponse,
    AssetTypeCreateRequest,
    AssetTypeResponse,
    AssetTypeUpdateRequest,
    AssetUpdateRequest,
    AssignAssetRequest,
)
from app.schemas.common import Page
from app.services.asset_service import asset_service
from app.services.employee_service import employee_service

router = APIRouter(tags=["assets"])


def _employee_id(current_user: User, db: Session) -> uuid.UUID:
    return employee_service.get_employee_by_user_id(db, current_user.id).id


# -- Asset types --------------------------------------------------------------


@router.get("/asset-types", response_model=list[AssetTypeResponse])
def list_asset_types(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset", "view")),
):
    return asset_service.list_asset_types(db, company_id)


@router.post("/asset-types", response_model=AssetTypeResponse, status_code=201)
def create_asset_type(
    payload: AssetTypeCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "create")),
    db: Session = Depends(get_db),
):
    return asset_service.create_asset_type(db, company_id, name=payload.name, actor_user_id=current_user.id)


@router.patch("/asset-types/{asset_type_id}", response_model=AssetTypeResponse)
def update_asset_type(
    asset_type_id: uuid.UUID,
    payload: AssetTypeUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "update")),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    return asset_service.update_asset_type(db, company_id, asset_type_id, actor_user_id=current_user.id, **updates)


@router.delete("/asset-types/{asset_type_id}", status_code=204)
def delete_asset_type(
    asset_type_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "delete")),
    db: Session = Depends(get_db),
):
    asset_service.delete_asset_type(db, company_id, asset_type_id, actor_user_id=current_user.id)


# -- Assets --------------------------------------------------------------------


@router.get("/assets", response_model=Page[AssetResponse])
def list_assets(
    asset_type_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset", "view")),
):
    return asset_service.list_assets(
        db, company_id, asset_type_id=asset_type_id, status=status, page=page, page_size=page_size
    )


@router.get("/assets/mine", response_model=list[AssetAssignmentResponse])
def list_my_assets(
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee_id = _employee_id(current_user, db)
    return asset_service.list_my_assignments(db, company_id, employee_id)


@router.get("/assets/summary", response_model=AssetSummaryResponse)
def get_asset_summary(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset", "view")),
):
    return asset_service.get_summary(db, company_id)


@router.get("/assets/export")
def export_assets(
    asset_type_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset", "export")),
):
    csv_text = asset_service.export_csv(db, company_id, asset_type_id=asset_type_id, status=status)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="asset-export.csv"'},
    )


@router.post("/assets", response_model=AssetResponse, status_code=201)
def create_asset(
    payload: AssetCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "create")),
    db: Session = Depends(get_db),
):
    return asset_service.create_asset(
        db,
        company_id,
        asset_type_id=payload.asset_type_id,
        asset_tag=payload.asset_tag,
        name=payload.name,
        purchase_date=payload.purchase_date,
        warranty_expiry=payload.warranty_expiry,
        notes=payload.notes,
        actor_user_id=current_user.id,
    )


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "update")),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    return asset_service.update_asset(db, company_id, asset_id, actor_user_id=current_user.id, **updates)


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(
    asset_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "delete")),
    db: Session = Depends(get_db),
):
    asset_service.delete_asset(db, company_id, asset_id, actor_user_id=current_user.id)


@router.post("/assets/{asset_id}/assign", response_model=AssetResponse)
def assign_asset(
    asset_id: uuid.UUID,
    payload: AssignAssetRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "update")),
    db: Session = Depends(get_db),
):
    return asset_service.assign_asset(
        db, company_id, asset_id, employee_id=payload.employee_id, actor_user_id=current_user.id
    )


@router.post("/assets/{asset_id}/return", response_model=AssetResponse)
def return_asset(
    asset_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_permission("asset", "update")),
    db: Session = Depends(get_db),
):
    return asset_service.return_asset(db, company_id, asset_id, actor_user_id=current_user.id)


@router.get("/assets/{asset_id}/history", response_model=list[AssetAssignmentResponse])
def get_asset_history(
    asset_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset", "view")),
):
    return asset_service.list_history_for_asset(db, company_id, asset_id)
