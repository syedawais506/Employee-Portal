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

## Leave — `/api/v1/leave-types`, `/holidays`, `/leave-requests`, `/leave/...` *(Phase 5)*

Full-day only (no half-day/hourly granularity yet — see ROADMAP.md). Broad `leave.view` is company-wide read access to leave types/holidays/settings only — anything that exposes *other employees'* requests or balances (the approval queue, company-wide balances, dashboard, export) is gated on the narrower `leave.approve`/`leave.export` instead, the same lesson the offer-letter feature was rebuilt around. That same `leave.approve` permission is reused as the signal for "may file leave on behalf of another employee," rather than inventing a separate permission for it.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /leave-types` | — | `[LeaveType]` | leave.view |
| `POST /leave-types` | `{name, is_paid, annual_quota_days?, max_carry_forward_days, requires_attachment}` | LeaveType (201) | leave.configure |
| `PATCH /leave-types/{id}` | any subset of the above | LeaveType | leave.configure |
| `DELETE /leave-types/{id}` | — | `204` — `409` if any leave request references it | leave.configure |
| `GET /holidays` | `year?` | `[Holiday]` — every holiday regardless of location; the calendar UI filters client-side to the viewer's own `employee.location` (plus company-wide ones) | leave.view |
| `POST /holidays` | `{date, name, location?}` | Holiday (201) — `location: null` (default) applies company-wide; a value like `"India"` scopes it to employees at that location | leave.configure |
| `PATCH /holidays/{id}` | `{date?, name?, location?, clear_location?}` | Holiday — `clear_location: true` is required to revert a scoped holiday back to company-wide, since an omitted/`null` `location` is otherwise treated as "unchanged" like every other optional PATCH field | leave.configure |
| `DELETE /holidays/{id}` | — | `204` | leave.configure |
| `GET /leave/settings` | — | `{require_hr_leave_approval}` | leave.view |
| `PATCH /leave/settings` | `{require_hr_leave_approval}` | `{require_hr_leave_approval}` | leave.configure |
| `GET /leave/balances/mine` | `year?` (defaults to current year) | `[LeaveBalance]` — caller's own | authenticated (self) |
| `GET /leave/balances` | `year?, employee_id?` | `[LeaveBalance]` — company-wide when `employee_id` is omitted | leave.approve |
| `POST /leave-requests` | multipart form: `leave_type_id, start_date, end_date, reason?, employee_id?, file?` | LeaveRequest (201) | leave.create (self, or on behalf of `employee_id` if the caller also holds leave.approve) |
| `GET /leave-requests/mine` | `status?` | `[LeaveRequest]` — caller's own | authenticated (self) |
| `GET /leave-requests` | `employee_id?, leave_type_id?, status?, page, page_size` | Page\<LeaveRequest\> — approval queue | leave.approve |
| `POST /leave-requests/{id}/cancel` | — | LeaveRequest (`status:"cancelled"`) — only while still open (pending/manager_approved/approved) | leave.update (self, or on behalf of, same as filing) |
| `DELETE /leave-requests/{id}` | — | `204` — hard delete | leave.delete |
| `POST /leave-requests/{id}/approve` | — | LeaveRequest — advances one step (Manager, then HR only if `require_hr_leave_approval`) | leave.approve |
| `POST /leave-requests/{id}/reject` | `{reason}` | LeaveRequest (`status:"rejected"`) | leave.reject |
| `POST /leave/carry-forward` | `{from_year, employee_id?}` | `{from_year, to_year, balances_updated}` — company-wide when `employee_id` is omitted | leave.configure |
| `GET /leave/dashboard` | — | `{pending_count, on_leave_today_count}` | leave.approve |
| `GET /leave/export` | `date_from?, date_to?, employee_id?, leave_type_id?, status?` | `text/csv` attachment (columns: Employee, Leave Type, Start Date, End Date, Days, Status, Reason) | leave.export |

`days_count` is computed server-side as business days in the range (weekdays minus `holiday_calendar` dates — company-wide holidays plus any scoped to the *requesting employee's own* `employee.location`), never trusted from the client. A request is rejected with `422` if it would exceed the employee's available balance (`granted + carried_forward + adjustment - held`, where "held" counts pending/manager_approved/approved requests, not just approved ones) for quota-tracked leave types, or if the selected leave type `requires_attachment` and no file was attached. Any two open requests for the same employee with overlapping date ranges return `409`, regardless of leave type. Carry-forward is a manual, admin-triggered action (no `celery-beat` scheduling yet — see ROADMAP.md).

## Assets — `/api/v1/asset-types`, `/assets` *(Phase 6)*

No approval step — Admin/HR assign and return directly. "Current holder" is never a stored field; it's derived from whichever `AssetAssignment` row for that asset has `returned_at: null` (at most one at a time). `asset.view` (company-wide) is Admin/HR/Manager only — a plain Employee holds no `asset.*` permission at all, but can always see their own current + past assignments via `/assets/mine`, which needs only authentication, the same self-scoping pattern as `/leave-requests/mine`.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /asset-types` | — | `[AssetType]` | asset.view |
| `POST /asset-types` | `{name}` | AssetType (201) | asset.create |
| `PATCH /asset-types/{id}` | `{name?}` | AssetType | asset.update |
| `DELETE /asset-types/{id}` | — | `204` — `409` if any asset references it | asset.delete |
| `GET /assets` | `asset_type_id?, status?, page, page_size` | Page\<Asset\> | asset.view |
| `GET /assets/mine` | — | `[AssetAssignment]` — caller's own current + past assignments | authenticated (self) |
| `GET /assets/summary` | — | `{total, available, assigned, retired, lost, damaged}` | asset.view |
| `GET /assets/export` | `asset_type_id?, status?` | `text/csv` attachment (columns: Asset Tag, Name, Type, Status, Current Holder, Purchase Date, Warranty Expiry) | asset.export |
| `POST /assets` | `{asset_type_id, asset_tag, name, purchase_date?, warranty_expiry?, notes?}` | Asset (201) | asset.create |
| `PATCH /assets/{id}` | `{asset_type_id?, asset_tag?, name?, purchase_date?, warranty_expiry?, status?, notes?}` | Asset — `status: "assigned"` is rejected (`422`); use `/assign` instead | asset.update |
| `DELETE /assets/{id}` | — | `204` — `409` if it has any assignment history | asset.delete |
| `POST /assets/{id}/assign` | `{employee_id}` | Asset (`status:"assigned"`) — `409` if the asset isn't `available` | asset.update |
| `POST /assets/{id}/return` | — | Asset (`status:"available"`) — `409` if there's no open assignment | asset.update |
| `GET /assets/{id}/history` | — | `[AssetAssignment]` — every assignment for this asset, newest first | asset.view |

## Reports — `/api/v1/reports` *(Phase 7)*

Not a generic query builder — each of the six reportable modules (`employee`, `department`, `project`, `timesheet`, `leave`, `asset`) has a fixed column set, reusing the exact `report_rows()` method that module's own Export button has called since its own phase (no duplicated SQL, no drift between what a module's own export produces and what shows up here). `filters` is a per-module shape, validated against that module's Pydantic filter schema — an unknown `module` or a filter that fails validation (e.g. a non-UUID `department_id`) returns `422`. Preview and export both run the identical unpaginated query; preview just truncates the in-memory result to 200 rows.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `POST /reports/preview` | `{module, filters}` | `{header: [...], rows: [[...]], total, truncated}` — first 200 rows | report.view |
| `POST /reports/export` | `{module, filters}` | `text/csv` attachment, same columns as that module's own `.../export` endpoint | report.export |
| `GET /reports/saved` | — | `[SavedReport]` — company-shared, not creator-private | report.view |
| `POST /reports/saved` | `{name, module, filters}` | SavedReport (201) — `409` on a duplicate name | report.configure |
| `PATCH /reports/saved/{id}` | `{name?, filters?}` | SavedReport — a new `filters` is validated against the report's own (unchangeable) `module` | report.configure |
| `DELETE /reports/saved/{id}` | — | `204` | report.configure |
| `POST /reports/saved/{id}/run` | — | Same shape as `/reports/preview`, using the saved filters | report.view |
| `GET /reports/saved/{id}/export` | — | `text/csv` attachment, using the saved filters | report.export |

`report.view`/`report.export` were declared in the permission catalog since Phase 1 (Admin/Finance: view+export; HR/Manager: view-only; Employee: none) but never wired to anything until this phase. `report.configure` (create/update/delete saved reports) is new, granted Admin-only — narrower than "use" the same way `leave.configure`/`timesheet.configure` are narrower than their modules' `.view`.

## Notifications — `/api/v1/notifications` *(Phase 7b)*

Always self-scoped to the recipient — no new permission catalog entries, same self-scoping pattern as `/leave-requests/mine`. A notification is created synchronously inside the same request/transaction as the action that triggered it (leave/timesheet submit+approve+reject, asset assign, onboarding submission → fans out to everyone holding `onboarding.review`); the REST API below is always the source of truth. The live WebSocket push is best-effort on top of that — if it fails or the client wasn't connected, the row is still there on next `GET /notifications`.

| Method & Path | Body | Response | Permission |
|---|---|---|---|
| `GET /notifications` | `unread_only?, page, page_size` | Page\<Notification\> — caller's own | authenticated (self) |
| `GET /notifications/unread-count` | — | `{unread_count}` | authenticated (self) |
| `POST /notifications/{id}/read` | — | Notification (`is_read: true`) — `404` if it isn't the caller's own | authenticated (self) |
| `POST /notifications/read-all` | — | `{marked_read: <count>}` | authenticated (self) |
| `WS /notifications/ws?token=<access_token>` | — | `{"type": "notification", "data": Notification}` per push | authenticated (self) |

The WebSocket route is the one deliberate exception to this app's "Bearer token in the `Authorization` header" auth convention — a browser `WebSocket` handshake can't set custom headers, so the access token travels as a query parameter instead, validated with the exact same `decode_token()`/active-user checks `get_current_user` uses for every other endpoint. An invalid or expired token closes the connection with code `4401` before `accept()`. Delivery is in-process only (an in-memory `user_id -> connections` registry, captured against the single Uvicorn event loop at startup) — there's no Redis pub/sub yet, so a notification created on one backend process can't reach a connection held open on another; fine for this app's current single-instance deployment, revisit if it's ever horizontally scaled.

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
