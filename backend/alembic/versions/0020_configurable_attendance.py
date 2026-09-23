"""Admin-configurable attendance: company.attendance_enabled / attendance_mode
("check_in_out" or "timesheet"), following the same per-company opt-in
convention as ai_chatbot_enabled. Both default to preserve today's behavior
(enabled, manual check-in/out) for every existing company.

Also adds attendance_record.source ("manual" vs "timesheet") so a row
created automatically from a timesheet submission (when a company runs in
"timesheet" mode) can be told apart from a real check-in/out — existing rows
default to "manual", which is exactly what they are.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-24 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("attendance_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "company",
        sa.Column("attendance_mode", sa.String(length=20), nullable=False, server_default="check_in_out"),
    )
    op.add_column(
        "attendance_record",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
    )


def downgrade() -> None:
    op.drop_column("attendance_record", "source")
    op.drop_column("company", "attendance_mode")
    op.drop_column("company", "attendance_enabled")
