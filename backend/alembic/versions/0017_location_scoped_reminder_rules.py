"""location-scoped timesheet reminder rules: drop the flat
timesheet_period_config.reminder_enabled/reminder_after_days fields shipped
in migration 0016 (replaced same-day, before any real usage, once the
requirement turned out to be per-location cadence rather than one rolling
threshold) in favor of a new timesheet_reminder_rule table — one row per
(company_id, location), location nullable meaning "default/every other
location," the same convention holiday_calendar.location already
established. No new permissions (reuses timesheet.view/timesheet.configure).

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-05 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("timesheet_period_config", "reminder_after_days")
    op.drop_column("timesheet_period_config", "reminder_enabled")

    op.create_table(
        "timesheet_reminder_rule",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cadence", sa.String(length=20), nullable=False, server_default="weekly"),
        sa.Column("grace_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "location", name="uq_timesheet_reminder_rule_company_location"),
    )
    op.execute("ALTER TABLE timesheet_reminder_rule ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE timesheet_reminder_rule FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON timesheet_reminder_rule
        USING (company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.drop_table("timesheet_reminder_rule")
    op.add_column(
        "timesheet_period_config",
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "timesheet_period_config",
        sa.Column("reminder_after_days", sa.Integer(), nullable=False, server_default="3"),
    )
