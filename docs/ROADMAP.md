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
- Document storage: MinIO/S3 via boto3, presigned download URLs, content-type/size validation
- Dedicated `onboarding` permission module (`view`/`review`/`approve`/`configure`) wired into the same dynamic RBAC engine from Phase 1, including retroactive grants to companies seeded before this phase shipped

**Simplified from the original scope** (deferred, not blocking): no separate "onboarding template" or per-employee task checklist beyond the document list itself; no virus-scan integration (hook point not yet added).

**Removed after shipping** (direct user request): offer letter PDF generation/download shipped in this phase gated on `employee.view`, but that permission is company-wide by design (like every other `.view` permission in this app — see Phase 1), so any Employee-role user could browse the directory and download *any* other employee's offer letter, not just their own. Rather than bolt on one-off "self only" scoping for this single endpoint, the feature was removed outright (route, PDF service, ReportLab dependency, frontend button all deleted) rather than kept behind a narrower fix — it wasn't load-bearing for anything else and the simplest correct fix was to not have it.

## Phase 3 — Projects & Employee Mapping *(shipped)*
- `project` (name, client_id, budget, billable flag, start/end date, status) — **no** `department_id`: cross-functional projects aren't pinned to a single department
- `project_member` (project_id, employee_id, role_on_project: `manager`/`member`) — a project can have more than one manager, so this is a join table rather than a single `project.manager_id` column; a pure join table like `role_permission`/`user_role` from Phase 1, no `company_id` or RLS of its own — tenant isolation comes from always resolving the project (company-scoped) first
- `client` — lightweight (name, contact name/email/phone), managed from a "Clients" tab on the Projects screen (same tabbed pattern as Onboarding's Review Queue / Document Checklist), reusing the existing `project.*` permissions rather than a separate module — it's an assignment target for projects, not a CRM
- Full CRUD + member add/remove, tenant isolation, and RBAC tests, same rigor as Phase 1/2
- `GET /projects/mine` — self-service, any authenticated employee sees only projects they're a member of (with their role on each), independent of the `project.view` permission — matches the original spec's "View Assigned Projects" for the Employee role, and keeps budget/client data out of a plain employee's view. The frontend routes `/projects` to the full management screen or this read-only view automatically based on permission.
- Dashboard: an "Active Projects" KPI added to the existing tenant dashboard — **not** hours or cost-incurred, since neither has a real data source until Phase 4 ships; those widgets land there instead of being built against fake numbers now

**Adjusted from the original scope** (see the scope-review discussion before this phase started): the original draft asked for an "hours, cost, status" dashboard and a single `manager_id`/employee-mapping model. Both were cut back — hours/cost data doesn't exist without Timesheets (Phase 4), and a join-table `project_member` with a role flag is more correct than a single manager column since a project can have multiple managers. Employee mapping itself (multiple projects, one manager/HR/department/cost-center) was already schema-supported since Phase 1; this phase is where it got a UI.

## Phase 4 — Timesheets
- `timesheet_period_config` (per-company period type: daily/weekly/monthly, plus week-start-day for weekly) — bi-weekly and fully custom periods are deferred, not enough real-world demand to justify the extra date-math complexity now
- `timesheet_entry` (employee, date, `project_id` validated against that employee's `project_member` rows from Phase 3, hours, billable flag, work type, description) — one row per day/project
- `timesheet_submission` — groups an employee's entries for one period and carries the actual workflow state (`draft → submitted → approved/rejected`); approval happens per period, not per entry row
- Approval chain: Manager approval always required (every employee already has one); a per-company toggle adds an optional final Finance sign-off. "Project Manager" as a distinct configurable step is deferred — Phase 3's `project_member.role_on_project` makes it possible to add later without a schema change, but a fully generic N-step engine isn't worth the complexity for the first version
- Rule engine: min/max hours per day, duplicate prevention (unique employee+date+project), weekend-logging warning (day-of-week only, no calendar dependency — holiday-aware rules wait for Phase 5's `holiday_calendar`), lock on approved periods with Admin-only reopen, bulk-approve. Project is always required (structural); description is optional by default with a per-company toggle to require it (`timesheet_period_config.require_description`, migration 0005 — flipped from the initial mandatory-by-default so employees can log time first and fill in detail later, not before)
- My Timesheet UI is a full month calendar (not a flat list): the active submission period is outlined inside the month for context, clicking a date inside it opens the log-time dialog and saves it as a draft immediately — the calendar tab is for logging only, it has no submit action
- Submission ranges are free-form, not snapped to `timesheet_period_config`: a **Drafts** tab lets the employee pick any From/To range, review every entry in it (status, rejection reason, edit/delete while still draft/rejected), and submit exactly that range — `timesheet_period_config`'s period type still drives the rule engine and the dashboard's "late" calculation, it just no longer locks submission to one window, so newly-logged entries can always be submitted by picking a range that covers them even if it overlaps something already submitted
- A **My Submissions** tab (every employee) shows the caller's own submission history in Pending / Approved / Rejected sub-tabs; the Approvals queue (for whoever holds `timesheet.approve`) uses the same three-bucket pattern instead of a status dropdown, and gained a per-row **Reopen** action (Admin-only, in the Approved bucket) so approved-in-error submissions don't need a database fix
- Permission fixes carried over from the Phase 1 catalog: Admin gains `timesheet.create`/`timesheet.export` (was missing), Finance gains `timesheet.approve` (needed for the optional Finance sign-off step) — no new permission module, reuses the `timesheet.*` catalog already seeded in migration 0001
- Timesheet dashboard: pending, rejected, late, hours by project/employee, billable %; a dedicated export panel filters CSV output by date range, project, employee, and employee location (opens in Excel, no new dependency) — a formatted `.xlsx`/PDF report is a fast-follow, not blocking this phase
- `employee.location` (nullable, migration 0006) — set at employee creation for a multi-country workforce (e.g. United States / India) specifically so exports can be filtered by it; not a DB enum, same loosely-validated-string pattern as `employment_type`/`status`, so adding a third country later needs no migration
- Reminders (late submission, pending approval) are deferred to a fast-follow once the core flow ships — no scheduler (`celery-beat`) service exists yet, and standing one up before the thing it reminds about is proven isn't worth the added infra now

**Adjusted from the original scope** (see the scope-review discussion before this phase started): the original draft specified a fully configurable Employee→Manager→PM→Finance chain and holiday-aware rules with no holiday table to back them. Both were narrowed — a 2-tier Manager+optional-Finance chain covers the vast majority of real approval flows without a generic workflow engine, and weekend/holiday rules were split so the calendar-dependent half waits for Phase 5. Submission was modeled as period-level (not per-entry) since that's how the rest of the draft's language ("period rules", "late submission") already assumes it works.

**Adjusted after first use, round 1** (direct user feedback once the calendar UI shipped): entries logging and period submission were split into two tabs (Calendar for input, Drafts for review-and-submit) instead of one combined screen, description was made optional by default (see migration 0005 above), and the export gained project/employee/date-range/location filters — which is also why `employee.location` exists.

**Adjusted after first use, round 2** (feedback after trying to log time into an already-submitted period and getting blocked): submission moved from "one fixed period per company config" to a free-form date range chosen at submit time, since the entry-level `submission_id` tracking already made overlapping ranges safe — the fixed-period model was adding a restriction the underlying data model didn't actually need. Self-service submission history (My Submissions) and the bucket-based Approvals restructuring shipped in the same pass since both came from the same request.

**Bug fix after round 2** (round 2 didn't fully fix it): `create_entry` still blocked logging a *new* entry on any date that fell inside an *approved* submission's date range, even if that specific date never had an entry in it — e.g. approve a Mon–Sun submission that only actually had a Monday entry, and Tuesday–Sunday were now permanently unloggable. That check scanned date ranges instead of specific entries; removed it entirely; locking now only applies to editing/deleting an entry that is *itself* already part of an approved submission (already correctly enforced in `update_entry`/`delete_entry` and unaffected by this fix). Same fix applied on the frontend: the calendar's per-period `isLocked` gate (which relied on the same now-defunct exact-range-match assumption from the pre-free-form model) was removed in favor of gating each entry chip by its own status.

## Cross-Phase — CSV Export (Employees, Departments, Projects, Clients)
Requested directly by the user after Timesheets shipped its export panel ("admin should have export in every module, with dates and multiple filters"). Rather than a new phase, this extends the export pattern already proven in Phase 4 to the other list-bearing modules:
- **Employees**: filters on search, department, status, employment type, location, manager, and a `joining_date` range. Gated by `employee.export` — already reserved in the Phase 1 catalog and already granted to Admin/HR, so no permission changes needed there.
- **Departments**: filters on search, parent department, and a `created_at` range (no better date field exists on the model). Required adding `department.export` to the catalog (it didn't exist before) and granting it to Admin.
- **Projects**: filters on status, client, billable flag, and a `start_date` range. `project.export` was already reserved in the Phase 1 catalog but — a real gap found while building this — **never actually granted to Admin**, so Admin couldn't have exported projects even after this ships without the fix. Migration 0007 grants it retroactively.
- **Clients**: reuses `project.export` (same permission-sharing pattern as the rest of the Clients module since Phase 3), filtered by search and a `created_at` range.

All four share the CSV-building helper (`app/utils/csv_export.py`) that Timesheets' export was refactored to use too, rather than four more copies of the same `csv.writer` boilerplate. Scope was deliberately kept to CSV with server-side filters (no `.xlsx`/PDF, no saved filter presets) — same reasoning as Timesheets' export: ship the real, useful version now, formatted reports are a fast-follow if asked for.

## Phase 5 — Leave Management *(shipped)*
- `leave_type` — per-company configurable (name, paid/unpaid, annual quota, max carry-forward days, requires-approval, requires-attachment) — merges the original draft's separate `leave_type` + `leave_policy` into one flat table, same pattern as `document_type` (Phase 2) and `timesheet_period_config` (Phase 4): no separate policy-versioning system for a first version
- `leave_balance` (employee, leave_type, year) — ledger fields (opening, accrued, carried-forward, used, adjustment) rather than a single mutable counter, so it stays encashment-ready and auditable the way Timesheets' entry-level tracking is
- `leave_request` (employee, leave_type, start_date, end_date, reason, optional attachment via the existing Phase 2 S3/document infra, status) — full-day / date-range only; half-day and hourly leave are deferred (see below)
- `holiday_calendar` (per-company: date, name) — also closes the loop Phase 4 left open: Timesheet's weekend-warning rule becomes holiday-aware once this table exists
- Approval chain: Manager always required, with a per-company toggle for an optional final HR sign-off — the same simplified 2-tier shape that worked for Timesheets (not literally shared code; Leave and Timesheets are different entities), and it matches the permissions Manager/HR/Admin already hold since Phase 1 (`leave.approve`/`leave.reject`)
- Balance enforcement: a request is rejected at creation time if pending + approved requests would exceed the available balance — avoids needing a hold/release state machine for "reserved" leave
- Carry-forward: a manual Admin-triggered action (per employee or company-wide) at the year boundary, not an automatic scheduled job — no `celery-beat` introduced this phase, consistent with Phase 4 deferring the same for reminders
- Leave calendar: extends the hand-built calendar component Timesheets already shipped (multi-day leave spans + holidays) rather than adding FullCalendar as a new dependency
- `leave.export` permission + CSV export (date range, leave type, employee, status filters) shipped from the start, applying the cross-module export pattern (Employees/Departments/Projects/Clients/Timesheets) at build time instead of retrofitting it afterward
- Permission fix: `leave.create` added to Admin/HR defaults so they can file leave on behalf of an employee (e.g. recording sick leave after the fact) — currently only Employee has it
- Dashboard: the existing "Leave" placeholder card becomes real (pending leave approvals, who's on leave today)

**Adjusted from the original scope** (scope-review discussion before this phase started): half-day and hourly leave were cut to full-day/date-range only — half-day is a real, common need but was cut anyway this round in favor of shipping the simpler model first; hourly leave specifically needs a work-day-length baseline that doesn't exist until Attendance/shift management (Phase 8), so building it now would mean assuming a placeholder number. The leave calendar reuses Timesheets' hand-built component instead of adding FullCalendar, and carry-forward is a manual Admin action rather than a scheduled job, both to avoid new infrastructure (a JS calendar library; `celery-beat`) for a first version. "Reuses the Phase 4 configurable-chain engine" from the original draft was inaccurate to keep — Phase 4 never built a generic reusable engine, it shipped a simplified Manager+optional-second-approver *pattern*, which Leave now follows on its own terms (Manager + optional HR, vs. Timesheets' Manager + optional Finance).

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
