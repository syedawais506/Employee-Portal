# API Contracts — Phase 1 (`/api/v1`)

Full interactive contract is auto-generated at runtime: `GET /docs` (Swagger UI) and `GET /openapi.json`. This document is the human-reviewable source contract these endpoints implement.

**Conventions**
- All requests/responses are JSON. All timestamps are ISO-8601 UTC.
- All list endpoints accept `?page=1&page_size=25` and return `{ "items": [...], "total": N, "page": 1, "page_size": 25 }`.
- All errors return `{ "error": { "code", "message", "details" } }` (see [LLD.md §7](./LLD.md#7-error-handling-contract)).
- Auth: `Authorization: Bearer <access_token>` header, except `/auth/login`, `/auth/refresh`, `/auth/forgot-password`, `/auth/reset-password`.
- Permission column shows the `(module, action)` a route requires; "self" means the endpoint scopes to the caller's own record regardless of role.

---

## Auth — `/api/v1/auth`

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `POST /auth/login` | `{email, password, remember_me}` | `{access_token, expires_in, user}` (+ `Set-Cookie: refresh_token`) | public |
| `POST /auth/refresh` | *(refresh cookie)* | `{access_token, expires_in}` (+ rotated cookie) | public (cookie-bound) |
| `POST /auth/logout` | — | `204` | authenticated |
| `POST /auth/forgot-password` | `{email}` | `202` (always, no user-enumeration) | public |
| `POST /auth/reset-password` | `{token, new_password}` | `204` | public |
| `POST /auth/verify-email` | `{token}` | `204` | public |
| `GET /auth/me` | — | `{id, email, company_id, is_super_admin, employee, permissions[]}` | authenticated |

## Companies — `/api/v1/companies` (Super Admin only)

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /companies` | query: `search, status, page, page_size` | Page<Company> | super_admin |
| `POST /companies` | `{name, slug, admin_email, admin_first_name, admin_last_name}` | Company (201) — also creates the seeded Admin user + default roles | super_admin |
| `GET /companies/{id}` | — | Company | super_admin |
| `PATCH /companies/{id}` | `{name?, status?}` | Company | super_admin |
| `DELETE /companies/{id}` | — | `204` (soft delete) | super_admin |

## Departments — `/api/v1/departments`

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /departments` | `search, parent_id, page, page_size` | Page<Department> | department.view |
| `POST /departments` | `{name, parent_department_id?, cost_center_code?}` | Department (201) | department.create |
| `GET /departments/{id}` | — | Department | department.view |
| `PATCH /departments/{id}` | `{name?, parent_department_id?}` | Department | department.update |
| `DELETE /departments/{id}` | — | `204` | department.delete |
| `GET /departments/export` | `search?, parent_department_id?, created_from?, created_to?` | `text/csv` attachment | department.export |

## Roles & Permissions — `/api/v1/roles`

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /roles` | — | `[{id, name, is_system, permissions:[{module,action,granted}]}]` | role.view |
| `POST /roles` | `{name}` | Role (201) | role.create |
| `PATCH /roles/{id}` | `{name?}` | Role | role.update |
| `PUT /roles/{id}/permissions` | `{permissions:[{module,action,granted}]}` | Role with updated grants | role.update |
| `DELETE /roles/{id}` | — | `204` (blocked if `is_system=true`) | role.delete |
| `GET /permissions/catalog` | — | `[{module, actions:[...]}]` full static catalog | authenticated |

## Employees — `/api/v1/employees`

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /employees` | `search, department_id, status, manager_id, page, page_size` | Page<EmployeeSummary> | employee.view |
| `POST /employees` | `{email, first_name, last_name, department_id?, designation?, manager_id?, employment_type, location?, joining_date, role_ids[]}` | Employee (201) — creates `user_account` (deactivated) + `employee` (`onboarding_status="invited"`) + queues an onboarding invite email (see Onboarding below) | employee.create |
| `GET /employees/{id}` | — | EmployeeDetail (incl. `onboarding_status`) | employee.view |
| `PATCH /employees/{id}` | `{first_name?, last_name?, phone?, department_id?, designation?, manager_id?, employment_type?, location?, status?}` | EmployeeDetail | employee.update |
| `DELETE /employees/{id}` | — | `204` (soft delete + deactivate user) | employee.delete |
| `GET /employees/me` | — | EmployeeDetail (caller's own) | self |
| `PATCH /employees/me` | `{phone?, address?}` (self-editable subset only) | EmployeeDetail | self |
| `GET /employees/export` | `search?, department_id?, status?, manager_id?, employment_type?, location?, joining_date_from?, joining_date_to?` | `text/csv` attachment | employee.export |

## Document Types — `/api/v1/document-types` *(Phase 2)*

Per-company configurable onboarding checklist. A new hire must upload every `is_required=true` type before their onboarding auto-advances to `submitted`.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /document-types` | — | `[{id, name, is_required, sort_order}]` | onboarding.view |
| `POST /document-types` | `{name, is_required, sort_order}` | DocumentType (201) | onboarding.configure |
| `PATCH /document-types/{id}` | `{name?, is_required?, sort_order?}` | DocumentType | onboarding.configure |
| `DELETE /document-types/{id}` | — | `204` | onboarding.configure |

## Onboarding — `/api/v1/onboarding` *(Phase 2)*

The `/onboarding/{token}` routes are **unauthenticated by design** — `{token}` is the secure, single-use-until-expiry credential emailed to the new hire (see [LLD.md](./LLD.md) for the token-hashing scheme). Every other route below requires a normal session plus the listed permission.

| Method & Path | Body | Response | Auth |
|---|---|---|---|
| `GET /onboarding/queue` | `page` n/a — full list | `[{id, employee_code, first_name, last_name, onboarding_status}]` for employees in `invited`/`submitted`/`hr_approved` | onboarding.view |
| `GET /onboarding/{token}` | — | `{employee, document_types[], uploaded_documents[], password_already_set, expires_at}` | public (token) |
| `POST /onboarding/{token}/password` | `{password}` | `204` | public (token); only while `onboarding_status="invited"` |
| `POST /onboarding/{token}/documents` | multipart: `document_type_id`, `file` | EmployeeDocument (201) | public (token); only while status is `invited`/`submitted` |
| `GET /employees/{id}/documents` | — | `[EmployeeDocument]` | onboarding.view |
| `POST /employees/{id}/documents/{doc_id}/review` | `{approve, notes?}` | EmployeeDocument (status set to approved/rejected) | onboarding.review |
| `GET /employees/{id}/documents/{doc_id}/download` | — | `{url}` — presigned S3/MinIO GET URL, 5 min expiry | onboarding.view |
| `POST /employees/{id}/onboarding/hr-approve` | — | `{onboarding_status:"hr_approved"}` — 422 if any required document isn't `approved` yet | onboarding.review |
| `POST /employees/{id}/onboarding/approve` | — | `{onboarding_status:"completed"}` — activates the account; 422 if not yet `hr_approved` | onboarding.approve |

File uploads are limited to PDF/PNG/JPEG, 10 MB max, validated server-side regardless of client-declared content type.

## Clients — `/api/v1/clients` *(Phase 3)*

Lightweight assignment target for projects — reuses the `project.*` permissions rather than a separate module.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /clients` | — | `[{id, name, contact_name, contact_email, contact_phone}]` | project.view |
| `POST /clients` | `{name, contact_name?, contact_email?, contact_phone?}` | Client (201) | project.create |
| `PATCH /clients/{id}` | `{name?, contact_name?, contact_email?, contact_phone?}` | Client | project.update |
| `DELETE /clients/{id}` | — | `204` (projects referencing it keep their other data; `client_id` becomes null) | project.delete |
| `GET /clients/export` | `search?, created_from?, created_to?` | `text/csv` attachment | project.export |

## Projects — `/api/v1/projects` *(Phase 3)*

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /projects` | `status?, page, page_size` | Page<ProjectSummary> | project.view |
| `POST /projects` | `{name, client_id?, budget?, is_billable, start_date?, end_date?, member_ids?: [{employee_id, role_on_project}]}` | ProjectDetail (201) | project.create |
| `GET /projects/mine` | — | `[{id, name, status, role_on_project, start_date, end_date}]` — projects the caller is a member of | authenticated (self, no `project.view` needed) |
| `GET /projects/{id}` | — | ProjectDetail (incl. `members[]`, `client`) | project.view |
| `PATCH /projects/{id}` | `{name?, client_id?, budget?, is_billable?, start_date?, end_date?, status?}` | ProjectDetail | project.update |
| `DELETE /projects/{id}` | — | `204` (hard delete; membership rows cascade) | project.delete |
| `POST /projects/{id}/members` | `{employee_id, role_on_project}` | ProjectDetail with updated `members[]` | project.update |
| `DELETE /projects/{id}/members/{employee_id}` | — | ProjectDetail with updated `members[]` | project.update |
| `GET /projects/export` | `status?, client_id?, is_billable?, start_date_from?, start_date_to?` | `text/csv` attachment | project.export |

`client_id` and every `employee_id` in `member_ids` are validated server-side to belong to the caller's company — cross-tenant references return `422`, not a silent no-op.

## Timesheets — `/api/v1/timesheets` *(Phase 4)*

Entries and submissions are always scoped to the caller's own employee record — there is no "edit someone else's timesheet" endpoint. Approval/dashboard/export routes act company-wide for whoever holds the relevant permission (same model as every other module — not restricted to "my direct reports").

Submission ranges are free-form: the caller picks the exact `period_start`/`period_end` to submit each time (not derived from `timesheet_period_config`), so a second submission for newly-logged entries never collides with one already pending for an overlapping range — `timesheet_period_config` still drives the rule engine (min/max hours per day) and the dashboard's "late" calculation, just not what a submission covers.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /timesheets/config` | — | TimesheetPeriodConfig (auto-created with defaults on first access) | timesheet.view |
| `PATCH /timesheets/config` | `{period_type?, week_start_day?, min_hours_per_day?, max_hours_per_day?, require_description?, warn_on_weekend?, require_finance_approval?}` | TimesheetPeriodConfig | timesheet.configure |
| `GET /timesheets/entries` | `date_from, date_to` | `[TimesheetEntry]` — caller's own | timesheet.view (self) |
| `POST /timesheets/entries` | `{project_id, entry_date, hours, is_billable, work_type, description?}` | TimesheetEntry (201) | timesheet.create (self) |
| `PATCH /timesheets/entries/{id}` | `{hours?, is_billable?, work_type?, description?, project_id?}` | TimesheetEntry | timesheet.update (self; 404 if not the caller's own) |
| `DELETE /timesheets/entries/{id}` | — | `204` | timesheet.update (self) |
| `POST /timesheets/submissions` | `{period_start, period_end}` | TimesheetSubmission (201) — submits every draft/rejected entry inside the given free-form date range (not snapped to `timesheet_period_config`; the caller chooses the exact range each time) | timesheet.update (self) |
| `GET /timesheets/submissions/mine` | `bucket?: pending\|approved\|rejected` | `[TimesheetSubmission]` — caller's own submission history, optionally filtered to one bucket (`pending` = submitted + manager_approved) | authenticated (self) |
| `GET /timesheets/submissions` | `bucket?: pending\|approved\|rejected, page, page_size` | Page\<TimesheetSubmission\> — approval queue | timesheet.approve |
| `POST /timesheets/submissions/{id}/approve` | — | TimesheetSubmission — advances one step (Manager, then Finance only if `require_finance_approval`) | timesheet.approve |
| `POST /timesheets/submissions/{id}/reject` | `{reason}` | TimesheetSubmission (`status:"rejected"`) | timesheet.reject |
| `POST /timesheets/submissions/bulk-approve` | `{submission_ids: [...]}` | `{approved: [...], failed: [{id, reason}]}` — partial failures don't abort the batch | timesheet.approve |
| `POST /timesheets/submissions/{id}/reopen` | — | TimesheetSubmission (`status:"submitted"`) — only approved submissions can be reopened | timesheet.delete (Admin-only by default — see ROADMAP.md) |
| `GET /timesheets/dashboard` | `date_from?, date_to?` | `{pending_count, rejected_count, late_count, billable_percentage, hours_by_project[], hours_by_employee[]}` | timesheet.approve OR timesheet.export |
| `GET /timesheets/export` | `date_from?, date_to?, employee_id?, project_id?, location?` | `text/csv` attachment (columns incl. Employee, Location, Project, Date, Hours, Billable, Work Type, Status, Description) | timesheet.export |

`project_id` on entry creation is validated against the caller's own `project_member` rows — logging time against a project you're not assigned to returns `422`. A duplicate `(employee, date, project)` entry returns `409`, as does creating/editing an entry inside an already-approved (locked) period.

## Health

Unversioned and mounted at the application root (not under `/api/v1`), so infra healthchecks (Docker `HEALTHCHECK`, load balancer probes) don't break across API version bumps.

| Method & Path | Response |
|---|---|
| `GET /health` | `{status:"ok"}` — liveness |
| `GET /health/ready` | `{status:"ok", db:"ok", redis:"ok"}` — readiness |

---

## Example: `Employee` response schema

```json
{
  "id": "b3b6...",
  "employee_code": "ACME-0007",
  "first_name": "Priya",
  "last_name": "Sharma",
  "email": "priya.sharma@acme-demo.com",
  "phone": "+91-9876543210",
  "department": { "id": "...", "name": "Engineering" },
  "designation": "Senior Software Engineer",
  "manager": { "id": "...", "first_name": "Rahul", "last_name": "Verma" },
  "employment_type": "full_time",
  "location": "India",
  "joining_date": "2023-06-12",
  "status": "active",
  "roles": [{ "id": "...", "name": "Employee" }],
  "created_at": "2023-06-01T10:00:00Z",
  "updated_at": "2026-01-10T08:30:00Z"
}
```

## Error codes catalog (Phase 1)

| code | HTTP | Meaning |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Login failed |
| `TOKEN_EXPIRED` / `TOKEN_INVALID` | 401 | JWT problem |
| `PERMISSION_DENIED` | 403 | RBAC check failed |
| `NOT_FOUND` | 404 | Entity not found in caller's company |
| `VALIDATION_ERROR` | 422 | Pydantic validation failure |
| `CONFLICT` | 409 | Unique constraint violation (e.g. duplicate email/employee_code) |
| `RATE_LIMITED` | 429 | Too many requests (auth endpoints) |
