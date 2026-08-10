# Employee Portal — Multi-Tenant SaaS

A commercial-grade, multi-tenant Employee Management Portal (Zoho People–style), built to eventually serve multiple independent customer companies from a single deployment with fully isolated data.

**Phases 1, 2 & 3 are shipped**: multi-tenant data model, authentication, dynamic RBAC/permission engine, Company/Department/Employee management, a full employee onboarding workflow (configurable document checklist, secure onboarding links, HR review, Admin activation, offer letters), and Projects & Employee Mapping (clients, project CRUD, team assignment, self-service "my projects" view) — fully wired end-to-end (React UI → FastAPI → PostgreSQL) rather than shallow-stubbed across every module. See [docs/ROADMAP.md](docs/ROADMAP.md) for what ships in later phases (timesheets, leave, assets, reports, notifications, attendance, billing, AI features).

## Documentation

| Document | Contents |
|---|---|
| [docs/SRS.md](docs/SRS.md) | Software Requirements Specification — functional & non-functional requirements, acceptance criteria |
| [docs/HLD.md](docs/HLD.md) | High-Level Design — architecture, multi-tenancy strategy, deployment view |
| [docs/LLD.md](docs/LLD.md) | Low-Level Design — auth flow, RBAC engine, tenant enforcement, module internals |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | ER diagram and table definitions |
| [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) | REST API contract (also live at `/docs` via Swagger) |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phased delivery plan, scope cuts and rationale per phase |

## Tech Stack

**Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth, Celery + Redis, PostgreSQL 16 (with Row-Level Security as defense-in-depth), boto3 (S3/MinIO document storage), ReportLab (offer letter PDFs)
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

### Try the onboarding workflow

Each demo company already has a **Taylor NewHire** employee sitting in the review queue with documents submitted and awaiting HR review — log in as `admin@acme-demo.com` (or an `hr@...` account) and open **Onboarding** in the sidebar to review their documents and walk them through HR approval → account activation.

To try the new-hire side of the flow yourself:
1. As an Admin/HR user, create a new employee under **Employees → New Employee**.
2. Open MailHog (http://localhost:8025) — the onboarding invite email (with a link to `/onboarding/<token>`) lands there instead of a real inbox.
3. Open that link in an incognito/private window (it's an unauthenticated page) to set a password and upload the required documents as the new hire would.
4. Back in the main app, go to **Onboarding** to review the documents, mark them HR-reviewed, then activate the account — the new hire can then log in with the password they set.

### Try Projects

Each demo company already has a client ("Northwind Trading Co") and two projects — a billable client project and an internal one, both with team members assigned. Log in as `admin@acme-demo.com` and open **Projects** in the sidebar to see the full management view (create/edit projects, manage clients from the "Clients" tab, add/remove team members). Log in as `employee@acme-demo.com` instead to see the same nav item resolve to a read-only "My Projects" view showing only what that employee is assigned to — no budget or client info, matching what a plain Employee role can see.

### Sending real email (instead of MailHog)

By default every email (onboarding invites, password resets) is captured locally by MailHog at http://localhost:8025 and never reaches a real inbox — that's intentional for local dev. To send real email:

1. Get SMTP credentials from a provider. Any of these work since the app just uses standard SMTP with optional STARTTLS:
   - **SendGrid**: host `smtp.sendgrid.net`, port `587`, user `apikey`, password = your SendGrid API key.
   - **Mailgun**: host `smtp.mailgun.org`, port `587`, user/password from your Mailgun domain's SMTP credentials.
   - **AWS SES**: host `email-smtp.<region>.amazonaws.com`, port `587`, user/password = SES SMTP credentials (not your AWS IAM keys — generate these separately in the SES console).
   - **Gmail** (fine for quick testing, not for production volume): host `smtp.gmail.com`, port `587`, user = your Gmail address, password = a 16-character [App Password](https://myaccount.google.com/apppasswords) (requires 2FA enabled — your normal Gmail password won't work).
2. Edit `docker/.env` and fill in (AWS SES example — swap host/user/password for your provider):
   ```
   SMTP_HOST=email-smtp.us-east-1.amazonaws.com
   SMTP_PORT=587
   SMTP_USER=your-ses-smtp-username
   SMTP_PASSWORD=your-ses-smtp-password
   SMTP_USE_TLS=true
   SMTP_FROM_EMAIL=onboarding@yourcompany.com
   SMTP_FROM_NAME=Employee Portal
   ```
   `SMTP_FROM_NAME` is optional — it sets the display name recipients see (e.g. "Employee Portal <onboarding@yourcompany.com>") instead of just the bare address.

   Most providers (SendGrid, Mailgun, SES) require `SMTP_FROM_EMAIL` to be a verified sender/domain, or the send will be rejected even with correct credentials. For SES specifically: the SMTP username/password are **not** your AWS access key/secret — generate them separately under SES → "SMTP settings" → "Create SMTP credentials", and the sending address/domain must be verified in that same SES account/region.
3. Recreate the backend and worker so they pick up the new env vars (a `restart` alone won't do it — the values are baked in at container creation):
   ```bash
   docker compose -f docker/docker-compose.yml up -d --force-recreate backend celery-worker
   ```
4. Trigger a real send (e.g. create a new employee, or use **Forgot password**) and check the **celery-worker** logs if it doesn't arrive — failed sends are logged there, not surfaced to the UI, since email delivery is fire-and-forget by design:
   ```bash
   docker compose -f docker/docker-compose.yml logs -f celery-worker
   ```

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

The backend test suite includes a dedicated cross-tenant-isolation suite (`backend/tests/integration/test_tenant_isolation.py`) that asserts, through the real HTTP API, that one company's Admin cannot read, list, update, or delete another company's data, a full onboarding-workflow suite (`test_onboarding.py`) covering invite → password → document upload → HR review → Admin activation, and a projects suite (`test_projects.py`) covering CRUD, member assignment, cross-tenant rejection, and the self-service "my projects" view.

## Security Notes for Deployment

- Rotate `SECRET_KEY` and every demo password before exposing this beyond local development.
- Postgres Row-Level Security is enabled on tenant tables as defense-in-depth behind the repository-layer tenant scoping, but RLS only constrains non-superuser, non-`BYPASSRLS` roles — see [docs/HLD.md §4](docs/HLD.md#4-multi-tenancy-strategy) for what's required in production for RLS to be a genuine second layer rather than a no-op.
- `CORS_ORIGINS`, `SMTP_*`, and `S3_*` in `docker/.env` / `backend/.env` all need real values outside local dev.
- TLS termination is not configured in the provided Nginx configs — add it (or terminate TLS at a load balancer in front of this stack) before serving real traffic.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the phase-by-phase plan: projects, timesheets, leave management, assets, reporting, notifications, attendance, subscription/billing, and AI features. Each phase builds on the Phase 1 & 2 foundation without requiring breaking schema changes.
