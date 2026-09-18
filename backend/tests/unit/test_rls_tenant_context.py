"""These don't exercise real RLS policies (the test DB is built with
Base.metadata.create_all(), not the Alembic migrations that define the
policies — see docs/HLD.md). What they do verify is the mechanism RLS relies
on: that app.current_company_id, once set via set_tenant_context(), stays
correct even if the Session's Session-to-connection binding changes mid-test
(e.g. after a commit releases the connection back to the pool). Without the
checkout listener, this is exactly the gap that let update_permissions()'s
post-commit re-fetch of a role silently 404 despite the role genuinely
belonging to the caller's own company.
"""

from sqlalchemy import text

from app.db.rls import set_tenant_context
from app.db.session import SessionLocal, engine


def test_tenant_context_survives_a_connection_pool_swap():
    db = SessionLocal()
    try:
        set_tenant_context(db, "11111111-1111-1111-1111-111111111111")
        db.commit()

        # Forces the next checkout onto a brand-new physical connection —
        # the worst case the checkout listener has to handle, since a fresh
        # connection has never had app.current_company_id set at all.
        engine.dispose(close=False)

        current = db.execute(text("SELECT current_setting('app.current_company_id', true)")).scalar()
        assert current == "11111111-1111-1111-1111-111111111111"
    finally:
        db.close()
