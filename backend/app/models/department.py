import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.employee import Employee


class Department(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "department"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_department_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("department.id", ondelete="SET NULL"), nullable=True
    )
    cost_center_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="departments")
    parent: Mapped["Department | None"] = relationship(remote_side="Department.id")
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")
