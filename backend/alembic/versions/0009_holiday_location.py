"""holiday_calendar: location (nullable = applies to every employee;
set = only excluded/shown for employees whose employee.location matches)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-25 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_holiday_company_date", "holiday_calendar", type_="unique")
    op.add_column("holiday_calendar", sa.Column("location", sa.String(100), nullable=True))
    op.create_unique_constraint(
        "uq_holiday_company_date_location", "holiday_calendar", ["company_id", "date", "location"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_holiday_company_date_location", "holiday_calendar", type_="unique")
    op.drop_column("holiday_calendar", "location")
    op.create_unique_constraint("uq_holiday_company_date", "holiday_calendar", ["company_id", "date"])
