# High-Level Design (HLD)

## Employee Management Portal — Multi-Tenant SaaS

Related: [SRS.md](./SRS.md) · [LLD.md](./LLD.md) · [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) · [API_CONTRACTS.md](./API_CONTRACTS.md)

---

## 1. Architecture Overview

Clean/layered architecture, monolith-first (deliberately not microservices — see §7).

```
                                   ┌─────────────────────┐
                                   │        Nginx         │
                                   │ (TLS, reverse proxy, │
                                   │  static frontend)     │
                                   └──────────┬───────────┘
                          ┌────────────────────┼────────────────────┐
                          │                    │                    │
                ┌─────────▼─────────┐ ┌────────▼─────────┐          │
                │   React SPA        │ │  FastAPI backend  │          │
                │  (Vite build,       │ │  (Uvicorn/Gunicorn │          │
                │   served as static  │ │   workers)         │          │
                │   assets)           │ └────────┬──────────┘          │
                └─────────────────────┘          │                     │
                                                  │                     │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │                             │                             │
           ┌────────▼────────┐          ┌─────────▼─────────┐         ┌─────────▼────────┐
           │   PostgreSQL      │          │       Redis         │         │  MinIO / S3        │
           │ (system of record,│          │ (cache, JWT deny-   │         │ (documents,        │
           │  row-level tenant │          │  list, Celery       │         │  avatars, exports)  │
           │  isolation)       │          │  broker/result       │         └────────────────────┘
           └───────────────────┘          │  backend, rate-limit│
                                           │  counters)          │
                                           └─────────┬───────────┘
                                                      │
                                           ┌──────────▼───────────┐
                                           │   Celery workers      │
                                           │ (email, reminders,     │
                                           │  exports, future AI)   │
                                           └────────────────────────┘
```

### Layers within the backend

```
API layer        → FastAPI routers; request/response = Pydantic schemas; no business logic
Service layer     → orchestrates business rules, transactions, calls repositories
Repository layer  → SQLAlchemy queries ONLY; every tenant-scoped query takes company_id
Model layer       → SQLAlchemy 2.0 declarative models
Core              → config, security (JWT/hashing), dependency-injection providers, exceptions
```

Dependency direction is strictly one-way: `api → service → repository → model`. Services never import SQLAlchemy sessions directly except via an injected repository; API routers never import repositories directly.

---

## 2. Component Responsibilities

| Component | Responsibility |
|---|---|
| `app/api` | Route definitions, request validation, response shaping, permission-dependency wiring |
| `app/services` | Business rules (e.g. "an employee's manager must be in the same company"), transaction boundaries |
| `app/repositories` | Data access, always parameterized by `company_id` for tenant-scoped entities |
| `app/models` | ORM models, table definitions, relationships |
| `app/schemas` | Pydantic request/response DTOs (never expose ORM models directly) |
| `app/core` | Settings (Pydantic `BaseSettings`), security utils, JWT, RBAC dependency, logging config |
| `app/tasks` | Celery tasks (email sending, reminders — Phase 1 ships email send only) |
| `frontend/src/api` | Axios instance + typed API client functions |
| `frontend/src/store` | Zustand stores (auth/session, UI state) |
| `frontend/src/features` | Feature-sliced modules (auth, employees, departments, companies) |

---

## 3. Request Lifecycle (example: `PATCH /api/v1/employees/{id}`)

1. Nginx terminates TLS, proxies to Uvicorn.
2. FastAPI dependency chain resolves: `get_db_session` → `get_current_user` (decodes JWT) → `require_permission("employee", "update")`.
3. Router calls `EmployeeService.update(company_id=current_user.company_id, employee_id, payload)`.
4. Service loads the employee via `EmployeeRepository.get(company_id, employee_id)` — raises 404 if not found **within that company** (never leaks existence of another tenant's row).
5. Service applies business rules (e.g. manager must belong to same company), persists via repository, commits.
6. Service emits an `AuditLogEntry` (actor, before/after diff) in the same transaction.
7. Response serialized through a Pydantic response schema — ORM model never returned directly.

---

## 4. Multi-Tenancy Strategy

**Chosen: shared database, shared schema, `company_id` discriminator**, enforced in the repository layer.

| Option | Isolation strength | Ops cost | Chosen? |
|---|---|---|---|
| Database-per-tenant | Strongest | High (migration fan-out, connection pooling per tenant) | No — deferred; documented as an escape hatch for large/regulated customers |
| Schema-per-tenant | Strong | Medium (still N schemas to migrate) | No |
| Shared schema + `company_id` + row-level enforcement | Good, if enforced consistently | Low | **Yes** |

Mitigations for the weakness of shared-schema isolation:
- A `TenantScopedRepository` base class requires `company_id` as the first argument of every query method — there is no code path to query without it.
- PostgreSQL **Row-Level Security (RLS)** policies are enabled as defense-in-depth: the app sets `SET LOCAL app.current_company_id` per request/transaction, and RLS policies on tenant tables reject rows outside that value even if application code has a bug.
- An automated integration test suite specifically asserts cross-tenant access returns 404/403 for every tenant-scoped endpoint (see [SRS.md §6](./SRS.md#6-acceptance-criteria-for-phase-1)).
- Super Admin operations run through a distinct, explicitly-named service path (`SuperAdminService`) that is the only code allowed to omit a `company_id` filter, and every use is audit-logged.

> **Operational caveat**: Postgres RLS never applies to superusers or roles with `BYPASSRLS`, and (without `FORCE ROW LEVEL SECURITY`, which this migration sets) not to the table owner either. The Docker Compose dev setup's default Postgres user is effectively a superuser, so in that environment RLS is present but inert — tenant isolation is enforced by the repository layer alone, which is the primary control either way. For RLS to act as a genuine second layer in production, provision the application's runtime DB role as a non-superuser, non-`BYPASSRLS` role distinct from the migration-owning role.

---

## 5. Authentication & RBAC Flow

```
Login → verify credentials → issue access JWT (15 min) + refresh JWT (7-30 days, "remember me" extends)
Access JWT claims: sub(user_id), company_id, role_ids, exp
Every request: decode+verify access JWT → load user → require_permission(module, action) dependency
             checks the union of grants across the user's roles (cached in Redis, invalidated on role change)
Refresh: POST /auth/refresh with refresh token → rotate (old one denylisted in Redis) → new pair issued
Logout: refresh token added to Redis denylist until its natural expiry
```

Full detail in [LLD.md §2-3](./LLD.md).

---

## 6. Deployment View

```
docker-compose services:
  postgres     — PostgreSQL 16, named volume, healthcheck
  redis        — Redis 7, healthcheck
  minio        — S3-compatible storage, console + API ports
  backend      — FastAPI app (Gunicorn+Uvicorn workers), depends_on postgres/redis healthy
  celery-worker— same image as backend, different entrypoint
  frontend     — multi-stage build → static files served by nginx
  nginx        — reverse proxy: / → frontend static, /api → backend, /docs → backend
```

CI/CD (GitHub Actions): lint → type-check → unit tests → integration tests (spins up Postgres/Redis service containers) → build Docker images → (on tag) push to registry.

---

## 7. Key Architectural Decisions & Rationale

| Decision | Rationale |
|---|---|
| Monolith-first, not microservices | Team size and current scale don't justify microservice operational overhead; clean layering makes future extraction possible without a rewrite |
| Shared-schema multi-tenancy | Lowest operational cost while meeting isolation requirements via enforced repository pattern + Postgres RLS as defense-in-depth |
| JWT (stateless) over server sessions | Horizontal scalability of API layer without sticky sessions; refresh-token rotation + Redis denylist covers revocation |
| Repository pattern | Keeps ORM/query concerns out of business logic; makes tenant-isolation a structural guarantee, not a convention |
| Pydantic schemas at the boundary | Prevents accidental over-exposure of ORM fields (e.g. password hash) in responses |
| Phase 1 scope cut | Ship one fully-real, end-to-end vertical slice (multi-tenancy + auth + RBAC + employee/department/company CRUD) rather than shallow-stub all 15 modules — establishes patterns every later module reuses |

---

## 8. Non-Functional Design Notes

- **Scalability**: stateless API pods behind Nginx/load balancer; Postgres read replicas and Redis cluster are future scale-out options, not needed at Phase 1 scale.
- **Security**: see [SRS.md §4](./SRS.md#4-non-functional-requirements); enforced via `SecurityMiddleware` (headers), `SlowAPI`/Redis-backed rate limiting on `/auth/*`, and strict Pydantic validation on all inputs.
- **Observability**: JSON structured logging with request-id middleware; `/health` (liveness) and `/health/ready` (DB+Redis check) endpoints for orchestrators.
