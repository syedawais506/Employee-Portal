"""reports: saved_report table; report.configure permission + retroactive
grant to Admin (report.view/export were already inserted by migration 0001's
frozen catalog snapshot and already granted to Admin/HR/Manager/Finance at
company-creation time via DEFAULT_ROLE_PERMISSIONS — only configure is new)

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-27 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = ["configure"]

# Mirrors DEFAULT_ROLE_PERMISSIONS in app/services/role_service.py for the
# "report" module. report.view/report.export already exist (Phase 1 catalog
# snapshot) and were already granted to every existing company's Admin/HR/
# Manager/Finance roles when those companies were created — only
# report.configure (Admin-only) is new here.
RETROACTIVE_GRANTS = {
    "Admin": ["configure"],
}


def upgrade() -> None:
    op.create_table(
        "saved_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("module", sa.String(20), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_saved_report_company_name"),
    )

    op.execute("ALTER TABLE saved_report ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE saved_report FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON saved_report
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
        [{"id": uuid.uuid4(), "module": "report", "action": action} for action in NEW_PERMISSIONS],
    )

    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, action FROM permission WHERE module = 'report'")
    ).fetchall()
    permission_id_by_action = {row.action: row.id for row in permission_rows}

    role_rows = connection.execute(sa.text("SELECT id, name FROM role WHERE name = 'Admin'")).fetchall()
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
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON saved_report")
    op.drop_table("saved_report")
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'report' AND action = 'configure')"
    )
    op.execute("DELETE FROM permission WHERE module = 'report' AND action = 'configure'")
