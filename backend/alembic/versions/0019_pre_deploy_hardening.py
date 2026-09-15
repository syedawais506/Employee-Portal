"""Pre-deployment hardening: indexes on the `status` columns that every
approval-queue query (and now every admin Ask HR message) filters on —
`leave_request.status` and `timesheet_submission.status` had none before.

Also removes RLS from `onboarding_invite`: it's looked up by its random
token hash (app/services/onboarding_service.py's _resolve_invite) *before*
the caller's company_id is known — that's the whole point of a public,
token-authenticated invite link, with the unguessable token itself as the
access control, same reasoning that already exempts `user_account` and
`company` from RLS (both are also looked up before a company context
exists). With RLS forced on this table there's no valid company_id to set
in the session before this very first lookup, so the lookup itself would
always return zero rows once RLS is actually enforced (see docs/ROADMAP.md's
pre-deployment audit entry) — this table was RLS'd in 0002 along with
document_type/employee_document without accounting for that ordering
problem specifically for onboarding_invite.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-15 00:00:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_leave_request_status", "leave_request", ["status"])
    op.create_index("ix_timesheet_submission_status", "timesheet_submission", ["status"])

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON onboarding_invite")
    op.execute("ALTER TABLE onboarding_invite NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE onboarding_invite DISABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE onboarding_invite ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE onboarding_invite FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON onboarding_invite
        USING (company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid)
        """
    )

    op.drop_index("ix_timesheet_submission_status", table_name="timesheet_submission")
    op.drop_index("ix_leave_request_status", table_name="leave_request")
