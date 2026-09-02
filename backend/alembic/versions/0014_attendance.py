"""attendance: attendance_shift_config, attendance_record; new attendance
module permissions (view/export/configure — entirely new module, unlike
asset/report which had a pre-declared catalog stub since Phase 1)

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-03 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = ["view", "export", "configure"]

# Mirrors DEFAULT_ROLE_PERMISSIONS in app/services/role_service.py for the
# "attendance" module only. Employee and Finance intentionally get nothing
# here — attendance has no billing angle the way Timesheets does, and every
# employee already gets their own record via /attendance/mine (self-scoped,
# no permission catalog entry needed for that).
RETROACTIVE_GRANTS = {
    "Admin": ["view", "export", "configure"],
    "HR": ["view", "export"],
    "Manager": ["view"],
}


def upgrade() -> None:
    op.create_table(
        "attendance_shift_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("shift_start", sa.Time(), nullable=False, server_default="09:00:00"),
        sa.Column("shift_end", sa.Time(), nullable=False, server_default="18:00:00"),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "attendance_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("attendance_date", sa.Date(), nullable=False, index=True),
        sa.Column("check_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("overtime_hours", sa.Numeric(4, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_record_employee_date"),
    )

    for table in ("attendance_shift_config", "attendance_record"):
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
        [{"id": uuid.uuid4(), "module": "attendance", "action": action} for action in NEW_PERMISSIONS],
    )

    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, action FROM permission WHERE module = 'attendance'")
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
    for table in ("attendance_shift_config", "attendance_record"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("attendance_record")
    op.drop_table("attendance_shift_config")
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'attendance')"
    )
    op.execute("DELETE FROM permission WHERE module = 'attendance'")
