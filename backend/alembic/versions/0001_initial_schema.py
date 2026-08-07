"""initial schema: company, department, user_account, employee, role/permission, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen snapshot of PERMISSION_CATALOG as it existed when this migration was
# written. Migrations must never import live application state (e.g. from
# app.services.role_service) — that dict grows in later phases (see 0002_*),
# and importing it here would silently reseed whatever it currently contains
# instead of what Phase 1 actually shipped, breaking replay on a fresh DB.
PERMISSION_CATALOG_AT_0001: dict[str, list[str]] = {
    "employee": ["view", "create", "update", "delete", "export", "import"],
    "department": ["view", "create", "update", "delete"],
    "role": ["view", "create", "update", "delete"],
    "company": ["view", "create", "update", "delete"],
    "project": ["view", "create", "update", "delete", "export"],
    "timesheet": ["view", "create", "update", "delete", "approve", "reject", "export"],
    "leave": ["view", "create", "update", "delete", "approve", "reject"],
    "asset": ["view", "create", "update", "delete"],
    "report": ["view", "export"],
}


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("subdomain", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_company_slug"),
        sa.UniqueConstraint("subdomain", name="uq_company_subdomain"),
    )

    op.create_table(
        "department",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("department.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cost_center_code", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_department_company_name"),
    )

    op.create_table(
        "user_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default="local"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_user_account_email"),
    )
    op.create_index("ix_user_account_email", "user_account", ["email"])

    op.create_table(
        "employee",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_code", sa.String(50), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("department.id", ondelete="SET NULL"), nullable=True),
        sa.Column("designation", sa.String(150), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employee.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employment_type", sa.String(30), nullable=False, server_default="full_time"),
        sa.Column("joining_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_employee_user_id"),
        sa.UniqueConstraint("company_id", "employee_code", name="uq_employee_company_code"),
    )
    op.create_index("ix_employee_company_status", "employee", ["company_id", "status"])
    op.create_index("ix_employee_company_department", "employee", ["company_id", "department_id"])
    op.create_index("ix_employee_company_manager", "employee", ["company_id", "manager_id"])

    op.create_table(
        "permission",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("module", sa.String(50), nullable=False, index=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.UniqueConstraint("module", "action", name="uq_permission_module_action"),
    )

    op.create_table(
        "role",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "name", name="uq_role_company_name"),
    )

    op.create_table(
        "role_permission",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "user_role",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_type", sa.String(100), nullable=False, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_company_created", "audit_log", ["company_id", "created_at"])
    op.create_index("ix_audit_log_company_entity", "audit_log", ["company_id", "entity_type", "entity_id"])

    # Seed the static permission catalog (module, action) — the single source
    # of truth for what can be granted to a role. See docs/LLD.md section 3.
    permission_table = sa.table(
        "permission",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
    )
    import uuid

    rows = [
        {"id": uuid.uuid4(), "module": module, "action": action}
        for module, actions in PERMISSION_CATALOG_AT_0001.items()
        for action in actions
    ]
    op.bulk_insert(permission_table, rows)

    # Row-Level Security: defense-in-depth behind repository-layer tenant
    # scoping. See docs/HLD.md section 4 and docs/DATABASE_SCHEMA.md.
    for table in ("department", "employee", "role", "audit_log"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE makes the policy apply even to the table owner — the role
        # migrations/the app connect as. Without FORCE, RLS is a no-op for
        # whichever role owns the table. It still does NOT apply to Postgres
        # superusers or roles with BYPASSRLS, so production must run the app
        # under a non-superuser, non-BYPASSRLS role for this to actually
        # constrain queries (see docs/HLD.md section 4 and README security notes).
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        nullable_clause = (
            "company_id IS NULL OR " if table == "role" else ""
        )
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING ({nullable_clause}company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for table in ("department", "employee", "role", "audit_log"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("audit_log")
    op.drop_table("user_role")
    op.drop_table("role_permission")
    op.drop_table("role")
    op.drop_table("permission")
    op.drop_table("employee")
    op.drop_table("user_account")
    op.drop_table("department")
    op.drop_table("company")
