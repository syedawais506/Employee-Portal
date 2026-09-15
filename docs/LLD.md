# Low-Level Design (LLD)

## Employee Management Portal — Phase 1 Modules

Related: [SRS.md](./SRS.md) · [HLD.md](./HLD.md) · [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) · [API_CONTRACTS.md](./API_CONTRACTS.md)

---

## 1. Backend Folder Structure

```
backend/
├── alembic/                       # migrations
│   ├── versions/
│   └── env.py
├── app/
│   ├── main.py                    # FastAPI app factory, middleware, router mounting
│   ├── core/
│   │   ├── config.py              # Settings(BaseSettings) — env-driven
│   │   ├── security.py            # password hashing, JWT encode/decode
│   │   ├── deps.py                # get_db, get_current_user, require_permission, get_current_company
│   │   ├── exceptions.py          # AppException hierarchy + FastAPI exception handlers
│   │   ├── logging.py             # structured JSON logging setup
│   │   └── rate_limit.py          # Redis-backed limiter
│   ├── db/
│   │   ├── base.py                # Declarative Base, naming convention
│   │   ├── session.py             # engine + SessionLocal, get_db dependency
│   │   └── rls.py                 # sets SET LOCAL app.current_company_id per request
│   ├── models/
│   │   ├── mixins.py              # TimestampMixin, TenantMixin, SoftDeleteMixin
│   │   ├── super_admin.py
│   │   ├── company.py
│   │   ├── department.py
│   │   ├── role.py                 # Role, Permission, RolePermission
│   │   ├── user.py                 # User (auth identity) + UserRole
│   │   ├── employee.py             # Employee profile (1:1 with User within a company)
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── company.py
│   │   ├── department.py
│   │   ├── role.py
│   │   ├── employee.py
│   │   └── common.py               # Pagination, ErrorResponse
│   ├── repositories/
│   │   ├── base.py                 # TenantScopedRepository[T] generic base
│   │   ├── company_repository.py
│   │   ├── department_repository.py
│   │   ├── role_repository.py
│   │   ├── user_repository.py
│   │   └── employee_repository.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── company_service.py      # Super-Admin-only operations
│   │   ├── department_service.py
│   │   ├── role_service.py
│   │   ├── employee_service.py
│   │   └── audit_service.py
│   ├── api/v1/
│   │   ├── router.py                # aggregates all endpoint routers
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── companies.py
│   │       ├── departments.py
│   │       ├── roles.py
│   │       └── employees.py
│   ├── tasks/
│   │   └── email_tasks.py           # Celery: send_verification_email, send_reset_email
│   └── utils/
│       └── email.py                 # SMTP send wrapper
└── tests/
    ├── unit/                        # service-layer, no DB
    └── integration/                 # real Postgres (test DB), tenant-isolation suite
```

---

## 2. Authentication Design

### 2.1 Password handling
- `passlib[bcrypt]` (or `argon2-cffi`) for hashing. Never store/log plaintext.
- Password policy validated in `schemas/auth.py` (min length 10, at least one letter + one digit — configurable per company in a later phase, fixed platform default now).

### 2.2 Tokens

| Token | Claims | Lifetime | Storage (client) |
|---|---|---|---|
| Access JWT | `sub` (user_id), `company_id`, `role_ids[]`, `type=access`, `exp`, `jti` | 15 min | memory (Zustand, not localStorage) |
| Refresh JWT | `sub`, `type=refresh`, `exp`, `jti` | 7 days (30 days if "remember me") | httpOnly secure cookie |

- `jti` (JWT ID) of every issued refresh token is stored in Redis with TTL = token lifetime, value = "active". On refresh, the old `jti` is marked "revoked" (denylist) before issuing a new pair — this is refresh-token rotation with reuse detection: if a revoked `jti` is presented again, all tokens for that user are revoked (possible token theft).
- Access tokens are not individually revocable (stateless, short-lived); logout revokes the refresh token so no new access token can be minted, and the short access-token lifetime bounds exposure.

### 2.3 Endpoints (see [API_CONTRACTS.md](./API_CONTRACTS.md) for full contract)
`POST /auth/register` (Super Admin/Admin-invoked, not public self-signup in Phase 1) · `POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `POST /auth/forgot-password` · `POST /auth/reset-password` · `POST /auth/verify-email` · `GET /auth/me`

### 2.4 `get_current_user` dependency (pseudocode)

```python
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_jwt(token)  # raises 401 on invalid/expired
    if payload["type"] != "access":
        raise credentials_exception
    user = user_repository.get_by_id(db, payload["sub"])
    if user is None or not user.is_active:
        raise credentials_exception
    request.state.company_id = payload["company_id"]  # used by RLS session var + repos
    return user
```

---

## 3. RBAC / Permission Engine

### 3.1 Data model
`Permission(module, action)` — static catalog seeded via migration (e.g. `employee.view`, `employee.create`, ... `timesheet.approve`).
`Role(id, company_id, name, is_system)` — tenant-scoped; `is_system=True` for the 5 seeded defaults (protects them from deletion, not from grant edits, except Admin/Super-Admin core grants).
`RolePermission(role_id, permission_id)` — many-to-many grant table.
`UserRole(user_id, role_id)` — many-to-many; a user may hold multiple roles.

### 3.2 `require_permission` dependency (pseudocode)

```python
def require_permission(module: str, action: str):
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        perms = permission_cache.get_effective_permissions(db, current_user.id)  # Redis-cached, keyed by user_id, invalidated on role change
        if f"{module}.{action}" not in perms and not current_user.is_super_admin:
            raise HTTPException(403, "Insufficient permission")
    return dependency
```

Usage in a router: `@router.delete("/{id}", dependencies=[Depends(require_permission("employee", "delete"))])`.

### 3.3 Admin permission UI contract
`GET /roles` returns roles with their grant matrix; `PUT /roles/{id}/permissions` accepts the full desired grant set `[{module, action, granted}]` and diffs it server-side — this is the "assign permissions from a UI without modifying code" requirement from the spec, fulfilled structurally (catalog is data, not code).

---

## 4. Multi-Tenant Enforcement — `TenantScopedRepository`

```python
class TenantScopedRepository(Generic[ModelT]):
    model: type[ModelT]

    def get(self, db: Session, company_id: UUID, id: UUID) -> ModelT | None:
        return db.query(self.model).filter(
            self.model.id == id, self.model.company_id == company_id
        ).first()

    def list(self, db: Session, company_id: UUID, *, skip: int, limit: int, **filters) -> Page[ModelT]:
        q = db.query(self.model).filter(self.model.company_id == company_id)
        ...  # apply filters, order, paginate

    def create(self, db: Session, company_id: UUID, obj_in: dict) -> ModelT:
        obj = self.model(company_id=company_id, **obj_in)
        ...
```

Every subclass (`EmployeeRepository`, `DepartmentRepository`, `RoleRepository`) inherits this — there is structurally no method that queries without `company_id`. Combined with Postgres RLS (`app/db/rls.py` sets `app.current_company_id` at the start of each request, via a session-scoped — not transaction-local — `set_config`, since a request can span multiple commits; and each tenant table has `CREATE POLICY ... USING (company_id = current_setting('app.current_company_id')::uuid)`), a bug that forgets the filter is still blocked at the database level. This is real enforcement, not just present-but-inert: the app connects at runtime as a dedicated non-superuser, non-`BYPASSRLS` role (see HLD.md §4's RLS callout and `docker/postgres-initdb/01-create-app-role.sh`), distinct from the superuser role migrations run as.

Any code path that queries an RLS-protected table must call `set_tenant_context(db, company_id)` on that session first, or the query silently returns zero rows (not an error) once RLS is enforced — `get_current_user` (`app/core/deps.py`) does this for every authenticated request; `run_daily_digest` (`app/tasks/digest_tasks.py`) does it per-company in its loop; the public onboarding flow resolves its invite by token first (`onboarding_invite` is deliberately RLS-exempt for exactly this reason) and calls it immediately after, before touching `employee`/`document_type`/`employee_document`/`company_tour_step`. Any new code path that touches an RLS-protected table on a session that never had this called is a bug.

`CompanyRepository` itself is **not** tenant-scoped (companies are the tenant boundary) — only `SuperAdminService` may use it directly; this is enforced by only injecting `CompanyRepository` into `CompanyService`, which is only wired into Super-Admin-only endpoints.

---

## 5. Employee Module

### 5.1 Model relationship
`User` (auth identity: email, password_hash, is_active, is_verified, is_super_admin, company_id nullable-for-super-admin) 1—1 `Employee` (profile: employee_code, first/last name, phone, department_id, designation, manager_id (self-referential FK to `employee.id`), employment_type, joining_date, status).

Splitting `User` (auth) from `Employee` (HR profile) allows future non-employee platform users (e.g. external client viewers in Finance reports) without overloading the auth table, and keeps auth concerns (password, tokens) architecturally separate from HR data.

### 5.2 Service rules enforced in `EmployeeService`
- `manager_id`, `department_id` must reference rows in the **same company** — validated in the service layer (defense-in-depth beyond the FK, since FKs alone don't check `company_id` equality across tables).
- Deactivating an employee cascades to disabling their `User.is_active` (single transaction).
- Employee code is unique per company (`UNIQUE(company_id, employee_code)`), not globally unique.

### 5.3 Audit
Every `create`/`update`/`delete` in `EmployeeService` calls `AuditService.record(actor, entity="employee", entity_id, before, after, ip, user_agent, company_id)` inside the same DB transaction (all-or-nothing).

---

## 6. Frontend Design

### 6.1 Structure (feature-sliced)

```
frontend/src/
├── api/           axios instance (interceptors: attach access token, 401 → refresh-and-retry once)
├── app/           App shell: providers (QueryClientProvider, ThemeProvider, RouterProvider)
├── store/         Zustand: useAuthStore (user, accessToken, permissions, login/logout actions)
├── routes/        route table + <ProtectedRoute requiredPermission="..."> wrapper
├── layouts/       AppLayout (sidebar+topbar+breadcrumbs), AuthLayout (centered card)
├── features/
│   ├── auth/          LoginPage, ForgotPasswordPage, ResetPasswordPage
│   ├── companies/     (Super Admin) CompanyListPage, CompanyFormDialog
│   ├── departments/   DepartmentListPage, DepartmentFormDialog
│   ├── roles/          RoleListPage, PermissionMatrixEditor
│   └── employees/      EmployeeListPage, EmployeeFormPage, EmployeeDetailPage
├── components/     shared: DataTable, ConfirmDialog, PageHeader, PermissionGate
├── theme/          MUI theme (light/dark), palette per dataviz-skill-aligned tokens
└── types/          shared TS types mirroring backend Pydantic schemas
```

### 6.2 Auth flow
1. `LoginPage` → `POST /auth/login` → store access token in memory (Zustand), refresh token arrives as httpOnly cookie (set by backend `Set-Cookie`).
2. Axios request interceptor attaches `Authorization: Bearer <accessToken>`.
3. Axios response interceptor: on 401, calls `/auth/refresh` (cookie sent automatically) once; on success retries the original request; on failure, clears store and redirects to `/login`.
4. `useAuthStore` also holds the flattened `permissions: string[]` (e.g. `["employee.view", "employee.create"]`) fetched from `GET /auth/me`, used by `<PermissionGate module="employee" action="delete">` to conditionally render actions, and by `<ProtectedRoute>` to gate whole pages. This is a UX convenience only — the API remains the enforcement boundary.

### 6.3 Data fetching
React Query for all server state (no manual `useEffect` fetch/loading/error plumbing); query keys namespaced `["employees", companyId, filters]`; mutations invalidate the relevant list query key.

---

## 7. Error Handling Contract

All API errors return a consistent envelope:

```json
{ "error": { "code": "PERMISSION_DENIED", "message": "You do not have permission to perform this action.", "details": null } }
```

`AppError` subclasses (`NotFoundError`, `PermissionDeniedError`, `ValidationAppError`, `ConflictError`, `TokenError`) map to HTTP 404/403/422/409/401 via a single FastAPI exception handler — routers raise domain exceptions, never construct `HTTPException` with hand-written status codes inline (keeps status-code mapping in one place).

---

## 8. Onboarding Module (Phase 2)

### 8.1 State machine

```
invited ──(password set + all required docs uploaded)──> submitted
submitted ──(HR approves every required document, then hr-approve)──> hr_approved
hr_approved ──(Admin approve)──> completed  [user.is_active=True, is_verified=True]
```

The `invited → submitted` transition is **not** a dedicated endpoint — `OnboardingService._maybe_advance_to_submitted` re-checks the condition after every password-set and document-upload call and flips the status automatically once both are satisfied. This avoids a redundant "submit" step the frontend would otherwise have to get right.

### 8.2 Token design

The onboarding invite is an opaque token (`secrets.token_urlsafe(32)`), emailed once and never persisted in raw form — only its SHA-256 hex digest (`OnboardingInvite.token_hash`) is stored, mirroring the pattern for password-reset tokens. `OnboardingInvite.used_at` is set the moment the new hire sets their password and doubles as the "password already set" flag returned to the frontend — there's no separate boolean column to keep in sync.

Unlike the JWT-based auth tokens, this is a **database-backed** token: HR needs to see and reason about invite state (has it been used? expired?) independent of any single token's cryptographic validity, which a stateless JWT can't provide.

### 8.3 Why account activation is deferred to Admin, not password-set

`EmployeeService.create_employee` sets `user.is_active=False` at creation (a change from the simpler Phase 1 behavior, which activated immediately). The account stays inactive through the entire `invited`/`submitted`/`hr_approved` states — even after the new hire has set a real password — and only flips to `is_active=True` on `OnboardingService.admin_approve`. This is what makes "Admin approves onboarding → account activated" a real gate rather than a formality: a new hire who has submitted documents cannot log in and start using the portal until both HR and Admin have signed off.

### 8.4 Document storage

Files are never stored in Postgres — `EmployeeDocument.file_key` is an S3/MinIO object key (`{company_id}/employees/{employee_id}/documents/{document_type_id}/{uuid}_{filename}`), uploaded via `app/utils/storage.py` (boto3, region/endpoint from `Settings.s3_*`). Downloads go through a 5-minute presigned URL (`generate_download_url`), never proxied through the API process. Re-uploading a document for the same `(employee_id, document_type_id)` pair overwrites the row in place (`EmployeeDocumentRepository.upsert`) rather than accumulating versions — sufficient for Phase 2's single-reviewer-cycle workflow.
