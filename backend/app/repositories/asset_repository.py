from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.asset import Asset, AssetAssignment, AssetType
from app.repositories.base import TenantScopedRepository


class AssetTypeRepository(TenantScopedRepository[AssetType]):
    model = AssetType

    def list_all(self, db: Session, company_id: uuid.UUID) -> list[AssetType]:
        stmt = select(AssetType).where(AssetType.company_id == company_id).order_by(AssetType.name)
        return list(db.execute(stmt).scalars().all())

    def get_by_name(self, db: Session, company_id: uuid.UUID, name: str) -> AssetType | None:
        stmt = select(AssetType).where(AssetType.company_id == company_id, AssetType.name == name)
        return db.execute(stmt).scalar_one_or_none()


class AssetRepository(TenantScopedRepository[Asset]):
    model = Asset

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> Asset | None:
        stmt = (
            select(Asset)
            .options(joinedload(Asset.asset_type))
            .where(Asset.id == id, Asset.company_id == company_id)
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_by_tag(self, db: Session, company_id: uuid.UUID, asset_tag: str) -> Asset | None:
        stmt = select(Asset).where(Asset.company_id == company_id, Asset.asset_tag == asset_tag)
        return db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        asset_type_id: uuid.UUID | None,
        status: str | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Asset], int]:
        conditions = [Asset.company_id == company_id]
        if asset_type_id:
            conditions.append(Asset.asset_type_id == asset_type_id)
        if status:
            conditions.append(Asset.status == status)

        count_stmt = select(func.count()).select_from(Asset).where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = (
            select(Asset)
            .options(joinedload(Asset.asset_type))
            .where(*conditions)
            .order_by(Asset.asset_tag)
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).unique().scalars().all())
        return items, total

    def list_for_export(
        self, db: Session, company_id: uuid.UUID, *, asset_type_id: uuid.UUID | None, status: str | None
    ) -> list[Asset]:
        conditions = [Asset.company_id == company_id]
        if asset_type_id:
            conditions.append(Asset.asset_type_id == asset_type_id)
        if status:
            conditions.append(Asset.status == status)
        stmt = (
            select(Asset).options(joinedload(Asset.asset_type)).where(*conditions).order_by(Asset.asset_tag)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def counts_by_status(self, db: Session, company_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Asset.status, func.count())
            .where(Asset.company_id == company_id)
            .group_by(Asset.status)
        )
        return {status: count for status, count in db.execute(stmt).all()}


class AssetAssignmentRepository(TenantScopedRepository[AssetAssignment]):
    model = AssetAssignment

    def get_open_for_asset(self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> AssetAssignment | None:
        stmt = (
            select(AssetAssignment)
            .options(joinedload(AssetAssignment.employee), joinedload(AssetAssignment.asset))
            .where(
                AssetAssignment.company_id == company_id,
                AssetAssignment.asset_id == asset_id,
                AssetAssignment.returned_at.is_(None),
            )
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_open_for_assets(
        self, db: Session, company_id: uuid.UUID, asset_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, AssetAssignment]:
        if not asset_ids:
            return {}
        stmt = (
            select(AssetAssignment)
            .options(joinedload(AssetAssignment.employee))
            .where(
                AssetAssignment.company_id == company_id,
                AssetAssignment.asset_id.in_(asset_ids),
                AssetAssignment.returned_at.is_(None),
            )
        )
        rows = db.execute(stmt).unique().scalars().all()
        return {row.asset_id: row for row in rows}

    def create_assignment(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        asset_id: uuid.UUID,
        employee_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> AssetAssignment:
        return self.create(
            db,
            company_id,
            asset_id=asset_id,
            employee_id=employee_id,
            assigned_at=datetime.now(timezone.utc),
            assigned_by=assigned_by,
        )

    def list_for_asset(self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> list[AssetAssignment]:
        stmt = (
            select(AssetAssignment)
            .options(joinedload(AssetAssignment.employee), joinedload(AssetAssignment.asset))
            .where(AssetAssignment.company_id == company_id, AssetAssignment.asset_id == asset_id)
            .order_by(AssetAssignment.assigned_at.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def list_for_employee(self, db: Session, company_id: uuid.UUID, employee_id: uuid.UUID) -> list[AssetAssignment]:
        stmt = (
            select(AssetAssignment)
            .options(joinedload(AssetAssignment.employee), joinedload(AssetAssignment.asset))
            .where(AssetAssignment.company_id == company_id, AssetAssignment.employee_id == employee_id)
            .order_by(AssetAssignment.assigned_at.desc())
        )
        return list(db.execute(stmt).unique().scalars().all())

    def has_any_for_asset(self, db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> bool:
        stmt = select(AssetAssignment.id).where(
            AssetAssignment.company_id == company_id, AssetAssignment.asset_id == asset_id
        ).limit(1)
        return db.execute(stmt).first() is not None
