"""white-label branding & company tour: company.logo_key, company.primary_color,
company_tour_step table. No new permissions — CRUD reuses the existing
onboarding.view/configure gates, since this is onboarding-flow configuration.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-04 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("company", sa.Column("logo_key", sa.String(512), nullable=True))
    op.add_column("company", sa.Column("primary_color", sa.String(20), nullable=True))

    op.create_table(
        "company_tour_step",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("image_key", sa.String(512), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.execute("ALTER TABLE company_tour_step ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE company_tour_step FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON company_tour_step
        USING (company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON company_tour_step")
    op.drop_table("company_tour_step")
    op.drop_column("company", "primary_color")
    op.drop_column("company", "logo_key")
