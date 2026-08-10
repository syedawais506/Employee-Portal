import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin, company_fk

if TYPE_CHECKING:
    from app.models.employee import Employee


class Client(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "client"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_client_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Project(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "project"
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_project_company_name"),)

    company_id: Mapped[uuid.UUID] = company_fk()
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_billable: Mapped[bool] = mapped_column(default=True, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    client: Mapped["Client | None"] = relationship()
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(Base):
    __tablename__ = "project_member"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True
    )
    role_on_project: Mapped[str] = mapped_column(String(20), default="member", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="members")
    employee: Mapped["Employee"] = relationship()

    @property
    def first_name(self) -> str:
        return self.employee.first_name

    @property
    def last_name(self) -> str:
        return self.employee.last_name
