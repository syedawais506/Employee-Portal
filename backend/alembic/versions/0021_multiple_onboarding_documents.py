"""Allow multiple files per document type per employee during onboarding.

Drops uq_employee_document_type (employee_id, document_type_id), the
constraint that limited an employee to exactly one uploaded file per
document type — HR now needs employees to be able to upload several files
under one category (e.g. multiple "Education" documents) without one
overwriting another. Storage keys were already unique per upload (see
app/utils/storage.py build_document_key), so existing files are unaffected;
only the database was enforcing one-row-per-type.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-24 00:00:01

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_employee_document_type", "employee_document", type_="unique")


def downgrade() -> None:
    # Re-adding this constraint would fail if any employee now has more than
    # one document row for the same type (the expected state after this
    # feature ships) — downgrading past this point requires manually
    # deduplicating employee_document rows first.
    op.create_unique_constraint(
        "uq_employee_document_type", "employee_document", ["employee_id", "document_type_id"]
    )
