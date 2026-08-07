"""Defense-in-depth: bind the current request's company_id to the Postgres
session so Row-Level Security policies enforce tenant isolation even if a
repository query forgets a company_id filter. See docs/HLD.md section 4.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_tenant_context(db: Session, company_id: str | None) -> None:
    # SET/SET LOCAL don't accept bind parameters in Postgres, so we use the
    # set_config() function instead — its third argument (true) scopes the
    # setting to the current transaction, equivalent to SET LOCAL.
    db.execute(
        text("SELECT set_config('app.current_company_id', :cid, true)"),
        {"cid": str(company_id) if company_id is not None else ""},
    )
