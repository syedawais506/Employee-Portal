from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.asset import Asset, AssetAssignment, AssetType
from app.repositories.asset_repository import AssetAssignmentRepository, AssetRepository, AssetTypeRepository
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.asset import AssetResponse
from app.schemas.common import Page
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service
from app.utils.csv_export import build_csv

VALID_STATUSES = {"available", "assigned", "retired", "lost", "damaged"}


class AssetService:
    def __init__(self) -> None:
        self.type_repo = AssetTypeRepository()
        self.asset_repo = AssetRepository()
        self.assignment_repo = AssetAssignmentRepository()
        self.employee_repo = EmployeeRepository()

    # -- Asset types ------------------------------------------------------

    def list_asset_types(self, db: Session, company_id: uuid.UUID) -> list[AssetType]:
        return self.type_repo.list_all(db, company_id)

    def get_asset_type(self, db: Session, company_id: uuid.UUID, asset_type_id: uuid.UUID) -> AssetType:
        asset_type = self.type_repo.get(db, company_id, asset_type_id)
        if asset_type is None:
            raise NotFoundError("Asset type not found")
        return asset_type

    def create_asset_type(
        self, db: Session, company_id: uuid.UUID, *, name: str, actor_user_id: uuid.UUID
    ) -> AssetType:
        if self.type_repo.get_by_name(db, company_id, name) is not None:
            raise ConflictError("An asset type with this name already exists")
        asset_type = self.type_repo.create(db, company_id, name=name)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset_type",
            entity_id=asset_type.id,
            action="create",
            after={"name": name},
        )
        db.commit()
        return asset_type

    def update_asset_type(
        self, db: Session, company_id: uuid.UUID, asset_type_id: uuid.UUID, *, actor_user_id: uuid.UUID, **updates
    ) -> AssetType:
        asset_type = self.get_asset_type(db, company_id, asset_type_id)
        before = {"name": asset_type.name}
        for field, value in updates.items():
            if value is not None:
                setattr(asset_type, field, value)
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset_type",
            entity_id=asset_type.id,
            action="update",
            before=before,
            after={"name": asset_type.name},
        )
        db.commit()
        return asset_type

    def delete_asset_type(
        self, db: Session, company_id: uuid.UUID, asset_type_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        asset_type = self.get_asset_type(db, company_id, asset_type_id)
        _, total = self.asset_repo.search(db, company_id, asset_type_id=asset_type_id, status=None, skip=0, limit=1)
        if total > 0:
            raise ConflictError("Cannot delete an asset type that has assets logged against it")
        self.type_repo.delete(db, company_id, asset_type_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset_type",
            entity_id=asset_type_id,
            action="delete",
            before={"name": asset_type.name},
        )
        db.commit()

    # -- Assets -------------------------------------------------------------

    def _to_response(self, asset: Asset, open_assignment: AssetAssignment | None) -> AssetResponse:
        return AssetResponse(
            id=asset.id,
            asset_type_id=asset.asset_type_id,
            asset_type_name=asset.asset_type_name,
            asset_tag=asset.asset_tag,
            name=asset.name,
            purchase_date=asset.purchase_date,
            warranty_expiry=asset.warranty_expiry,
            status=asset.status,
            notes=asset.notes,
            current_employee_id=open_assignment.employee_id if open_assignment else None,
            current_employee_name=open_assignment.employee_name if open_assignment else None,
        )

    def get_asset(self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> AssetResponse:
        asset = self.asset_repo.get(db, company_id, asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        open_assignment = self.assignment_repo.get_open_for_asset(db, company_id, asset_id)
        return self._to_response(asset, open_assignment)

    def list_assets(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        asset_type_id: uuid.UUID | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> Page[AssetResponse]:
        skip = (page - 1) * page_size
        assets, total = self.asset_repo.search(
            db, company_id, asset_type_id=asset_type_id, status=status, skip=skip, limit=page_size
        )
        open_map = self.assignment_repo.get_open_for_assets(db, company_id, [a.id for a in assets])
        items = [self._to_response(a, open_map.get(a.id)) for a in assets]
        return Page(items=items, total=total, page=page, page_size=page_size)

    def create_asset(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        asset_type_id: uuid.UUID,
        asset_tag: str,
        name: str,
        purchase_date: date | None,
        warranty_expiry: date | None,
        notes: str | None,
        actor_user_id: uuid.UUID,
    ) -> AssetResponse:
        self.get_asset_type(db, company_id, asset_type_id)
        if self.asset_repo.get_by_tag(db, company_id, asset_tag) is not None:
            raise ConflictError("An asset with this tag already exists")
        asset = self.asset_repo.create(
            db,
            company_id,
            asset_type_id=asset_type_id,
            asset_tag=asset_tag,
            name=name,
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
            notes=notes,
        )
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset",
            entity_id=asset.id,
            action="create",
            after={"asset_tag": asset_tag, "name": name},
        )
        db.commit()
        return self.get_asset(db, company_id, asset.id)

    def update_asset(
        self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID, *, actor_user_id: uuid.UUID, **updates
    ) -> AssetResponse:
        asset = self.asset_repo.get(db, company_id, asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        if updates.get("status") == "assigned":
            raise ValidationAppError("Use the assign action to mark an asset as assigned")
        if updates.get("status") is not None and updates["status"] not in VALID_STATUSES:
            raise ValidationAppError("Invalid status")
        before = {"status": asset.status}
        for field, value in updates.items():
            if value is not None:
                setattr(asset, field, value)
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset",
            entity_id=asset.id,
            action="update",
            before=before,
            after={"status": asset.status},
        )
        db.commit()
        return self.get_asset(db, company_id, asset_id)

    def delete_asset(
        self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> None:
        asset = self.asset_repo.get(db, company_id, asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        if self.assignment_repo.has_any_for_asset(db, company_id, asset_id):
            raise ConflictError("Cannot delete an asset that has assignment history")
        self.asset_repo.delete(db, company_id, asset_id)
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset",
            entity_id=asset_id,
            action="delete",
            before={"asset_tag": asset.asset_tag},
        )
        db.commit()

    # -- Assignment ----------------------------------------------------------

    def assign_asset(
        self,
        db: Session,
        company_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        employee_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> AssetResponse:
        asset = self.asset_repo.get(db, company_id, asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        if asset.status != "available":
            raise ConflictError(f"Asset is not available (current status: {asset.status})")
        employee = self.employee_repo.get(db, company_id, employee_id)
        if employee is None:
            raise ValidationAppError("Employee does not belong to this company")

        self.assignment_repo.create_assignment(
            db, company_id, asset_id=asset_id, employee_id=employee_id, assigned_by=actor_user_id
        )
        asset.status = "assigned"
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset",
            entity_id=asset.id,
            action="update",
            after={"status": "assigned", "employee_id": str(employee_id)},
        )
        notification_service.notify(
            db,
            company_id,
            employee.user_id,
            type="asset.assigned",
            title=f"{asset.name} was assigned to you",
            body=f"Asset tag: {asset.asset_tag}",
            entity_type="asset",
            entity_id=asset.id,
        )
        db.commit()
        return self.get_asset(db, company_id, asset_id)

    def return_asset(
        self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID, *, actor_user_id: uuid.UUID
    ) -> AssetResponse:
        asset = self.asset_repo.get(db, company_id, asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        open_assignment = self.assignment_repo.get_open_for_asset(db, company_id, asset_id)
        if open_assignment is None:
            raise ConflictError("This asset is not currently assigned")

        open_assignment.returned_at = datetime.now(timezone.utc)
        open_assignment.returned_by = actor_user_id
        asset.status = "available"
        db.flush()
        audit_service.record(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            entity_type="asset",
            entity_id=asset.id,
            action="update",
            after={"status": "available"},
        )
        db.commit()
        return self.get_asset(db, company_id, asset_id)

    def list_history_for_asset(self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> list[AssetAssignment]:
        if self.asset_repo.get(db, company_id, asset_id) is None:
            raise NotFoundError("Asset not found")
        return self.assignment_repo.list_for_asset(db, company_id, asset_id)

    def list_my_assignments(self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID) -> list[AssetAssignment]:
        return self.assignment_repo.list_for_employee(db, company_id, employee_id)

    # -- Summary & export ------------------------------------------------------

    def get_summary(self, db: Session, company_id: uuid.UUID) -> dict:
        counts = self.asset_repo.counts_by_status(db, company_id)
        return {
            "total": sum(counts.values()),
            "available": counts.get("available", 0),
            "assigned": counts.get("assigned", 0),
            "retired": counts.get("retired", 0),
            "lost": counts.get("lost", 0),
            "damaged": counts.get("damaged", 0),
        }

    def report_rows(
        self, db: Session, company_id: uuid.UUID, *, asset_type_id: uuid.UUID | None = None, status: str | None = None
    ) -> tuple[list[str], list[list]]:
        assets = self.asset_repo.list_for_export(db, company_id, asset_type_id=asset_type_id, status=status)
        open_map = self.assignment_repo.get_open_for_assets(db, company_id, [a.id for a in assets])
        header = ["Asset Tag", "Name", "Type", "Status", "Current Holder", "Purchase Date", "Warranty Expiry"]
        rows = [
            [
                a.asset_tag,
                a.name,
                a.asset_type_name,
                a.status,
                open_map[a.id].employee_name if a.id in open_map else "",
                a.purchase_date.isoformat() if a.purchase_date else "",
                a.warranty_expiry.isoformat() if a.warranty_expiry else "",
            ]
            for a in assets
        ]
        return header, rows

    def export_csv(
        self, db: Session, company_id: uuid.UUID, *, asset_type_id: uuid.UUID | None, status: str | None
    ) -> str:
        header, rows = self.report_rows(db, company_id, asset_type_id=asset_type_id, status=status)
        return build_csv(header, rows)


asset_service = AssetService()
