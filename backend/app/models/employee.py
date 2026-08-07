import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin, company_fk


class Employee(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "employee"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_code", name="uq_employee_company_code"),
    )

    company_id: Mapped[uuid.UUID] = company_fk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("department.id", ondelete="SET NULL"), nullable=True
    )
    designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employee.id", ondelete="SET NULL"), nullable=True
    )
    employment_type: Mapped[str] = mapped_column(String(30), default="full_time", nullable=False)
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    company: Mapped["Company"] = relationship(back_populates="employees")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="employee")  # noqa: F821
    department: Mapped["Department | None"] = relationship(back_populates="employees")  # noqa: F821
    manager: Mapped["Employee | None"] = relationship(remote_side="Employee.id")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def email(self) -> str:
        return self.user.email
