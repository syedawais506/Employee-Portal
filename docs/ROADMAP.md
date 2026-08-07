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

## Phase 2 — Onboarding & Documents
- `employee_document`, `onboarding_task`, `onboarding_template` tables
- Configurable per-company document checklist; secure onboarding link (signed, expiring token) for new hires
- Document upload to S3/MinIO with virus-scan hook (stub) and file-type/size validation
- HR review queue → Admin approval → account activation state machine
- Offer letter generation (template + PDF render)

## Phase 3 — Projects & Employee Mapping
- `project`, `project_member`, `client` tables
- Project CRUD, budget, billable flag, employee/manager/client assignment
- Project dashboard (hours, cost, status)
- Employee mapping: multiple projects, one manager, one HR, one department, one cost center (schema already supports; this phase builds the UI/reporting)

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

## Explicit Non-Goals for Phase 1
To keep Phase 1 a real, working slice rather than a wide shallow scaffold, the following are **not** built yet even though their tables/fields are reserved in the schema: onboarding workflow, document upload, projects, timesheets, leave, assets, reports, notifications beyond transactional email, biometric/GPS attendance, OAuth social login, MFA enforcement, AI features. Each has a clear landing phase above and none require breaking schema changes to the Phase 1 foundation.
