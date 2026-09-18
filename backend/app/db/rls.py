"""Defense-in-depth: bind the current request's company_id to the Postgres
session so Row-Level Security policies enforce tenant isolation even if a
repository query forgets a company_id filter. See docs/HLD.md section 4.
"""

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, SessionTransaction

_INFO_KEY = "tenant_company_id"


def set_tenant_context(db: Session, company_id: str | None) -> None:
    value = str(company_id) if company_id is not None else ""
    # Session.info is a plain dict living on the Session object itself, not
    # on any ambient thread/task context — unlike a contextvar, it can't go
    # stale just because FastAPI happens to run a later sync dependency (or
    # the endpoint body) in a different worker thread than this one. See
    # _reapply_after_begin below for why that distinction is the whole fix.
    db.info[_INFO_KEY] = value
    db.execute(
        text("SELECT set_config('app.current_company_id', :cid, false)"),
        {"cid": value},
    )


@event.listens_for(Session, "after_begin")
def _reapply_after_begin(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
    """Re-applies the request's tenant context at the start of every
    transaction a Session opens, not just the first one.

    A Session's connection is released back to the pool on every commit; the
    next query on that same Session silently opens a new transaction — on a
    connection that may be physically different — which is exactly what
    Session.commit() does in the middle of any service method that commits
    and then does another RLS-protected read (e.g. RoleService.
    update_permissions re-fetching the role right after saving its
    permissions). Without this, that later query can run with no tenant
    context at all and RLS quietly filters out rows that plainly belong to
    the caller's own company — "Role not found" for a role that exists.

    This has to be a Session event (reading session.info) rather than a Pool
    checkout event keyed off a contextvar: FastAPI resolves each sync
    dependency (get_current_user, get_current_company_id, the endpoint body,
    ...) via its own run_in_threadpool call, each with its own copied
    context, so a contextvar set in one doesn't reliably reach the next.
    session.info lives on the Session instance itself, which FastAPI's
    dependency caching guarantees is the same object throughout the request
    regardless of which worker thread touches it.
    """
    value = session.info.get(_INFO_KEY)
    if value is None:
        return
    connection.execute(
        text("SELECT set_config('app.current_company_id', :cid, false)"),
        {"cid": value},
    )
