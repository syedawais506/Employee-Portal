"""timesheets: timesheet_period_config, timesheet_entry, timesheet_submission

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-01 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Only "configure" is new to the "timesheet" module — view/create/update/delete/
# approve/reject/export were already seeded for it in migration 0001.
NEW_PERMISSIONS = ["configure"]

# Mirrors DEFAULT_ROLE_PERMISSIONS in app/services/role_service.py for the
# "timesheet" module only — grants existing companies' system roles the same
# widened defaults a brand-new company gets automatically now that every role
# can log its own hours and Finance/Admin have their new approval/config powers.
RETROACTIVE_GRANTS = {
    "Admin": ["create", "update", "delete", "export", "configure"],
    "HR": ["view", "create", "update"],
    "Manager": ["create", "update"],
    "Finance": ["create", "update", "approve", "reject"],
}


def upgrade() -> None:
    op.create_table(
        "timesheet_period_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period_type", sa.String(20), nullable=False, server_default="weekly"),
        sa.Column("week_start_day", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_hours_per_day", sa.Numeric(4, 2), nullable=True),
        sa.Column("max_hours_per_day", sa.Numeric(4, 2), nullable=True, server_default="24"),
        sa.Column("require_project_and_description", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("warn_on_weekend", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_finance_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "timesheet_submission",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("manager_approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manager_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finance_approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finance_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "period_start", "period_end", name="uq_timesheet_submission_employee_period"),
    )

    op.create_table(
        "timesheet_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("timesheet_submission.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("entry_date", sa.Date(), nullable=False, index=True),
        sa.Column("hours", sa.Numeric(4, 2), nullable=False),
        sa.Column("is_billable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("work_type", sa.String(20), nullable=False, server_default="office"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "entry_date", "project_id", name="uq_timesheet_entry_employee_date_project"),
    )

    for table in ("timesheet_period_config", "timesheet_submission", "timesheet_entry"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
            """
        )

    # Seed the new "timesheet.configure" permission catalog row.
    permission_table = sa.table(
        "permission",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
    )
    op.bulk_insert(
        permission_table,
        [{"id": uuid.uuid4(), "module": "timesheet", "action": action} for action in NEW_PERMISSIONS],
    )

    # Retroactively grant the widened "timesheet" permissions to existing
    # companies' system roles, matching what a brand-new company gets
    # automatically now — see RETROACTIVE_GRANTS above and
    # DEFAULT_ROLE_PERMISSIONS in role_service.py.
    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, action FROM permission WHERE module = 'timesheet'")
    ).fetchall()
    permission_id_by_action = {row.action: row.id for row in permission_rows}

    role_rows = connection.execute(
        sa.text("SELECT id, name FROM role WHERE name IN ('Admin', 'HR', 'Manager', 'Finance')")
    ).fetchall()
    for role_row in role_rows:
        for action in RETROACTIVE_GRANTS.get(role_row.name, []):
            connection.execute(
                sa.text(
                    "INSERT INTO role_permission (role_id, permission_id) VALUES (:role_id, :permission_id) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_row.id, "permission_id": permission_id_by_action[action]},
            )


def downgrade() -> None:
    for table in ("timesheet_period_config", "timesheet_submission", "timesheet_entry"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("timesheet_entry")
    op.drop_table("timesheet_submission")
    op.drop_table("timesheet_period_config")
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'timesheet' AND action = 'configure')"
    )
    op.execute("DELETE FROM permission WHERE module = 'timesheet' AND action = 'configure'")
