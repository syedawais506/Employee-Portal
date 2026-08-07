# Database

The schema is authored and versioned as Alembic migrations in [`backend/alembic/versions/`](../backend/alembic/versions/) — that is the single source of truth (`alembic upgrade head` applies it; `alembic downgrade` reverts it). This directory does not duplicate DDL to avoid the two drifting apart.

- ER diagram and table-by-table reference: [`docs/DATABASE_SCHEMA.md`](../docs/DATABASE_SCHEMA.md)
- Seed / demo data: [`backend/scripts/seed.py`](../backend/scripts/seed.py) (run via `python -m scripts.seed` or `scripts/seed.sh`)

Reserve this directory for standalone SQL assets that don't belong in a migration — e.g. one-off analytics views, backup/restore scripts, or data-warehouse export definitions — as those needs arise in later phases.
