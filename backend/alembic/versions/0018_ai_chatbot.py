"""HR FAQ chatbot: company.ai_chatbot_enabled (nullable=false, default off,
same per-company opt-in convention as require_hr_leave_approval /
slack_webhook_url). No new permissions — the admin toggle reuses
company.configure, the employee-facing chat endpoint is self-scoped
(authenticated, no permission needed). See docs/ROADMAP.md Phase 13.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-08 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("ai_chatbot_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("company", "ai_chatbot_enabled")
