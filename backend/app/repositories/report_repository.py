import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import SavedReport
from app.repositories.base import TenantScopedRepository


class SavedReportRepository(TenantScopedRepository[SavedReport]):
    model = SavedReport

    def list_all(self, db: Session, company_id: uuid.UUID) -> list[SavedReport]:
        stmt = select(SavedReport).where(SavedReport.company_id == company_id).order_by(SavedReport.name)
        return list(db.execute(stmt).scalars().all())

    def get_by_name(self, db: Session, company_id: uuid.UUID, name: str) -> SavedReport | None:
        stmt = select(SavedReport).where(SavedReport.company_id == company_id, SavedReport.name == name)
        return db.execute(stmt).scalar_one_or_none()
