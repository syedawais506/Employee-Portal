# Software Requirements Specification (SRS)

## Employee Management Portal — Multi-Tenant SaaS

**Document version:** 1.0
**Status:** Phase 0 — Baseline
**Related documents:** [HLD.md](./HLD.md), [LLD.md](./LLD.md), [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md), [API_CONTRACTS.md](./API_CONTRACTS.md), [ROADMAP.md](./ROADMAP.md)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for a commercial, multi-tenant Employee Management Portal ("the Platform"), comparable in scope to Zoho People, sold as a SaaS product to multiple independent customer organizations ("Companies" / "Tenants") from a single deployment.

### 1.2 Scope

The Platform provides, per tenant: employee lifecycle management, onboarding, org structure (departments/projects/cost centers), timesheets, leave management, asset tracking, reporting, notifications, and role-based dashboards. A Super Admin layer manages tenants, subscriptions, and global platform configuration. The system is built for eventual resale as a licensed SaaS product with per-tenant billing/subscription hooks.

This SRS covers the full target scope. **Delivery is phased** — see [ROADMAP.md](./ROADMAP.md) for what ships in each phase. Phase 1 (this implementation pass) delivers: multi-tenant data model, authentication, RBAC/permission engine, Company/Department/Employee CRUD, and the frontend application shell. Modules marked "(Future)" below are specified now for architectural completeness but not implemented in Phase 1.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Tenant / Company | An isolated customer organization using the platform |
| Super Admin | Platform operator, manages tenants; not a member of any tenant |
| RBAC | Role-Based Access Control |
| Row-Level Isolation | Enforcing `company_id` scoping on every tenant-owned row |
| JWT | JSON Web Token, used for stateless auth |

### 1.4 Intended Audience

Engineering (backend/frontend/DevOps), QA, and product stakeholders implementing or extending the platform.

---

## 2. Overall Description

### 2.1 Product Perspective

Greenfield product. Backend is a FastAPI monolith organized by clean-architecture layers (API → Service → Repository → ORM), deployed behind Nginx, backed by PostgreSQL, Redis (cache/broker), and S3-compatible object storage (MinIO in dev). Frontend is a React SPA consuming a versioned REST API.

### 2.2 Tenancy Model

**Strategy: shared database, shared schema, discriminator column** (`company_id` on every tenant-scoped table), enforced at the ORM/repository layer, not the database-connection layer. Rationale documented in [HLD.md §4](./HLD.md#4-multi-tenancy-strategy). This is the standard, cost-effective approach for a SaaS product at this stage; schema-per-tenant or database-per-tenant is deferred to a future scaling phase if a customer requires it contractually (documented as an option in the roadmap, not built now).

Hierarchy:

```
Platform (Super Admin)
 └─ Company (Tenant)
     ├─ Departments
     ├─ Cost Centers
     ├─ Projects
     ├─ Roles & Permissions (tenant-customizable)
     └─ Employees (Users)
```

Every tenant-owned row carries `company_id`. No query may cross a `company_id` boundary except from the Super Admin context, which operates in a separate, explicitly-marked code path.

### 2.3 User Classes and Characteristics

| Role | Scope | Summary capability |
|---|---|---|
| Super Admin | Platform-wide | Create/delete companies, manage subscriptions/licenses, global settings |
| Admin | Company | Manage employees, departments, projects, leave/timesheet policy, roles/permissions |
| HR | Company | Onboarding, document management, offer letters, exit process |
| Manager | Team (reports-to graph) | Approve timesheets/leave, team dashboard, assign projects |
| Employee | Self | Timesheets, leave requests, documents, profile, assigned projects |
| Finance | Company | Billing/costing reports, billable hours, client reports |

Capabilities are not hardcoded to role names beyond sane defaults — see §2.5 Permission Model.

### 2.4 Operating Environment

- Backend: Python 3.13+, FastAPI, Uvicorn/Gunicorn workers, PostgreSQL 16, Redis 7
- Frontend: modern evergreen browsers (Chrome, Edge, Firefox, Safari — last 2 versions), responsive down to 375px width
- Deployment: Docker containers behind Nginx reverse proxy; GitHub Actions for CI/CD

### 2.5 Permission Model (Dynamic RBAC)

Permissions are **not** hardcoded per role. The system defines:

- **Modules** (e.g. `employee`, `timesheet`, `leave`, `project`, `report`, `asset`)
- **Actions** per module (`view`, `create`, `update`, `delete`, `export`, `import`, `approve`, `reject`)
- **Roles** are tenant-scoped, named collections of `(module, action)` grants
- **Role assignment** maps a User to one or more Roles within their Company

Five roles above are seeded as defaults per new Company (non-deletable "system" roles for Admin/Super Admin only; others editable), but an Admin can create custom roles and toggle grants from a UI grid — no code change required. See [LLD.md §3](./LLD.md#3-rbac--permission-engine).

### 2.6 Constraints

- All tenant data must be logically isolated; a cross-tenant data leak is a Sev-1 defect.
- Passwords stored using bcrypt/argon2; never logged or returned in any API response.
- All list endpoints must be paginated; no unbounded `SELECT *` across a tenant's full table.
- API is versioned (`/api/v1/...`) from day one to allow non-breaking evolution.

### 2.7 Assumptions and Dependencies

- Single platform-level PostgreSQL instance is sufficient for target scale (validated up to ~5,000 companies / ~500 employees each before re-evaluating tenancy strategy).
- SMTP provider and S3-compatible storage are externally provisioned in production (MinIO used only for local/dev parity).

---

## 3. Functional Requirements

Each requirement is tagged `[P1]` (Phase 1, implemented now) or `[FUT]` (specified, future phase per roadmap).

### FR-1 Authentication & Session Management
- FR-1.1 `[P1]` Email + password login issuing short-lived access JWT + long-lived refresh JWT (rotated on use).
- FR-1.2 `[P1]` Logout revokes the refresh token (server-side denylist in Redis).
- FR-1.3 `[P1]` Forgot password → emailed time-limited reset token → password reset.
- FR-1.4 `[P1]` Email verification on account creation.
- FR-1.5 `[P1]` "Remember me" extends refresh-token lifetime.
- FR-1.6 `[FUT]` Google OAuth2 login, Microsoft OAuth2 login (interfaces stubbed in Phase 1: `auth_provider` column, pluggable strategy).
- FR-1.7 `[FUT]` MFA (TOTP) — `mfa_enabled`/`mfa_secret` columns reserved in Phase 1 schema, enforcement logic deferred.

### FR-2 Multi-Tenant / Company Management
- FR-2.1 `[P1]` Super Admin creates/edits/suspends/deletes a Company (soft delete).
- FR-2.2 `[P1]` Each Company has isolated Departments, Employees, Roles.
- FR-2.3 `[P1]` No cross-company data access via any authenticated non-Super-Admin session.
- FR-2.4 `[FUT]` Subscription plans, seat limits, billing cycle, license enforcement.

### FR-3 RBAC / Permission Engine
- FR-3.1 `[P1]` Seed default roles (Admin, HR, Manager, Employee, Finance) per new Company.
- FR-3.2 `[P1]` Admin can create custom roles and assign module/action grants via UI.
- FR-3.3 `[P1]` Every API endpoint enforces required `(module, action)` permission via a shared dependency.
- FR-3.4 `[P1]` A user may hold multiple roles; effective permission = union of grants.

### FR-4 Employee Management
- FR-4.1 `[P1]` CRUD for employee profile (identity, contact, department, designation, manager, employment type, status, joining date).
- FR-4.2 `[P1]` Employee directory with search/filter/pagination, scoped to the caller's company.
- FR-4.3 `[FUT]` Document uploads, asset assignment history, skills matrix — schema reserved, UI in a later phase.

### FR-5 Onboarding `[FUT]`
- Configurable per-company document checklist; onboarding-link workflow; HR review → Admin approval → account activation. Schema for `onboarding_task` and `employee_document` reserved in Phase 1 data model (see DATABASE_SCHEMA.md) so Phase 2 does not require breaking migrations.

### FR-6 Project Management `[FUT]`
- Project CRUD, employee/manager/client assignment, budget & billable flag, project dashboard.

### FR-7 Timesheets `[FUT]`
- Configurable period (daily/weekly/bi-weekly/monthly/custom) per company; multi-stage configurable approval chain; rule engine (max/min hours, mandatory fields, duplicate prevention, lock/reopen).

### FR-8 Leave Management `[FUT]`
- Configurable leave types, accrual/carry-forward rules, approval workflow, calendar view.

### FR-9 Assets `[FUT]`
- Asset inventory, assignment/return tracking, warranty tracking.

### FR-10 Reports `[FUT]`
- Per-module report views plus a custom report builder; export to Excel/CSV/PDF.

### FR-11 Notifications `[FUT in full; groundwork in P1]`
- FR-11.1 `[P1]` Transactional email sending (SMTP) for verification/password-reset — infrastructure only.
- FR-11.2 `[FUT]` In-app notifications via WebSocket, digest reminders (birthdays, anniversaries, document expiry), Slack/Teams integration.

### FR-12 Audit Logging
- FR-12.1 `[P1]` Every write (create/update/delete) on tenant-scoped entities is recorded: actor, timestamp, entity, before/after diff, IP, user agent, company.
- FR-12.2 `[P1]` Audit log is append-only and queryable by Admin/Super Admin.

### FR-13 Dashboards
- FR-13.1 `[P1]` Role-aware dashboard shell (widgets vary by role); Phase 1 ships Employee/Admin/Super-Admin dashboard with real data (headcount, department breakdown); Manager/HR/Finance widgets land with their owning modules.

---

## 4. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Security | OWASP Top 10 mitigations; bcrypt/argon2 password hashing; parameterized queries only (SQLAlchemy ORM, no raw string interpolation); CSRF protection on cookie-based flows; strict CORS allowlist; security headers (HSTS, X-Content-Type-Options, X-Frame-Options); rate limiting on auth endpoints |
| Availability | Stateless API layer (horizontally scalable); target 99.9% uptime for production deployment |
| Performance | P95 API latency < 300ms for list endpoints at 10k-row tenant scale (indexed, paginated) |
| Isolation | 100% of tenant-scoped queries filtered by `company_id`; enforced by repository-layer base class + automated test suite |
| Auditability | All mutations logged; logs immutable and retained ≥ 1 year |
| Internationalization | UTF-8 throughout; timezone-aware timestamps (UTC storage, tenant-local display) — locale/i18n string catalogs deferred (`[FUT]`) |
| Accessibility | WCAG 2.1 AA target for core flows (forms, tables, navigation) |
| Maintainability | Clean architecture, SOLID, ≥ 80% test coverage on service layer for implemented modules |
| Observability | Structured JSON logs; health/readiness endpoints; request-id correlation |

---

## 5. External Interface Requirements

- **REST API**: JSON over HTTPS, versioned under `/api/v1`, documented via OpenAPI/Swagger at `/docs`.
- **Email**: SMTP (any provider — configured via env vars; MailHog in dev).
- **Object storage**: S3-compatible API (MinIO dev, AWS S3 prod) for documents/avatars.
- **Frontend ↔ Backend**: Axios client with interceptor-based access-token attach + refresh-on-401.

---

## 6. Acceptance Criteria for Phase 1

1. Two seeded companies exist with non-overlapping employees, departments, and roles.
2. A user authenticated as Company A Admin cannot read, list, or mutate any Company B resource (verified by integration test, not just manual check).
3. Login issues a valid JWT; protected endpoints reject missing/expired/invalid tokens with 401.
4. RBAC: an Employee-role user receives 403 on employee-delete; an Admin-role user succeeds.
5. Full employee CRUD works end-to-end through the React UI against the real API.
6. `docker compose up` brings up Postgres, Redis, MinIO, backend, frontend, and Nginx with no manual steps beyond `.env` configuration and one seed-data command.
7. Swagger docs at `/docs` accurately reflect all implemented endpoints.
