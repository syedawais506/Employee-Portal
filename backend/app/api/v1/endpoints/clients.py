import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_company_id, get_db, require_permission
from app.models.user import User
from app.schemas.project import ClientCreateRequest, ClientResponse, ClientUpdateRequest
from app.services.client_service import client_service

router = APIRouter(prefix="/clients", tags=["projects"])


@router.get("/export")
def export_clients(
    search: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project", "export")),
):
    csv_text = client_service.export_csv(
        db, company_id, search=search, created_from=created_from, created_to=created_to
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clients-export.csv"'},
    )


@router.get("", response_model=list[ClientResponse])
def list_clients(
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("project", "view")),
):
    return client_service.list_clients(db, company_id)


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "create")),
):
    return client_service.create_client(
        db,
        company_id,
        name=payload.name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        actor_user_id=current_user.id,
    )


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdateRequest,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "update")),
):
    return client_service.update_client(
        db,
        company_id,
        client_id,
        name=payload.name,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        actor_user_id=current_user.id,
    )


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: uuid.UUID,
    company_id: uuid.UUID = Depends(get_current_company_id),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project", "delete")),
):
    client_service.delete_client(db, company_id, client_id, actor_user_id=current_user.id)
