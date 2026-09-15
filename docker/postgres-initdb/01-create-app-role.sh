#!/usr/bin/env bash
# Runs once, automatically, only when the postgres container initializes a
# brand-new (empty) data volume — see the official postgres image's
# docker-entrypoint-initdb.d convention. Re-running against an
# already-initialized volume requires re-creating it (docker compose down -v)
# or applying this by hand.
#
# Why this role exists: POSTGRES_USER (see docker-compose.yml) is always a
# real Postgres superuser — that's just how the official postgres image's
# initdb works, there's no way to make the first/owning role anything else.
# Superusers unconditionally bypass Row-Level Security regardless of FORCE
# ROW LEVEL SECURITY (see the RLS policies created across alembic/versions/).
# So the app must connect at runtime as a genuinely restricted role for RLS
# to do anything at all. Migrations still run as POSTGRES_USER (DDL needs
# ownership privileges this role deliberately doesn't have) via
# MIGRATION_DATABASE_URL — see backend/alembic/env.py.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${APP_DB_USER} WITH LOGIN PASSWORD '${APP_DB_PASSWORD}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${APP_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${APP_DB_USER};

    -- No tables exist yet at initdb time (migrations run afterward) — these
    -- two GRANTs are a no-op today. ALTER DEFAULT PRIVILEGES below is what
    -- actually matters: it makes every table/sequence a *future* migration
    -- creates (owned by POSTGRES_USER) automatically grant these rights to
    -- ${APP_DB_USER} too, with no manual GRANT step needed per migration.
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${APP_DB_USER};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ${APP_DB_USER};

    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO ${APP_DB_USER};
EOSQL
