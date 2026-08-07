from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class Company(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "company"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    subdomain: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    departments: Mapped[list["Department"]] = relationship(  # noqa: F821
        back_populates="company", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(  # noqa: F821
        back_populates="company", cascade="all, delete-orphan"
    )
