# Employee Portal — Multi-Tenant SaaS

A commercial-grade, multi-tenant Employee Management Portal (Zoho People–style), built to eventually serve multiple independent customer companies from a single deployment with fully isolated data.

**Phases 1–9c are shipped**: multi-tenant data model, authentication, dynamic RBAC/permission engine, Company/Department/Employee management, a full employee onboarding workflow (configurable document checklist, secure onboarding links, HR review, Admin activation), Projects & Employee Mapping (clients, project CRUD, team assignment, self-service "my projects" view), Timesheets (time entry against assigned projects, configurable period rules, Manager + optional Finance approval chain, bulk approve, dashboard, CSV export), Leave Management (configurable leave types and company holiday calendar, ledger-based balance tracking, Manager + optional HR approval chain, overlap and balance enforcement, on-behalf-of filing, dashboard, CSV export), Assets (asset type catalog, tag/warranty tracking, direct Admin/HR assign & return with no approval step, a ledger-based assignment history, self-service "my assets" view, CSV export), Reporting (a cross-module Reports hub over Employees/Departments/Projects/Timesheets/Leave/Assets/Attendance with on-screen preview before export, and shared saved filter sets), in-app Notifications (a live WebSocket-pushed, persisted-per-user feed triggered by leave/timesheet approvals, asset assignment, and onboarding submissions), Digest Reminders & Outbound Webhooks (a daily `celery-beat` job for work-anniversary, document-expiry, and Admin-configurable, per-location, calendar-anchored timesheet-submission reminders — e.g. weekly for US employees, monthly for India — the last of which re-fires daily until resolved, unlike the other two — plus an Admin-configurable Slack/Teams webhook that mirrors every notification to a shared channel), a role-aware Dashboard (headcount by project for Admins, a self-service "My Projects" view for everyone else, plus New-Hires and Birthdays-This-Week widgets), Attendance (button-based check-in/check-out, configurable shift hours, computed late/overtime flags, a company-wide Today view), White-Label Onboarding Branding & Company Tour (a per-company logo and accent color plus an Admin-authored, skippable welcome-slide stepper, both shown only on the public onboarding link a new hire opens), a Mobile-Responsive UI (a collapsible hamburger nav below the tablet breakpoint, agenda-list views replacing the month grid for logging time/requesting leave on a phone, and every data table scrolling within itself instead of breaking the page), and an Ask HR AI Chatbot (an Admin-configurable, Google Gemini–backed assistant grounded in the company's own leave types and holiday calendar — Admins get the full company-wide leave picture, every other role only ever sees their own balance, never another employee's data) — fully wired end-to-end (React UI → FastAPI → PostgreSQL) rather than shallow-stubbed across every module. See [docs/ROADMAP.md](docs/ROADMAP.md) for what ships in later phases (subscription/billing, auth expansion, Microsoft Teams embedding).

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

**Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth, Celery + Redis, PostgreSQL 16 (with Row-Level Security as defense-in-depth), boto3 (S3/MinIO document storage)
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

This copies `docker/.env.example` to `docker/.env` on first run (auto-generating a real random value for every secret placeholder in it), builds and starts every service, runs migrations, and seeds demo data. When it finishes:

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

### Try White-Label Onboarding Branding & Company Tour

This is aimed at the "we're reselling this to another company, and they want their own brand on it" scenario — scoped specifically to the one page an outside person (a new hire) sees before they're a user of anything: the public onboarding link, not the internal dashboard/login your own staff already knows is a shared platform.

Log in as `admin@acme-demo.com` and open **Onboarding → Branding & Tour**. The two demo companies already come pre-branded with different accent colors (Acme Corp indigo, Globex Inc teal) and a 3-step welcome tour, so you can compare them side by side rather than starting from a blank slate. Upload a logo (PNG/JPEG), change the accent color, and add/edit/reorder/delete tour steps (title + body, with an optional image) — same document-checklist-style CRUD as the tab next to it, reusing the existing `onboarding.configure` permission rather than a new one.

Then repeat the "Try the new-hire side" steps above (create an employee, open their invite link from MailHog in a private window) and watch the onboarding link itself: your logo and company name in the header, your accent color on the buttons, and — since tour steps are configured — a skippable slide-by-slide tour shown first, before the password/document steps. Dismiss it (or finish it) and reload the link: it won't show again on that same link, but a small "View company tour" button lets you replay it. This is intentionally *not* an embeddable widget for a company's own external website — see docs/ROADMAP.md for why — it's a fully on-brand link they can put wherever they want (their careers page, an email template, etc.).

### Try the Dashboard widgets

Log in as `admin@acme-demo.com` and the landing page (**Dashboard**) shows a **Headcount by Project** chart — Admin-only, reusing the same `company.configure` permission that gates Integrations — built from the project list already fetched for the KPI cards above it, no extra request. Log in as `employee@acme-demo.com` instead and that chart is replaced by a **My Projects** card listing just what that employee is assigned to, the same self-service fallback pattern used for "My Hours This Week"/"My Pending Leave Requests."

Everyone (any role) also sees **New Hires (Last 7 Days)** and **Birthdays This Week** cards, computed client-side from the employee list's `joining_date`/`birth_date` fields — no dedicated dashboard endpoint. Riley Employee (`employee@acme-demo.com`) is seeded with a birthday matching today's month/day, so the Birthdays card always has at least one entry to show on first login. `birth_date` is optional — set it from **Employees → New Employee** (or the edit form); leaving it blank just opts that employee out of the birthday widget.

### Try Projects

Each demo company already has a client ("Northwind Trading Co") and two projects — a billable client project and an internal one, both with team members assigned. Log in as `admin@acme-demo.com` and open **Projects** in the sidebar to see the full management view (create/edit projects, manage clients from the "Clients" tab, add/remove team members). Log in as `employee@acme-demo.com` instead to see the same nav item resolve to a read-only "My Projects" view showing only what that employee is assigned to — no budget or client info, matching what a plain Employee role can see.

### Try Timesheets

Each demo company already has a submitted timesheet awaiting approval, an approved one, and a rejected one, so every tab has real data on first login. Log in as `employee@acme-demo.com` and open **Timesheets**:
- **My Timesheet** — a full month calendar (the active week/month is outlined; the rest of the month stays visible for context). Click any date inside the outline to log hours against one of your assigned projects — a description is optional — which saves it as a draft immediately. Click an existing entry chip to edit or delete it. There's no submit action here on purpose.
- **Drafts** — pick any From/To date range, review what's logged in it, and click **Submit** once you're happy with it. Ranges are free-form: you can submit part of a period now and the rest later, even if it overlaps something already submitted, since only entries still in draft (or rejected) ever get swept up.
- **My Submissions** — your own submission history in Pending / Approved / Rejected tabs, so you can always see where something you sent for approval stands.

Log in as `manager@acme-demo.com` to see an **Approvals** tab as well, with the same Pending / Approved / Rejected tab pattern — approve/reject/bulk-approve from Pending, or Reopen an approved-in-error submission if you're an Admin. Log in as `admin@acme-demo.com` to additionally see a **Dashboard** tab — pending/rejected/late counts, hours by project/employee, billable %, and an export panel that filters the CSV by date range, project, employee, and employee location — and a **Settings** tab (period type, min/max hours per day, whether a description is required, whether Finance sign-off is required, and a "Submission Reminders" section — a per-location table of reminder rules, the only role that can change these company-wide rules).

Reminders are configured per employee **location**, not one company-wide toggle: Acme Corp is seeded with a **weekly** rule for "United States" (Alex Admin, Morgan Manager) and a **monthly** rule for "India" (Riley Employee, Casey Finance) — the exact "different cadence per location" scenario this was built for. Globex Inc has no rules at all, so the two demo companies contrast the same way their branding colors do. Cadence is calendar-anchored (the most recently fully-elapsed week or month, not a rolling day count) — click **Add Rule** to add one for a location that doesn't have one yet, or edit/delete an existing one.

Like the other two digest checks below, reminders run once daily via `celery-beat` rather than on demand — to see one fire without waiting for a real week/month to elapse, trigger the job manually:
```bash
docker compose -f docker/docker-compose.yml exec backend python -c "from app.tasks.digest_tasks import run_daily_digest; run_daily_digest()"
```
then check **Notifications** (bell icon) as `employee@acme-demo.com` or `finance@acme-demo.com` for a "Please submit your timesheet" entry once the current week/month is far enough past its grace period. Unlike the work-anniversary/document-expiry reminders below, this one re-fires every day the relevant period stays uncovered, not just once.

Employee location (e.g. "United States" / "India") is set from **Employees → New Employee** (or the edit form) — it exists specifically so the timesheet export can be filtered by it for a multi-country workforce.

**Manager-hierarchy approval**: the Manager step can only be approved/rejected by that specific employee's assigned manager (`Employees → Manager` field), not by any Manager-role user company-wide — you'll still see everyone's pending submissions in the queue, but acting on one outside your reporting line returns a clear "Only this employee's manager or an Admin can approve this submission" error. Since `manager@acme-demo.com` is Riley Employee's assigned manager (set at seed time), their approvals work as expected; Admin can always approve/reject anyone as an override. Try it yourself: assign a different Manager to an employee under **Employees**, then confirm only that specific person (or Admin) can act on their submissions.

### Try Leave

Each demo company already has a leave type catalog (Annual, Sick — requires an attachment, Unpaid — unlimited/untracked), a company-wide holiday (Christmas Day) plus a location-scoped one (Diwali, India-only), and a pending, an approved, and a rejected leave request, so every tab has real data on first login. Log in as `employee@acme-demo.com` (an India-based demo employee) and open **Leave**:
- **My Leave** — a month calendar highlighting your own requests (color-coded by status) and holidays. Only holidays that apply to you show up — company-wide ones, plus any scoped to your own `Employees → location` field — so switching an employee's location (Admin only) changes which holidays they see and which dates get excluded from their leave day-count. Click any date to open the request dialog, or click an existing request chip to jump straight to its bucket below. A **Pending / Approved / Rejected** list below the calendar lets you cancel anything still open.
- **Balances** — granted/carried-forward/adjustment/used/available per leave type for the selected year; "used" is always computed from approved requests rather than stored, so it can never drift.

Log in as `manager@acme-demo.com` to see an **Approvals** tab as well (Pending / Approved / Rejected, same pattern as Timesheets), plus a company-wide view in **Balances**. Log in as `admin@acme-demo.com` to additionally see a **Dashboard** tab (pending count, on-leave-today count, and an export panel filtered by date range, employee, leave type, and status) and a **Settings** tab (leave types and holiday calendar CRUD — holidays can be scoped to "All locations" or one specific location — the HR sign-off toggle, and a manual carry-forward action).

Same manager-hierarchy restriction as Timesheets applies here: only an employee's specifically-assigned manager (or Admin, as an override) can act on their pending request — see "Try Timesheets" above for how to try it yourself. Since a Manager is themselves an employee, their own leave requests route to *their* assigned manager too, not to any `leave.approve` holder — the demo's `manager@acme-demo.com` reports to `admin@acme-demo.com`, so only Admin can approve the Manager's own leave.

Filing leave "on behalf of" another employee (from the request dialog's employee picker) requires `leave.approve`, not just `leave.view` — broad view permissions are company-wide by design, so anything that lets you act as someone else needs a narrower gate, the same lesson the offer-letter feature was rebuilt around (see ROADMAP.md).

### Try Assets

Each demo company already has a small asset type catalog (Laptop, Monitor) and two laptops — one currently assigned, one sitting available — so **Assets** has real data on first login. Log in as `employee@acme-demo.com` and open **Assets** to see a **My Assets** tab: your own currently- and previously-assigned equipment, with no company-wide `asset.view` permission required — every employee can see their own.

Log in as `admin@acme-demo.com` (or `hr@acme-demo.com`) to additionally see **All Assets** (summary counts, filters by type/status, Assign/Return actions, a history icon per row, and an Export CSV button) and **Asset Types** (a simple name catalog). There's no approval step here on purpose — Admin/HR assign and return equipment directly, unlike Timesheets/Leave's approval chains. "Current holder" is never a stored field on the asset; it's always derived from the assignment ledger, so it can't drift out of sync. Log in as `manager@acme-demo.com` to see the same **All Assets**/**Asset Types** tabs in read-only form — Manager holds `asset.view` but not `asset.create`/`update`/`delete`, so the Add/Edit/Delete/Assign/Return controls are hidden.

### Try Reports

Each demo company already has two saved reports ("Active Employees" and "Pending Leave Requests") so **Reports** isn't empty on first login. Log in as `admin@acme-demo.com` and open **Reports**: pick a module from the dropdown (Employees, Departments, Projects, Timesheets, Leave, or Assets), fill in whichever filters you care about, and click **Preview** to see results on-screen before committing to a download — every other export in this app is a blind download, so this is the one place you can look before you export. **Export CSV** downloads the exact same rows using the exact same column set that module's own Export button produces, since Reports reuses each module's existing export logic rather than a second query engine. Click **Save Report** to name and persist the current module + filters — saved reports are shared across everyone with report access, not private to whoever created them, and show up in the **Saved Reports** list on the left for one-click re-running or exporting later.

Log in as `finance@acme-demo.com` to see Preview and Export CSV but no **Save Report** button — Finance holds `report.export` but not `report.configure`, which is Admin-only (narrower than "use", the same pattern as `leave.configure`). Log in as `manager@acme-demo.com` or `hr@acme-demo.com` to see Preview only, no export.

### Try Notifications

Every non-Super-Admin user has a bell icon in the top bar with an unread-count badge. Log in as `manager@acme-demo.com` in one browser tab and `employee@acme-demo.com` in another (or a private window), then in the Employee tab open **Leave** and submit a request — the Manager tab's bell badge updates live, no refresh needed, since it's pushed over a WebSocket the moment the request is created. Click the bell to see the feed (title, detail, timestamp), click a notification to mark it read, or **Mark all read** to clear the badge. Approve or reject that request as Manager and the Employee tab's bell updates the same way.

Notifications fire from: Leave (submitted → the requester's manager; approved/rejected → the requester; filed on someone's behalf → that employee), Timesheets (submitted → manager; approved → submitter), Assets (assigned → the employee), and Onboarding (a new hire finishes uploading documents → everyone holding `onboarding.review`, typically HR). The live push is a bonus on top of a real persisted feed — even without the WebSocket connected, `GET /notifications` always reflects the true state, so refreshing the page never loses anything.

### Try Digest Reminders & Webhooks

Log in as `admin@acme-demo.com` and open **Integrations** (visible only to whoever holds the new `company.configure` permission — Admin by default). Paste any URL into **Webhook URL** and click **Save**, then **Send test message** — since there's no real Slack workspace in this demo environment, check the **backend** container logs for the outbound POST instead of a real channel:
```bash
docker compose -f docker/docker-compose.yml logs -f celery-worker
```
Once a webhook URL is configured, every event that already triggers an in-app notification also posts a plain-text message there — a fan-out event (e.g. onboarding submission notifying every HR reviewer) still only posts once, not once per recipient.

The two digest reminders run once daily via the new `celery-beat` service, so you won't see them fire on demand in the UI — they're a scheduled job, not a request-triggered action. **Work anniversaries** check every active employee's `joining_date` against today's month/day (excluding their hire year); **document expiry** checks every `EmployeeDocument.expiry_date` set by HR at review time (**Onboarding** → a submitted employee → the checkmark on a document opens an "Expiry date (optional)" prompt) and notifies every `onboarding.review` holder exactly 7 days before it expires, once, not once per day in the lookahead window.

### Try Attendance

Every non-Super-Admin user sees **Attendance** in the sidebar. Log in as `employee@acme-demo.com` and open **My Attendance** — the seed data already includes two days of history (one on-time, one late-with-overtime), so it isn't empty on first login. Click **Check In**, then **Check Out**; the card shows whichever action is next, and flags a late check-in or any overtime once you've checked out. You can't check in twice or check out without checking in first — both return a `409`.

Log in as `admin@acme-demo.com` (or `manager@acme-demo.com`/`hr@acme-demo.com`) to additionally see **Today** (every active employee, including "not checked in yet" — not just those with a row) and **Company Attendance** (filterable history + CSV export, export requires `attendance.export` which Manager doesn't hold). Admin also sees **Settings** to change the company-wide shift hours and grace period that drive the late/overtime computation — there's no per-department override yet. Attendance is also selectable as a module in **Reports**, alongside Employees/Leave/Assets/etc.

Check-in/check-out has no GPS or QR scanning behind it — just a server timestamp — consistent with the roadmap's own note that real geofencing/biometrics are external integration points, not built in-house.

### Try the Ask HR chatbot

This needs a free Gemini API key: grab one from **aistudio.google.com/apikey** (no credit card required), then set `GEMINI_API_KEY` in `docker/.env` and restart the backend (`docker compose -f docker/docker-compose.yml up -d --build backend`). Without a key configured, the toggle below still works but the chat itself returns a clear "not configured on this server" error instead of an answer.

Log in as `admin@acme-demo.com` and open **Integrations** — it's enabled for Acme Corp by default in the seed data (Globex Inc isn't, same contrast as everything else seeded that way), toggle-able at the bottom under "HR Assistant". Log in as `employee@acme-demo.com` and open the new **Ask HR** item in the sidebar (it only appears once the setting above is on — if you just flipped it, reload the page first, since that flag is only refreshed on login/reload, not live). Ask it something like *"How many sick days do I have left?"* or *"Is there a holiday coming up?"* — answers come only from this company's own leave types, holiday calendar, and your own leave balances. Conversation history is client-side only — it resets on reload, nothing is persisted server-side.

Access is two-tiered: log back in as `admin@acme-demo.com` and ask **Ask HR** *"Who has pending leave requests?"*, *"Who has pending timesheets?"*, *"Who's checked in today?"*, or *"What assets do we have and who's holding what?"* — Admin gets the full company-wide picture end to end (Leave, Timesheets, Attendance, Assets, by employee name), not just leave. Log in as `employee@acme-demo.com`, `manager@acme-demo.com`, or `hr@acme-demo.com` and ask the same things — none of them can see anything beyond their own leave balance, structurally (the queries for anyone else's data, or for Timesheets/Attendance/Assets at all, are never even run for a non-Admin request, not just withheld by the prompt).

### Try it on mobile

Open http://localhost:8080 on a phone (or shrink a desktop browser window / use its device-emulation mode to a phone width, e.g. Chrome DevTools' device toolbar). The sidebar collapses behind a hamburger icon in the top-left; tap it to open the nav, tap a link to navigate (it auto-closes). **My Timesheet** and **My Leave** switch from the month grid to a scrollable one-day-per-row agenda list — tap a day to log time or request leave exactly like on desktop. Every data table (Employees, approval queues, reports, etc.) scrolls horizontally within itself if it has more columns than fit, rather than forcing the whole page to scroll sideways.

### Try granting Admin rights to an existing employee

Log in as `admin@acme-demo.com`, open **Employees**, and click into any employee (e.g. Riley Employee) — the detail page now shows a **Roles** row. Click the edit (pencil) icon: the same Roles checkbox group used when creating a new employee now also appears here, pre-checked with whatever roles the employee currently holds. Check **Admin** alongside (or instead of) their existing role and **Save changes** — that employee can now log in and do everything an Admin can, including managing other employees' roles themselves.

This is gated on `role.update`, not the broader `employee.update` — log in as `hr@acme-demo.com` and open the same employee's edit dialog to see the Roles section simply isn't there (HR can edit phone/department/etc., but can't promote anyone to Admin). Try removing the Admin role from `admin@acme-demo.com` itself while it's the only Admin account in Acme Corp — it's rejected with a `422` ("Cannot remove the last Admin from this company"), so there's no way to accidentally lock the whole company out of admin access. Promote a second employee to Admin first and the original Admin can then safely step down.

### Try exporting data

Timesheets isn't the only module with an export — as Admin, **Employees**, **Departments**, **Projects**, the **Clients** tab (inside Projects), **Leave**, and **Assets** each have an **Export CSV** button (Assets' lives inline on the All Assets tab rather than a filter dialog) that filters by whatever's relevant to that module: department/status/location/manager for Employees, client/billable/start-date for Projects, leave type/status/employee for Leave, asset type/status for Assets, and so on. All six share the same CSV-building code Timesheets' export uses.

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
   docker compose -f docker/docker-compose.yml up -d --force-recreate backend celery-worker celery-beat
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

The backend test suite includes a dedicated cross-tenant-isolation suite (`backend/tests/integration/test_tenant_isolation.py`) that asserts, through the real HTTP API, that one company's Admin cannot read, list, update, or delete another company's data, a full onboarding-workflow suite (`test_onboarding.py`) covering invite → password → document upload → HR review → Admin activation, a projects suite (`test_projects.py`) covering CRUD, member assignment, cross-tenant rejection, and the self-service "my projects" view, a timesheets suite (`test_timesheets.py`) covering entry/submission/approval lifecycle, the rule engine (duplicate prevention, max-hours-per-day, project-membership), reject-then-resubmit across a different free-form range, independently-submittable overlapping ranges, the optional Finance approval step, bulk approve, admin-only reopen, bucket-filtered submission history, location-filtered export, dashboard/export permission gating, and the manager-hierarchy restriction on the approve/reject action (a Manager who isn't the specific employee's assigned manager gets `403` even though they hold `timesheet.approve`, Admin retains an override, and a Manager's own submission correctly routes to their own assigned manager rather than any Manager-permission holder), a leave suite (`test_leave.py`) covering the Manager + optional-HR approval chain, balance enforcement against held (not just approved) requests, overlap prevention, on-behalf-of filing gated on `leave.approve` rather than `leave.view`, required-attachment enforcement, carry-forward, dashboard/export permission gating, location-scoped holidays (a holiday only excludes a business day for employees at a matching location, and two holidays may share a date as long as their locations differ), and the identical manager-hierarchy restriction on the approve/reject action; an assets suite (`test_assets.py`) covering assign/return with no approval step, rejecting an assign on a non-available asset or a return with no open assignment, blocking a direct `status: "assigned"` update in favor of the assign action, delete guards for in-use asset types and assets with assignment history, permission gating across Admin/HR/Manager/Employee, and the self-scoped `/assets/mine` endpoint that needs no `asset.*` grant; a reports suite (`test_reports.py`) covering preview/export correctness for a filtered module, rejecting an unknown module and invalid per-module filter values, saved-report CRUD including duplicate-name and cross-module filter validation on update, running/exporting a saved report, and permission gating across Admin/HR/Manager/Finance/Employee (view-only vs. export vs. `report.configure`, which is Admin-only); a notifications suite (`test_notifications.py`) covering every trigger point (leave submit/on-behalf-of/approve/reject, timesheet submit/approve, asset assign, onboarding submission fanning out to every HR-review-permission holder), self-scoping (a notification can only be marked read by its own recipient, and is invisible cross-tenant), unread-count/mark-read/mark-all-read, and rejecting an invalid WebSocket auth token before `accept()`; a digests-and-webhooks suite (`test_digests_and_webhooks.py`) covering `company.configure` permission gating on the new Integrations endpoints, webhook dispatch firing exactly once per event (including a two-recipient fan-out that must still post a single message), no dispatch when no webhook URL is configured, and the two digest reminder types (work-anniversary matching on month/day while excluding the hire year, and document-expiry matching only at the exact 7-day lead time, not a rolling window); an attendance suite (`test_attendance.py`) covering the check-in/check-out happy path and its conflict rules (no double check-in, no check-out without checking in, no double check-out), self-scoping on `/mine`, permission gating across Admin/Manager/HR/Employee for company-wide view/export/configure, the Today dashboard distinguishing checked-in from not-yet-checked-in, cross-tenant isolation, Attendance's inclusion as a Reports module, and late/overtime computation against an explicit injected time (the same testable-seam pattern the digest task's `today` parameter uses, since real wall-clock time can't be controlled from a test); a branding-and-tour suite (`test_branding_and_tour.py`) covering `onboarding.configure`/`onboarding.view` permission gating on the new Branding and Company Tour endpoints, hex-color validation, logo/tour-image content-type rejection for non-images, full tour-step CRUD (including sort-order), the public onboarding context correctly reflecting both an unconfigured company (null branding, empty tour) and a configured one (ordered tour steps, accent color), and cross-tenant isolation of both; a role-assignment suite (`test_role_assignment.py`) covering granting the Admin role to an existing employee (confirmed by logging in as them afterward and hitting an Admin-only endpoint), that HR is blocked despite holding `employee.update` (gated on `role.update` specifically), Manager/Employee rejection, cross-tenant `role_id` rejection, and the last-Admin guard (blocked when it's the sole remaining Admin, allowed once a second Admin exists); a dashboard-widgets-and-reminders suite (`test_dashboard_widgets_and_reminders.py`) covering `birth_date` settable/clearable on create and update and returned on both detail and summary responses, per-location reminder rule CRUD (default vs. location-scoped rules, duplicate-location rejection, invalid-cadence rejection, `timesheet.configure`-gated mutation with `timesheet.view`-only read access), calendar-anchored weekly and monthly cadence firing only once their grace period elapses, a location-specific rule taking precedence over the default rule, no reminder for a location matching no rule and no default, no reminder for an employee with no project membership or who joined after the period in question, and — the key differentiator versus the work-anniversary/document-expiry digests — the same uncovered period triggering a reminder again the next day (not deduplicated) and stopping the moment a submission actually covers it; an AI chatbot suite (`test_ai_chatbot.py`) covering the `company.ai_chatbot_enabled` toggle (disabled by default, `company.configure`-gated, reflected on `/auth/me`), `/ai/chat` rejecting with `422` when the company hasn't enabled it and `503` when the server has no `GEMINI_API_KEY` configured or the upstream call fails/times out, cross-tenant isolation of the enabled flag, prior conversation turns correctly replayed as history on each call, and — with the real Gemini call mocked via the same `httpx.post` monkeypatch seam `test_digests_and_webhooks.py` already established — the two-tier context split: an Admin's prompt containing another employee's name and the full pending-request queue plus company-wide Timesheets/Attendance/Assets sections, while the identical question asked by an Employee, Manager, HR, or Finance user never has any other employee's name, the company-wide leave queue, or any Timesheets/Attendance/Assets data anywhere in its context; and an exports suite (`test_exports.py`) covering permission gating and filter correctness for the Employees, Departments, Projects, and Clients CSV exports.

## Security Notes for Deployment

- Rotate `SECRET_KEY` and every demo password before exposing this beyond local development.
- Postgres Row-Level Security is enabled on tenant tables as defense-in-depth behind the repository-layer tenant scoping, and is real enforcement, not a no-op: `docker-compose.yml` provisions a dedicated non-superuser, non-`BYPASSRLS` role (`APP_DB_USER`) that the app connects as at runtime, distinct from the superuser role (`POSTGRES_USER`) migrations run as — see [docs/HLD.md §4](docs/HLD.md#4-multi-tenancy-strategy) for the full mechanism, including the one deliberate RLS exemption (`onboarding_invite`, looked up by token before a company context exists).
- `docker-compose.yml` refuses to start without `POSTGRES_PASSWORD`, `SECRET_KEY`, `APP_DB_PASSWORD`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY` set to real values in `docker/.env` (no insecure fallback default) — see `docker/.env.example` for the full list, including `MIGRATION_DATABASE_URL` (superuser, migrations only) vs. `DATABASE_URL` (restricted role, app runtime).
- MinIO's ports (9000 API, 9001 console) are bound to `127.0.0.1` by default, not every network interface — only nginx is meant to be reachable from outside the host. Set `S3_HOST_BIND=0.0.0.0` only if you deliberately want MinIO reachable directly from other machines.
- `/docs` and `/openapi.json` are automatically disabled (`404`) when `APP_ENV=production`, which `docker-compose.yml` always sets — don't rely on Swagger UI being reachable in that environment; see `docs/API_CONTRACTS.md` for the maintained contract reference instead.
- `/auth/login` is rate-limited (`AUTH_RATE_LIMIT`, default 5/minute per IP) and `/ai/chat` is rate-limited per-user (`AI_CHAT_RATE_LIMIT_PER_MINUTE`, default 10/minute) — see `docs/API_CONTRACTS.md`.
- File uploads (branding logo, company tour images, onboarding documents, leave attachments) are validated by actual file-signature bytes, not the client-declared content type, which is trivially spoofable.
- Outbound webhook URLs (Slack/Teams integration) are validated against SSRF at both save time and delivery time — must be `https://` and must not resolve to a private/loopback/link-local/reserved address.
- `CORS_ORIGINS`, `SMTP_*`, and `S3_*` in `docker/.env` / `backend/.env` all need real values outside local dev.
- TLS termination is not configured in the provided Nginx configs — add it (or terminate TLS at a load balancer in front of this stack) before serving real traffic.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the phase-by-phase plan: projects, timesheets, leave management, assets, reporting, notifications, attendance, subscription/billing, and AI features. Each phase builds on the Phase 1 & 2 foundation without requiring breaking schema changes.
