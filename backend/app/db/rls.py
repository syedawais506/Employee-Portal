"""Defense-in-depth: bind the current request's company_id to the Postgres
session so Row-Level Security policies enforce tenant isolation even if a
repository query forgets a company_id filter. See docs/HLD.md section 4.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_tenant_context(db: Session, company_id: str | None) -> None:
    # SET/SET LOCAL don't accept bind parameters in Postgres, so we use the
    # set_config() function instead. The third argument is false (i.e. NOT
    # scoped to just the current transaction, unlike SET LOCAL) deliberately:
    # a single request/script often spans multiple commits on the same
    # Session/connection (each service-layer call tends to end with its own
    # db.commit()), and SET LOCAL's value is wiped at every commit — the next
    # RLS-protected query after any such commit would silently see no tenant
    # context at all. A session-scoped set_config persists across commits on
    # this connection for the rest of its checkout; the next request to reuse
    # this pooled connection always calls this again (get_current_user) before
    # its own first query, so there's no cross-request leakage in practice.
    db.execute(
        text("SELECT set_config('app.current_company_id', :cid, false)"),
        {"cid": str(company_id) if company_id is not None else ""},
    )
