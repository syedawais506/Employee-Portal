from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company


class CompanyRepository:
    """Not tenant-scoped by design: companies ARE the tenant boundary.
    Only CompanyService (Super-Admin-only) may use this. See docs/LLD.md section 4.
    """

    def get(self, db: Session, id: uuid.UUID) -> Company | None:
        return db.get(Company, id)

    def get_by_slug(self, db: Session, slug: str) -> Company | None:
        return db.execute(select(Company).where(Company.slug == slug)).scalar_one_or_none()

    def list(
        self, db: Session, *, search: str | None, skip: int, limit: int
    ) -> tuple[list[Company], int]:
        stmt = select(Company).where(Company.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Company).where(Company.deleted_at.is_(None))
        if search:
            like = f"%{search}%"
            condition = or_(Company.name.ilike(like), Company.slug.ilike(like))
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        total = db.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(Company.created_at.desc()).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all()), total

    def create(self, db: Session, **fields) -> Company:
        company = Company(**fields)
        db.add(company)
        db.flush()
        return company
