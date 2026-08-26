import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk

if TYPE_CHECKING:
    from app.models.employee import Employee


class AssetType(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "asset_type"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_asset_type_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Asset(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "asset"
    __table_args__ = (UniqueConstraint("company_id", "asset_tag", name="uq_asset_company_tag"),)

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    asset_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_type.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    # available | assigned | retired | lost | damaged — "assigned" is kept in
    # sync by assign/return, the rest are edited directly (see leave_service
    # -style guard: assigning a non-available asset is rejected).
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    asset_type: Mapped["AssetType"] = relationship()

    @property
    def asset_type_name(self) -> str:
        return self.asset_type.name


class AssetAssignment(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "asset_assignment"

    company_id: Mapped[uuid.UUID] = company_fk(nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )

    asset: Mapped["Asset"] = relationship()
    employee: Mapped["Employee"] = relationship()

    @property
    def asset_tag(self) -> str:
        return self.asset.asset_tag

    @property
    def asset_name(self) -> str:
        return self.asset.name

    @property
    def employee_name(self) -> str:
        return self.employee.full_name
