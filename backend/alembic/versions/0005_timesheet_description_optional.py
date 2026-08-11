"""timesheet_period_config: description is optional by default

Employees log time first and submit later — requiring a description on every
entry up front didn't match that flow. The column also only ever gated
description (project was already structurally required), so it's renamed to
match what it actually does.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-12 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "timesheet_period_config",
        "require_project_and_description",
        new_column_name="require_description",
        server_default=sa.false(),
    )
    op.execute("UPDATE timesheet_period_config SET require_description = false")


def downgrade() -> None:
    op.execute("UPDATE timesheet_period_config SET require_description = true")
    op.alter_column(
        "timesheet_period_config",
        "require_description",
        new_column_name="require_project_and_description",
        server_default=sa.true(),
    )
