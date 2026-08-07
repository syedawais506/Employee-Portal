# Employee Portal — Multi-Tenant SaaS

A commercial-grade, multi-tenant Employee Management Portal (Zoho People–style), built to eventually serve multiple independent customer companies from a single deployment with fully isolated data.

**This is Phase 1** of a multi-phase build: multi-tenant data model, authentication, dynamic RBAC/permission engine, and Company/Department/Employee management — fully wired end-to-end (React UI → FastAPI → PostgreSQL) rather than shallow-stubbed across every module. See [docs/ROADMAP.md](docs/ROADMAP.md) for what ships in later phases (onboarding, projects, timesheets, leave, assets, reports, notifications, attendance, billing, AI features).

## Documentation

| Document | Contents |
|---|---|
| [docs/SRS.md](docs/SRS.md) | Software Requirements Specification — functional & non-functional requirements, acceptance criteria |
| [docs/HLD.md](docs/HLD.md) | High-Level Design — architecture, multi-tenancy strategy, deployment view |
| [docs/LLD.md](docs/LLD.md) | Low-Level Design — auth flow, RBAC engine, tenant enforcement, module internals |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | ER diagram and table definitions |
| [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) | REST API contract (also live at `/docs` via Swagger) |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phased delivery plan, Phase 1 scope cut and rationale |

## Tech Stack

**Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth, Celery + Redis, PostgreSQL 16 (with Row-Level Security as defense-in-depth)
**Frontend:** React 19, TypeScript, Vite, MUI, TanStack Query, React Hook Form, React Router, Zustand, Recharts
**Infra:** Docker, Docker Compose, Nginx, GitHub Actions CI, MinIO (S3-compatible, dev), MailHog (SMTP capture, dev)

## Project Structure

```
backend/    FastAPI app — clean architecture: api → services → repositories → models
frontend/   React SPA — feature-sliced: features/{auth,employees,departments,roles,companies}
database/   (reserved for standalone SQL/seed assets outside Alembic)
docker/     docker-compose.yml, gateway Nginx config
docs/       SRS, HLD, LLD, schema, API contracts, roadmap
scripts/    convenience scripts (migrate, seed, dev-up, run-tests)
```

## Quick Start (Docker — recommended)

Requires Docker and Docker Compose.

```bash
./scripts/dev-up.sh
```

This copies `docker/.env.example` to `docker/.env` (edit it first if you want non-default secrets), builds and starts every service, runs migrations, and seeds demo data. When it finishes:

| URL | What |
|---|---|
| http://localhost:8080 | The app (frontend + API, same origin via the gateway) |
| http://localhost:8080/docs | Swagger / OpenAPI docs |
| http://localhost:8025 | MailHog — view password-reset/verification emails sent in dev |
| http://localhost:9001 | MinIO console (`minioadmin` / `minioadmin` by default) |

### Demo credentials

Seeded by `python -m scripts.seed` (already run by `dev-up.sh`):

| Role | Email | Password |
|---|---|---|
| Super Admin | `superadmin@employee-portal-demo.com` | `SuperAdmin@12345` |
| Acme Corp — Admin | `admin@acme-demo.com` | `Demo@12345` |
| Acme Corp — Manager | `manager@acme-demo.com` | `Demo@12345` |
| Acme Corp — Employee | `employee@acme-demo.com` | `Demo@12345` |
| Acme Corp — HR | `hr@acme-demo.com` | `Demo@12345` |
| Acme Corp — Finance | `finance@acme-demo.com` | `Demo@12345` |
| Globex Inc — (same 5 roles) | `<role>@globex-demo.com` | `Demo@12345` |

Log in as `admin@acme-demo.com` and `admin@globex-demo.com` in two browser sessions to see tenant isolation firsthand — neither can see the other's employees, departments, or roles.

**Change these credentials before any non-local deployment.**

### Stopping / resetting

```bash
docker compose -f docker/docker-compose.yml down          # stop
docker compose -f docker/docker-compose.yml down -v        # stop + wipe volumes (fresh DB next time)
```

## Local Development (without Docker)

### Backend

```bash
cd backend
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # point DATABASE_URL/REDIS_URL at your local Postgres/Redis
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`; Swagger at `/docs`. Health checks are unversioned: `/health`, `/health/ready`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL defaults to /api/v1 via the Vite dev proxy
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api` to `http://localhost:8000` (configurable via `VITE_API_PROXY_TARGET`).

### Running tests

```bash
./scripts/run-tests.sh          # backend: ruff + mypy + pytest (needs Postgres + Redis reachable)
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
```

The backend test suite includes a dedicated cross-tenant-isolation suite (`backend/tests/integration/test_tenant_isolation.py`) that asserts, through the real HTTP API, that one company's Admin cannot read, list, update, or delete another company's data.

## Security Notes for Deployment

- Rotate `SECRET_KEY` and every demo password before exposing this beyond local development.
- Postgres Row-Level Security is enabled on tenant tables as defense-in-depth behind the repository-layer tenant scoping, but RLS only constrains non-superuser, non-`BYPASSRLS` roles — see [docs/HLD.md §4](docs/HLD.md#4-multi-tenancy-strategy) for what's required in production for RLS to be a genuine second layer rather than a no-op.
- `CORS_ORIGINS`, `SMTP_*`, and `S3_*` in `docker/.env` / `backend/.env` all need real values outside local dev.
- TLS termination is not configured in the provided Nginx configs — add it (or terminate TLS at a load balancer in front of this stack) before serving real traffic.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the phase-by-phase plan: onboarding & documents, projects, timesheets, leave management, assets, reporting, notifications, attendance, subscription/billing, and AI features. Each phase builds on this Phase 1 foundation without requiring breaking schema changes.
