"""department.export permission; grant it + the already-catalogued
project.export to Admin (Admin never actually had project.export despite it
being seeded in migration 0001 — a fresh company created before this pass
would have had the same gap, so existing companies need the retroactive grant)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-14 00:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    permission_table = sa.table(
        "permission",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
    )
    op.bulk_insert(permission_table, [{"id": uuid.uuid4(), "module": "department", "action": "export"}])

    connection = op.get_bind()
    permission_rows = connection.execute(
        sa.text("SELECT id, module, action FROM permission WHERE (module, action) IN "
                "(('department', 'export'), ('project', 'export'))")
    ).fetchall()
    permission_ids = [row.id for row in permission_rows]

    admin_role_ids = connection.execute(sa.text("SELECT id FROM role WHERE name = 'Admin'")).scalars().all()
    for role_id in admin_role_ids:
        for permission_id in permission_ids:
            connection.execute(
                sa.text(
                    "INSERT INTO role_permission (role_id, permission_id) VALUES (:role_id, :permission_id) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'department' AND action = 'export')"
    )
    op.execute("DELETE FROM permission WHERE module = 'department' AND action = 'export'")
    op.execute(
        "DELETE FROM role_permission WHERE permission_id IN "
        "(SELECT id FROM permission WHERE module = 'project' AND action = 'export') "
        "AND role_id IN (SELECT id FROM role WHERE name = 'Admin')"
    )
