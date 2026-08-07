"""onboarding: document_type, employee_document, onboarding_invite, employee.onboarding_status

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-01 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = ["view", "review", "approve", "configure"]

# Mirrors DEFAULT_ROLE_PERMISSIONS in app/services/role_service.py for the
# "onboarding" module only — used to retroactively grant existing companies'
# system roles the same defaults a brand-new company gets automatically.
RETROACTIVE_GRANTS = {
    "Admin": ["view", "review", "approve", "configure"],
    "HR": ["view", "review"],
}


def upgrade() -> None:
    op.add_column(
        "employee",
        sa.Column("onboarding_status", sa.String(20), nullable=False, server_default="completed"),
    )

    op.create_table(
        "document_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_document_type_company_name"),
    )

    op.create_table(
        "employee_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_type.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.String(500), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "document_type_id", name="uq_employee_document_type"),
    )

    op.create_table(
        "onboarding_invite",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_onboarding_invite_token_hash", "onboarding_invite", ["token_hash"])

    for table in ("document_type", "employee_document", "onboarding_invite"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
            """
        )

    # Seed the new "onboarding" permission catalog rows.
    permission_table = sa.table(
        "permission",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
    )
    op.bulk_insert(
        permission_table,
        [{"id": uuid.uuid4(), "module": "onboarding", "action": action} for action in NEW_PERMISSIONS],
    )

    # Retroactively grant the new permissions to existing companies' system
    # roles, matching what a brand-new company gets automatically — see
    # RETROACTIVE_GRANTS above and DEFAULT_ROLE_PERMISSIONS in role_service.py.
    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, action FROM permission WHERE module = 'onboarding'")
    ).fetchall()
    permission_id_by_action = {row.action: row.id for row in permission_rows}

    role_rows = connection.execute(
        sa.text("SELECT id, name FROM role WHERE name IN ('Admin', 'HR')")
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
    for table in ("document_type", "employee_document", "onboarding_invite"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("onboarding_invite")
    op.drop_table("employee_document")
    op.drop_table("document_type")
    op.execute("DELETE FROM role_permission WHERE permission_id IN (SELECT id FROM permission WHERE module = 'onboarding')")
    op.execute("DELETE FROM permission WHERE module = 'onboarding'")
    op.drop_column("employee", "onboarding_status")
