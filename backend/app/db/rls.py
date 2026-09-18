"""Defense-in-depth: bind the current request's company_id to the Postgres
session so Row-Level Security policies enforce tenant isolation even if a
repository query forgets a company_id filter. See docs/HLD.md section 4.
"""

import contextvars

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Mirrors whatever the current request last passed to set_tenant_context(),
# so the checkout listener below can re-apply it to any connection handed
# out later in the same request — see register_tenant_context_listener().
_current_company_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_company_id", default=None
)


def set_tenant_context(db: Session, company_id: str | None) -> None:
    value = str(company_id) if company_id is not None else ""
    _current_company_id.set(value)
    # SET/SET LOCAL don't accept bind parameters in Postgres, so we use the
    # set_config() function instead. The third argument is false (i.e. NOT
    # scoped to just the current transaction, unlike SET LOCAL) deliberately:
    # SET LOCAL's value is wiped at every commit, and a single request often
    # spans multiple commits on the same Session. Session-scoped set_config
    # survives commits too — but only on the one physical connection it's
    # applied to here. A Session releases its connection back to the pool on
    # every commit and transparently checks out a (possibly different) one
    # for the next query, so that alone isn't enough; see the checkout
    # listener below for what actually makes this correct across the whole
    # request.
    db.execute(
        text("SELECT set_config('app.current_company_id', :cid, false)"),
        {"cid": value},
    )


def register_tenant_context_listener(engine: Engine) -> None:
    """Re-applies the request's tenant context to every connection the pool
    hands out for the rest of the request, not just the one active when
    set_tenant_context() was first called.

    Without this, a mid-request db.commit() (routine — most service methods
    end with one) releases the Session's connection back to the pool; the
    next query on that same Session can be handed a *different* physical
    connection that never had app.current_company_id set. RLS then silently
    filters out rows that genuinely belong to the caller's own tenant — e.g.
    a role that plainly exists comes back "not found" purely because the
    second lookup after the permissions-save commit landed on a fresh
    connection. See the role-permissions save bug in docs/CHANGELOG.md.
    """

    @event.listens_for(engine, "checkout")
    def _apply_tenant_context(dbapi_connection, connection_record, connection_proxy) -> None:  # noqa: ANN001
        value = _current_company_id.get()
        if value is None:
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("SELECT set_config('app.current_company_id', %s, false)", (value,))
        finally:
            cursor.close()
