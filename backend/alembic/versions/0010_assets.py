"""assets: asset_type, asset, asset_assignment; asset.export permission +
retroactive grants (Admin already had view/create/update/delete from the
Phase 1 catalog stub — only export is new; HR/Manager get their first-ever
asset grants here)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-26 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = ["export"]

# Mirrors DEFAULT_ROLE_PERMISSIONS in app/services/role_service.py for the
# "asset" module only. Admin already holds view/create/update/delete from the
# Phase 1 catalog stub (asset.* was pre-declared but unused before this
# phase), so only export is new for Admin — HR and Manager get their first
# asset grants at all here.
RETROACTIVE_GRANTS = {
    "Admin": ["export"],
    "HR": ["view", "create", "update", "export"],
    "Manager": ["view"],
}


def upgrade() -> None:
    op.create_table(
        "asset_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_asset_type_company_name"),
    )

    op.create_table(
        "asset",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset_type.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("asset_tag", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("warranty_expiry", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "asset_tag", name="uq_asset_company_tag"),
    )

    op.create_table(
        "asset_assignment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    for table in ("asset_type", "asset", "asset_assignment"):
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
        [{"id": uuid.uuid4(), "module": "asset", "action": action} for action in NEW_PERMISSIONS],
    )

    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, action FROM permission WHERE module = 'asset'")
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
    for table in ("asset_type", "asset", "asset_assignment"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("asset_assignment")
    op.drop_table("asset")
    op.drop_table("asset_type")
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'asset' AND action = 'export')"
    )
    op.execute("DELETE FROM permission WHERE module = 'asset' AND action = 'export'")
