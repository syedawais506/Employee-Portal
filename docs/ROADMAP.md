# Product & Engineering Roadmap

Phasing is scoped so every phase ships something real and testable end-to-end, rather than shallow-stubbing all modules at once. Each phase builds on the multi-tenant/RBAC/audit foundation from Phase 1 — no phase requires re-architecting an earlier one.

## Phase 0 — Foundation Docs *(this pass)*
SRS, HLD, LLD, ER diagram, API contracts, roadmap. No code.

## Phase 1 — Platform Core *(this pass)*
- Repo scaffold (backend/frontend/docker/docs/scripts), clean architecture layers
- PostgreSQL schema + Alembic migration for: company, department, user_account, employee, role, permission, role_permission, user_role, audit_log
- JWT auth (login/refresh/logout/forgot-password/reset-password/verify-email), Redis-backed refresh-token rotation & denylist
- Dynamic RBAC engine + 5 seeded default roles per company + permission-matrix admin UI
- Company management (Super Admin), Department CRUD, Employee CRUD — fully wired UI → API → DB
- Audit logging on all mutations
- Super Admin, Admin, HR, Manager, Employee, Finance dashboards: shell + role-aware nav (Employee/Admin/Super-Admin dashboards get real KPI widgets; others get placeholder widgets ready for their module's data)
- Docker Compose (Postgres, Redis, MinIO, backend, frontend, Nginx), GitHub Actions CI (lint, type-check, test, build)
- Seed script: 2 demo companies, users per role, departments
- Backend unit + integration tests incl. a dedicated cross-tenant-isolation test suite

## Phase 2 — Onboarding & Documents *(shipped)*
- `document_type` (per-company configurable checklist), `employee_document`, `onboarding_invite` tables; `employee.onboarding_status` (`invited → submitted → hr_approved → completed`)
- Admin-configurable document checklist (required/optional, ordered) — no code changes needed to add a document type
- Secure onboarding link: opaque token (SHA-256 hashed at rest, 7-day expiry), emailed to the new hire, resolves to a public (unauthenticated) onboarding portal
- New hire sets their password and uploads each required document via the public link; account stays deactivated (`is_active=False`) until Admin approval — the employee cannot log in through the normal flow before then
- Auto-advance to "submitted" once a password is set and every required document has been uploaded (no separate submit button/endpoint)
- HR review queue: per-document approve/reject with notes, then a `hr-approve` gate requiring every required document be approved
- Admin final approval activates the account (`is_active=True`, `is_verified=True`)
- Offer letter generation: real PDF (ReportLab), pulling live employee/company/department data — not a stub
- Document storage: MinIO/S3 via boto3, presigned download URLs, content-type/size validation
- Dedicated `onboarding` permission module (`view`/`review`/`approve`/`configure`) wired into the same dynamic RBAC engine from Phase 1, including retroactive grants to companies seeded before this phase shipped

**Simplified from the original scope** (deferred, not blocking): no separate "onboarding template" or per-employee task checklist beyond the document list itself; no virus-scan integration (hook point not yet added); offer letter template is fixed (not yet per-company customizable).

## Phase 3 — Projects & Employee Mapping *(shipped)*
- `project` (name, client_id, budget, billable flag, start/end date, status) — **no** `department_id`: cross-functional projects aren't pinned to a single department
- `project_member` (project_id, employee_id, role_on_project: `manager`/`member`) — a project can have more than one manager, so this is a join table rather than a single `project.manager_id` column; a pure join table like `role_permission`/`user_role` from Phase 1, no `company_id` or RLS of its own — tenant isolation comes from always resolving the project (company-scoped) first
- `client` — lightweight (name, contact name/email/phone), managed from a "Clients" tab on the Projects screen (same tabbed pattern as Onboarding's Review Queue / Document Checklist), reusing the existing `project.*` permissions rather than a separate module — it's an assignment target for projects, not a CRM
- Full CRUD + member add/remove, tenant isolation, and RBAC tests, same rigor as Phase 1/2
- `GET /projects/mine` — self-service, any authenticated employee sees only projects they're a member of (with their role on each), independent of the `project.view` permission — matches the original spec's "View Assigned Projects" for the Employee role, and keeps budget/client data out of a plain employee's view. The frontend routes `/projects` to the full management screen or this read-only view automatically based on permission.
- Dashboard: an "Active Projects" KPI added to the existing tenant dashboard — **not** hours or cost-incurred, since neither has a real data source until Phase 4 ships; those widgets land there instead of being built against fake numbers now

**Adjusted from the original scope** (see the scope-review discussion before this phase started): the original draft asked for an "hours, cost, status" dashboard and a single `manager_id`/employee-mapping model. Both were cut back — hours/cost data doesn't exist without Timesheets (Phase 4), and a join-table `project_member` with a role flag is more correct than a single manager column since a project can have multiple managers. Employee mapping itself (multiple projects, one manager/HR/department/cost-center) was already schema-supported since Phase 1; this phase is where it got a UI.

## Phase 4 — Timesheets
- `timesheet_period_config` (per-company period rules), `timesheet_entry`, `timesheet_approval_step`
- Configurable approval chain (Employee → Manager → PM → Finance, each step optional per company)
- Rule engine: min/max hours, mandatory fields, duplicate prevention, weekend/holiday rules, lock/reopen, bulk approve
- Reminders via Celery beat (late submission, pending approval) — email first, in-app next
- Timesheet dashboard: pending, rejected, late, hours by project/employee, billable %, Excel/PDF export

## Phase 5 — Leave Management
- `leave_type`, `leave_policy`, `leave_balance`, `leave_request`, `holiday_calendar`
- Configurable leave types incl. custom, half-day/hourly leave, carry-forward rules, encashment-ready ledger
- Approval workflow (reuses the Phase 4 configurable-chain engine)
- Leave calendar (FullCalendar integration) + holiday calendar

## Phase 6 — Assets
- `asset`, `asset_assignment`, `asset_type`
- Assignment/return tracking, warranty tracking, history per employee

## Phase 7 — Reporting & Notifications
- Cross-module report views (employee, project, department, leave, timesheet, billing, utilization, bench)
- Custom report builder (saved filter + column sets → export)
- In-app notifications (WebSocket/Socket.IO), digest reminders (birthdays, anniversaries, probation, document expiry)
- Slack / Microsoft Teams outbound webhooks

## Phase 8 — Attendance & Subscription/Billing
- Attendance: GPS/QR check-in, shift management, overtime, late marks (biometric/face-recognition as external integration points, not built in-house)
- Super Admin subscription plans, seat limits, license enforcement, usage metering

## Phase 9 — Auth Expansion & AI Features
- Google/Microsoft OAuth2 login (schema already reserved: `auth_provider`), MFA (TOTP) enforcement
- AI features (chatbot for HR FAQs, resume parsing, timesheet suggestions, report generation) as opt-in, provider-agnostic integrations

---

## Explicit Non-Goals for Phase 1 (superseded where later phases have shipped)
To keep Phase 1 a real, working slice rather than a wide shallow scaffold, the following were **not** built yet even though their tables/fields were reserved in the schema: onboarding workflow, document upload, projects, timesheets, leave, assets, reports, notifications beyond transactional email, biometric/GPS attendance, OAuth social login, MFA enforcement, AI features. Each has a clear landing phase above and none required breaking schema changes to the Phase 1 foundation. Onboarding workflow and document upload shipped in Phase 2 (above); the rest remain open per their listed phase.
