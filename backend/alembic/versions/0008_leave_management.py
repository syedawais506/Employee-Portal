"""leave management: leave_type, holiday_calendar, leave_balance,
leave_request; company.require_hr_leave_approval; leave.export/configure
permissions + retroactive grants matching the widened Phase 5 defaults

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-26 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = ["export", "configure"]

# Mirrors DEFAULT_ROLE_PERMISSIONS in app/services/role_service.py for the
# "leave" module only — grants existing companies' system roles the same
# widened defaults a brand-new company gets automatically now.
RETROACTIVE_GRANTS = {
    "Admin": ["create", "update", "delete", "export", "configure"],
    "HR": ["create", "update", "export"],
    "Manager": ["create", "update"],
}


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("require_hr_leave_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "leave_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("annual_quota_days", sa.Integer(), nullable=True),
        sa.Column("max_carry_forward_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requires_attachment", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_leave_type_company_name"),
    )

    op.create_table(
        "holiday_calendar",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "date", name="uq_holiday_company_date"),
    )

    op.create_table(
        "leave_balance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("leave_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_type.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("granted", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("carried_forward", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("adjustment", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance_employee_type_year"),
    )

    op.create_table(
        "leave_request",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("leave_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_type.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("start_date", sa.Date(), nullable=False, index=True),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("attachment_file_key", sa.String(512), nullable=True),
        sa.Column("attachment_original_filename", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("manager_approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manager_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hr_approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("hr_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    for table in ("leave_type", "holiday_calendar", "leave_balance", "leave_request"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
            """
        )

    permission_table = sa.table(
        "permission",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
    )
    op.bulk_insert(
        permission_table,
        [{"id": uuid.uuid4(), "module": "leave", "action": action} for action in NEW_PERMISSIONS],
    )

    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, action FROM permission WHERE module = 'leave'")
    ).fetchall()
    permission_id_by_action = {row.action: row.id for row in permission_rows}

    role_rows = connection.execute(
        sa.text("SELECT id, name FROM role WHERE name IN ('Admin', 'HR', 'Manager')")
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
    for table in ("leave_type", "holiday_calendar", "leave_balance", "leave_request"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("leave_request")
    op.drop_table("leave_balance")
    op.drop_table("holiday_calendar")
    op.drop_table("leave_type")
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'leave' AND action IN ('export', 'configure'))"
    )
    op.execute("DELETE FROM permission WHERE module = 'leave' AND action IN ('export', 'configure')")
    op.drop_column("company", "require_hr_leave_approval")
