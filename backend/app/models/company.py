from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee import Employee


class Company(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "company"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    subdomain: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    require_hr_leave_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    slack_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    departments: Mapped[list["Department"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
