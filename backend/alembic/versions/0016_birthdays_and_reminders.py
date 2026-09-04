"""dashboard widgets & configurable timesheet reminders: employee.birth_date
(nullable, optional PII, opt-in), timesheet_period_config.reminder_enabled/
reminder_after_days. No new permissions.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-05 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employee", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column(
        "timesheet_period_config",
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "timesheet_period_config",
        sa.Column("reminder_after_days", sa.Integer(), nullable=False, server_default="3"),
    )


def downgrade() -> None:
    op.drop_column("timesheet_period_config", "reminder_after_days")
    op.drop_column("timesheet_period_config", "reminder_enabled")
    op.drop_column("employee", "birth_date")
