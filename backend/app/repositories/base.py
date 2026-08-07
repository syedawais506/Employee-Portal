from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    """Base repository for any model with a company_id column.

    Every read/write method takes company_id explicitly so there is no code
    path capable of querying across tenants. See docs/LLD.md section 4.
    """

    # Every concrete subclass's `model` declares id/company_id/created_at
    # columns, but the TypeVar bound (Base) can't express that without the
    # SQLAlchemy mypy plugin — hence the targeted ignores below rather than a
    # bug in the underlying query.
    model: type[ModelT]

    def get(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> ModelT | None:
        stmt = select(self.model).where(
            self.model.id == id, self.model.company_id == company_id  # type: ignore[attr-defined]
        )
        return db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        db: Session,
        company_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 25,
        order_by=None,
    ) -> tuple[list[ModelT], int]:
        base_stmt = select(self.model).where(self.model.company_id == company_id)  # type: ignore[attr-defined]
        count_stmt = select(func.count()).select_from(self.model).where(
            self.model.company_id == company_id  # type: ignore[attr-defined]
        )
        total = db.execute(count_stmt).scalar_one()
        stmt = base_stmt.order_by(order_by if order_by is not None else self.model.created_at.desc())  # type: ignore[attr-defined]
        stmt = stmt.offset(skip).limit(limit)
        items = list(db.execute(stmt).scalars().all())
        return items, total

    def create(self, db: Session, company_id: uuid.UUID, **fields) -> ModelT:
        obj = self.model(company_id=company_id, **fields)
        db.add(obj)
        db.flush()
        return obj

    def delete(self, db: Session, company_id: uuid.UUID, id: uuid.UUID) -> None:
        obj = self.get(db, company_id, id)
        if obj is not None:
            db.delete(obj)
            db.flush()
