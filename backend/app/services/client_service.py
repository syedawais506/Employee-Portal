from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.project import Client
from app.repositories.project_repository import ClientRepository
from app.services.audit_service import audit_service
from app.utils.csv_export import build_csv


class ClientService:
    def __init__(self) -> None:
        self.repo = ClientRepository()

    def list_clients(self, db: Session, company_id: uuid.UUID) -> list[Client]:
        return self.repo.list_all(db, company_id)

    def get_client(self, db: Session, company_id: uuid.UUID, client_id: uuid.UUID) -> Client:
        client = self.repo.get(db, company_id, client_id)
        if client is None:
            raise NotFoundError("Client not found")
        return client

    def create_client(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        name: str,
        contact_name: str | None,
        contact_email: str | None,
        contact_phone: str | None,
        actor_user_id: uuid.UUID,
    ) -> Client:
        if any(c.name == name for c in self.repo.list_all(db, company_id)):
            raise ConflictError("A client with this name already exists")
        client = self.repo.create(
            db,
            company_id,
            name=name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="client",
            entity_id=client.id,
            action="create",
            after={"name": name},
        )
        db.commit()
        return client

    def update_client(
        self,
        db: Session,
        company_id: uuid.UUID,
        client_id: uuid.UUID,
        *,
        name: str | None,
        contact_name: str | None,
        contact_email: str | None,
        contact_phone: str | None,
        actor_user_id: uuid.UUID,
    ) -> Client:
        client = self.get_client(db, company_id, client_id)
        before = {"name": client.name}
        if name is not None:
            client.name = name
        if contact_name is not None:
            client.contact_name = contact_name
        if contact_email is not None:
            client.contact_email = contact_email
        if contact_phone is not None:
            client.contact_phone = contact_phone
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="client",
            entity_id=client.id,
            action="update",
            before=before,
            after={"name": client.name},
        )
        db.commit()
        return client

    def delete_client(
        self, db: Session, company_id: uuid.UUID, client_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        client = self.get_client(db, company_id, client_id)
        self.repo.delete(db, company_id, client_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="client",
            entity_id=client_id,
            action="delete",
            before={"name": client.name},
        )
        db.commit()

    def export_csv(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        search: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> str:
        clients = self.repo.list_for_export(
            db, company_id, search=search, created_from=created_from, created_to=created_to
        )
        header = ["Name", "Contact Name", "Contact Email", "Contact Phone", "Created At"]
        rows = [
            [c.name, c.contact_name or "", c.contact_email or "", c.contact_phone or "", c.created_at.isoformat()]
            for c in clients
        ]
        return build_csv(header, rows)


client_service = ClientService()
