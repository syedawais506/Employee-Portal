"""digests and webhooks: company.slack_webhook_url, employee_document.expiry_date,
new company.configure permission (Admin-only, self-scoped tenant settings —
distinct from company.update which remains Super-Admin-only cross-tenant management)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-29 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen literal snapshot — do NOT import the live PERMISSION_CATALOG/DEFAULT_ROLE_PERMISSIONS
# dicts from app.services.role_service here. Only the action that's genuinely new at this
# migration (verified against the 0001 frozen snapshot) is listed.
NEW_PERMISSIONS: dict[str, list[str]] = {
    "company": ["configure"],
}

RETROACTIVE_GRANTS: dict[str, list[str]] = {
    "Admin": ["configure"],
}


def upgrade() -> None:
    op.add_column("company", sa.Column("slack_webhook_url", sa.String(500), nullable=True))
    op.add_column("employee_document", sa.Column("expiry_date", sa.Date(), nullable=True))

    conn = op.get_bind()

    permission_ids: dict[str, uuid.UUID] = {}
    for module, actions in NEW_PERMISSIONS.items():
        for action in actions:
            permission_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    "INSERT INTO permission (id, module, action) VALUES (:id, :module, :action)"
                ),
                {"id": permission_id, "module": module, "action": action},
            )
            permission_ids[f"{module}.{action}"] = permission_id

    for role_name, actions in RETROACTIVE_GRANTS.items():
        role_rows = conn.execute(
            sa.text("SELECT id FROM role WHERE name = :name"), {"name": role_name}
        ).fetchall()
        for action in actions:
            permission_id = permission_ids["company." + action]
            for (role_id,) in role_rows:
                conn.execute(
                    sa.text(
                        "INSERT INTO role_permission (role_id, permission_id) VALUES (:role_id, :permission_id)"
                    ),
                    {"role_id": role_id, "permission_id": permission_id},
                )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM permission WHERE module = 'company' AND action = 'configure'"))
    op.drop_column("employee_document", "expiry_date")
    op.drop_column("company", "slack_webhook_url")
