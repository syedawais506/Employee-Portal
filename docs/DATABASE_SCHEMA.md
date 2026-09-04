# Database Schema — Phase 1, 2, 3, 4, 5, 6, 7 & 7b

PostgreSQL 16. All tenant-owned tables carry `company_id`. UUID primary keys are generated in the application (Python `uuid.uuid4()`), not by a Postgres extension. All tables have `created_at`, `updated_at`; soft-deletable tables also have `deleted_at`.

## ER Diagram

```mermaid
erDiagram
    COMPANY ||--o{ DEPARTMENT : has
    COMPANY ||--o{ ROLE : defines
    COMPANY ||--o{ USER_ACCOUNT : employs
    COMPANY ||--o{ EMPLOYEE : has
    COMPANY ||--o{ AUDIT_LOG : scopes

    DEPARTMENT ||--o{ EMPLOYEE : contains
    DEPARTMENT }o--o| DEPARTMENT : "parent (self-ref)"

    ROLE ||--o{ ROLE_PERMISSION : grants
    PERMISSION ||--o{ ROLE_PERMISSION : "granted via"
    USER_ACCOUNT ||--o{ USER_ROLE : "assigned"
    ROLE ||--o{ USER_ROLE : "assigned to"

    USER_ACCOUNT ||--|| EMPLOYEE : "profile of"
    EMPLOYEE }o--o| EMPLOYEE : "manager (self-ref)"

    COMPANY ||--o{ DOCUMENT_TYPE : configures
    COMPANY ||--o{ EMPLOYEE_DOCUMENT : scopes
    COMPANY ||--o{ ONBOARDING_INVITE : scopes
    EMPLOYEE ||--o{ EMPLOYEE_DOCUMENT : uploads
    EMPLOYEE ||--|| ONBOARDING_INVITE : "invited via"
    DOCUMENT_TYPE ||--o{ EMPLOYEE_DOCUMENT : "instance of"

    COMPANY ||--o{ CLIENT : has
    COMPANY ||--o{ PROJECT : has
    CLIENT ||--o{ PROJECT : "billed to"
    PROJECT ||--o{ PROJECT_MEMBER : staffs
    EMPLOYEE ||--o{ PROJECT_MEMBER : "assigned to"

    COMPANY ||--o| TIMESHEET_PERIOD_CONFIG : configures
    COMPANY ||--o{ TIMESHEET_SUBMISSION : scopes
    COMPANY ||--o{ TIMESHEET_ENTRY : scopes
    EMPLOYEE ||--o{ TIMESHEET_ENTRY : logs
    PROJECT ||--o{ TIMESHEET_ENTRY : "hours against"
    EMPLOYEE ||--o{ TIMESHEET_SUBMISSION : submits
    TIMESHEET_SUBMISSION ||--o{ TIMESHEET_ENTRY : groups

    COMPANY ||--o{ LEAVE_TYPE : configures
    COMPANY ||--o{ HOLIDAY_CALENDAR : configures
    COMPANY ||--o{ LEAVE_BALANCE : scopes
    COMPANY ||--o{ LEAVE_REQUEST : scopes
    EMPLOYEE ||--o{ LEAVE_BALANCE : has
    EMPLOYEE ||--o{ LEAVE_REQUEST : requests
    LEAVE_TYPE ||--o{ LEAVE_BALANCE : "tracked as"
    LEAVE_TYPE ||--o{ LEAVE_REQUEST : "instance of"

    COMPANY ||--o{ ASSET_TYPE : configures
    COMPANY ||--o{ ASSET : owns
    COMPANY ||--o{ ASSET_ASSIGNMENT : scopes
    ASSET_TYPE ||--o{ ASSET : "instance of"
    ASSET ||--o{ ASSET_ASSIGNMENT : "assigned via"
    EMPLOYEE ||--o{ ASSET_ASSIGNMENT : holds
    COMPANY ||--o{ SAVED_REPORT : configures
    COMPANY ||--o{ NOTIFICATION : scopes
    USER_ACCOUNT ||--o{ NOTIFICATION : receives

    TIMESHEET_PERIOD_CONFIG {
        uuid id PK
        uuid company_id FK UK "one config per company"
        string period_type "daily|weekly|monthly"
        int week_start_day "0=Monday..6=Sunday, weekly only"
        numeric min_hours_per_day "nullable"
        numeric max_hours_per_day "nullable, default 24"
        bool require_description
        bool warn_on_weekend
        bool require_finance_approval
    }

    TIMESHEET_SUBMISSION {
        uuid id PK
        uuid company_id FK
        uuid employee_id FK
        date period_start
        date period_end
        string status "submitted|manager_approved|approved|rejected"
        timestamptz submitted_at
        uuid manager_approved_by FK "nullable"
        timestamptz manager_approved_at "nullable"
        uuid finance_approved_by FK "nullable"
        timestamptz finance_approved_at "nullable"
        uuid rejected_by FK "nullable"
        timestamptz rejected_at "nullable"
        string rejection_reason "nullable"
    }

    TIMESHEET_ENTRY {
        uuid id PK
        uuid company_id FK
        uuid employee_id FK
        uuid project_id FK "ON DELETE RESTRICT"
        uuid submission_id FK "nullable — null while still a draft"
        date entry_date
        numeric hours
        bool is_billable
        string work_type "office|remote|client_site"
        string description "nullable"
    }

    LEAVE_TYPE {
        uuid id PK
        uuid company_id FK
        string name "UNIQUE per company"
        bool is_paid
        int annual_quota_days "nullable = unlimited/untracked"
        int max_carry_forward_days
        bool requires_attachment
    }

    HOLIDAY_CALENDAR {
        uuid id PK
        uuid company_id FK
        date date "UNIQUE per company + location"
        string name
        string location "nullable = all locations; else must match employee.location"
    }

    LEAVE_BALANCE {
        uuid id PK
        uuid company_id FK
        uuid employee_id FK
        uuid leave_type_id FK
        int year
        numeric granted
        numeric carried_forward
        numeric adjustment
    }

    LEAVE_REQUEST {
        uuid id PK
        uuid company_id FK
        uuid employee_id FK
        uuid leave_type_id FK "ON DELETE RESTRICT"
        date start_date
        date end_date
        int days_count "business days, holidays/weekends excluded"
        string reason "nullable"
        string attachment_file_key "nullable"
        string status "pending|manager_approved|approved|rejected|cancelled"
        uuid manager_approved_by FK "nullable"
        timestamptz manager_approved_at "nullable"
        uuid hr_approved_by FK "nullable"
        timestamptz hr_approved_at "nullable"
        uuid rejected_by FK "nullable"
        timestamptz rejected_at "nullable"
        string rejection_reason "nullable"
        timestamptz cancelled_at "nullable"
    }

    ASSET_TYPE {
        uuid id PK
        uuid company_id FK
        string name "UNIQUE per company"
    }

    ASSET {
        uuid id PK
        uuid company_id FK
        uuid asset_type_id FK "ON DELETE RESTRICT"
        string asset_tag "UNIQUE per company"
        string name
        date purchase_date "nullable"
        date warranty_expiry "nullable"
        string status "available|assigned|retired|lost|damaged"
        string notes "nullable"
    }

    ASSET_ASSIGNMENT {
        uuid id PK
        uuid company_id FK
        uuid asset_id FK
        uuid employee_id FK
        timestamptz assigned_at
        uuid assigned_by FK "nullable"
        timestamptz returned_at "nullable"
        uuid returned_by FK "nullable"
    }

    SAVED_REPORT {
        uuid id PK
        uuid company_id FK
        string name "UNIQUE per company"
        string module "employee|department|project|timesheet|leave|asset"
        jsonb filters
        uuid created_by FK "nullable"
    }

    NOTIFICATION {
        uuid id PK
        uuid company_id FK
        uuid user_id FK "recipient"
        string type "e.g. leave.approved, asset.assigned"
        string title
        string body "nullable"
        string entity_type "nullable, loose reference"
        uuid entity_id "nullable"
        bool is_read
    }

    CLIENT {
        uuid id PK
        uuid company_id FK
        string name
        string contact_name
        string contact_email
        string contact_phone
    }

    PROJECT {
        uuid id PK
        uuid company_id FK
        uuid client_id FK "nullable"
        string name
        numeric budget "nullable"
        bool is_billable
        date start_date
        date end_date
        string status "active|on_hold|completed|cancelled"
    }

    PROJECT_MEMBER {
        uuid project_id FK
        uuid employee_id FK
        string role_on_project "manager|member"
    }

    DOCUMENT_TYPE {
        uuid id PK
        uuid company_id FK
        string name
        bool is_required
        int sort_order
        timestamptz created_at
    }

    EMPLOYEE_DOCUMENT {
        uuid id PK
        uuid company_id FK
        uuid employee_id FK
        uuid document_type_id FK
        string file_key "S3/MinIO object key"
        string original_filename
        string content_type
        int size_bytes
        string status "pending|approved|rejected"
        string review_notes
        uuid reviewed_by FK
        timestamptz reviewed_at
        timestamptz uploaded_at
    }

    ONBOARDING_INVITE {
        uuid id PK
        uuid company_id FK
        uuid employee_id FK UK
        string token_hash UK "SHA-256, raw token never stored"
        timestamptz expires_at
        timestamptz used_at "set once the new hire sets a password"
        timestamptz created_at
    }

    COMPANY {
        uuid id PK
        string name
        string slug UK
        string subdomain UK
        string status
        timestamptz created_at
        timestamptz deleted_at
    }

    DEPARTMENT {
        uuid id PK
        uuid company_id FK
        string name
        uuid parent_department_id FK
        timestamptz created_at
    }

    USER_ACCOUNT {
        uuid id PK
        uuid company_id FK "nullable for super admin"
        string email UK
        string password_hash
        bool is_super_admin
        bool is_active
        bool is_verified
        string auth_provider "local|google|microsoft"
        bool mfa_enabled
        timestamptz created_at
    }

    EMPLOYEE {
        uuid id PK
        uuid company_id FK
        uuid user_id FK UK
        string employee_code
        string first_name
        string last_name
        string phone
        uuid department_id FK
        string designation
        uuid manager_id FK
        string employment_type
        string location "nullable — e.g. United States, India; set at employee creation, filters timesheet exports"
        date joining_date
        string status
        string onboarding_status "invited|submitted|hr_approved|completed"
    }

    ROLE {
        uuid id PK
        uuid company_id FK "nullable for platform-level system roles"
        string name
        bool is_system
    }

    PERMISSION {
        uuid id PK
        string module
        string action
    }

    ROLE_PERMISSION {
        uuid role_id FK
        uuid permission_id FK
    }

    USER_ROLE {
        uuid user_id FK
        uuid role_id FK
    }

    AUDIT_LOG {
        uuid id PK
        uuid company_id FK
        uuid actor_user_id FK
        string entity_type
        uuid entity_id
        string action
        jsonb before
        jsonb after
        string ip_address
        string user_agent
        timestamptz created_at
    }
```

---

## Table Definitions (DDL-level detail)

### `company`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| name | varchar(255) NOT NULL | |
| slug | varchar(100) UNIQUE NOT NULL | URL-safe identifier |
| subdomain | varchar(100) UNIQUE | reserved for future subdomain-per-tenant routing |
| status | varchar(20) NOT NULL DEFAULT 'active' | active / suspended / cancelled |
| require_hr_leave_approval | boolean NOT NULL DEFAULT false | *(Phase 5)* adds the optional HR sign-off step after Manager approval on leave requests |
| slack_webhook_url | varchar(500) NULL | *(Phase 7c)* Admin-configured Slack incoming-webhook or Teams connector URL; when set, every event that already triggers an in-app notification also posts a plain-text message here |
| logo_key | varchar(512) NULL | *(Phase 9c)* S3/MinIO object key for the company's logo — same private-bucket-plus-presigned-URL pattern as employee documents, not a public URL stored directly |
| primary_color | varchar(20) NULL | *(Phase 9c)* hex accent color (e.g. `#4F46E5`) applied to the public onboarding link's buttons |
| created_at, updated_at | timestamptz | |
| deleted_at | timestamptz NULL | soft delete |

### `department`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| name | varchar(255) NOT NULL | |
| parent_department_id | uuid FK → department.id NULL | self-referential, same company |
| cost_center_code | varchar(50) NULL | |
| created_at, updated_at | timestamptz | |
| | | `UNIQUE(company_id, name)` |

### `user_account`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NULL | NULL only for `is_super_admin=true` |
| email | varchar(255) UNIQUE NOT NULL | normalized to lowercase at the repository layer for case-insensitive matching |
| password_hash | varchar(255) NOT NULL | bcrypt/argon2 |
| is_super_admin | boolean NOT NULL DEFAULT false | |
| is_active | boolean NOT NULL DEFAULT true | |
| is_verified | boolean NOT NULL DEFAULT false | |
| auth_provider | varchar(20) NOT NULL DEFAULT 'local' | local / google / microsoft (future) |
| mfa_enabled | boolean NOT NULL DEFAULT false | reserved |
| mfa_secret | varchar(255) NULL | reserved, encrypted at rest |
| last_login_at | timestamptz NULL | |
| created_at, updated_at | timestamptz | |

### `employee`
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| user_id | uuid FK → user_account.id UNIQUE NOT NULL | 1:1 |
| employee_code | varchar(50) NOT NULL | `UNIQUE(company_id, employee_code)` |
| first_name, last_name | varchar(100) NOT NULL | |
| phone | varchar(30) NULL | |
| department_id | uuid FK → department.id NULL | must be same company (service-layer check) |
| designation | varchar(150) NULL | |
| manager_id | uuid FK → employee.id NULL | self-ref, must be same company |
| employment_type | varchar(30) NOT NULL DEFAULT 'full_time' | full_time / part_time / contract / intern |
| location | varchar(100) NULL | free text, not a DB enum (same pattern as employment_type/status) — UI offers "United States" / "India" as presets; set at employee creation, used to filter timesheet exports across a multi-country workforce *(migration 0006)* |
| joining_date | date NULL | |
| birth_date | date NULL | optional; month/day drives the "Birthdays This Week" dashboard widget *(migration 0016)* |
| status | varchar(20) NOT NULL DEFAULT 'active' | active / on_leave / exited |
| onboarding_status | varchar(20) NOT NULL DEFAULT 'completed' | invited / submitted / hr_approved / completed — `'completed'` default backfills pre-Phase-2 rows and lets seed/admin-created rows opt out of the invite flow |
| created_at, updated_at | timestamptz | |
| deleted_at | timestamptz NULL | |

### `document_type` *(Phase 2)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| name | varchar(150) NOT NULL | `UNIQUE(company_id, name)` |
| is_required | boolean NOT NULL DEFAULT true | admin-toggleable per company |
| sort_order | int NOT NULL DEFAULT 0 | display order in the checklist |
| created_at, updated_at | timestamptz | |

### `company_tour_step` *(Phase 9c)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| title | varchar(150) NOT NULL | |
| body | varchar(2000) NOT NULL | |
| image_key | varchar(512) NULL | optional slide image, same private-bucket-plus-presigned-URL pattern as `company.logo_key` |
| sort_order | int NOT NULL DEFAULT 0 | display order in the tour |
| created_at, updated_at | timestamptz | |

An Admin-authored, ordered list of welcome slides shown to a new hire on the public onboarding page before they set a password — same company-scoped catalog shape as `document_type` (no approval step, no versioning; edit or delete in place). No "seen" flag stored here or anywhere else — whether a given onboarding link has already shown the tour is tracked client-side only (localStorage, keyed by the onboarding token).

### `employee_document` *(Phase 2)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id NOT NULL | |
| document_type_id | uuid FK → document_type.id NOT NULL | `UNIQUE(employee_id, document_type_id)` — re-upload replaces in place |
| file_key | varchar(512) NOT NULL | object key in the S3/MinIO bucket, not the file itself |
| original_filename, content_type | varchar | |
| size_bytes | int NOT NULL | validated ≤ 10 MB at upload time |
| status | varchar(20) NOT NULL DEFAULT 'pending' | pending / approved / rejected |
| review_notes | varchar(500) NULL | shown back to the employee on rejection |
| reviewed_by | uuid FK → user_account.id NULL | |
| reviewed_at | timestamptz NULL | |
| expiry_date | date NULL | *(Phase 7c)* optionally set by HR at review time (visa, ID card, etc.); the daily digest notifies `onboarding.review` holders exactly 7 days before this date |
| uploaded_at | timestamptz | |

### `onboarding_invite` *(Phase 2)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id UNIQUE NOT NULL | one invite per employee |
| token_hash | varchar(64) UNIQUE NOT NULL | SHA-256 hex digest; the raw token is emailed once and never persisted |
| expires_at | timestamptz NOT NULL | 7 days from creation |
| used_at | timestamptz NULL | set when the new hire sets their password — doubles as the "password already set" flag |
| created_at | timestamptz | |

### `client` *(Phase 3)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| name | varchar(255) NOT NULL | `UNIQUE(company_id, name)` |
| contact_name | varchar(150) NULL | |
| contact_email | varchar(255) NULL | |
| contact_phone | varchar(30) NULL | |
| created_at, updated_at | timestamptz | |

### `project` *(Phase 3)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| client_id | uuid FK → client.id NULL, `ON DELETE SET NULL` | |
| name | varchar(255) NOT NULL | `UNIQUE(company_id, name)` |
| budget | numeric(12,2) NULL | |
| is_billable | boolean NOT NULL DEFAULT true | |
| start_date, end_date | date NULL | |
| status | varchar(20) NOT NULL DEFAULT 'active' | active / on_hold / completed / cancelled |
| created_at, updated_at | timestamptz | |

### `project_member` *(Phase 3)*
| Column | Type | Notes |
|---|---|---|
| project_id | uuid FK → project.id, `ON DELETE CASCADE` | composite PK with employee_id |
| employee_id | uuid FK → employee.id, `ON DELETE CASCADE` | composite PK with project_id |
| role_on_project | varchar(20) NOT NULL DEFAULT 'member' | manager / member |

A pure join table — no `company_id` of its own, same pattern as `role_permission`/`user_role`. Tenant isolation comes from always resolving the `project` row (company-scoped) before touching membership rows, not from RLS on this table.

### `timesheet_period_config` *(Phase 4)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | one row per company, lazily created on first access |
| period_type | varchar(20) NOT NULL DEFAULT 'weekly' | daily / weekly / monthly — bi-weekly and fully custom periods are deferred (see ROADMAP.md) |
| week_start_day | int NOT NULL DEFAULT 0 | 0=Monday..6=Sunday; only meaningful when period_type='weekly' |
| min_hours_per_day | numeric(4,2) NULL | enforced per-day at submission time, only for days that already have an entry |
| max_hours_per_day | numeric(4,2) NULL DEFAULT 24 | enforced per-day at entry create/update time, across all of that employee's projects |
| require_description | boolean NOT NULL DEFAULT false | project is always required structurally; this only gates description *(renamed + default flipped in migration 0005 — employees log time and submit later, so a mandatory description up front didn't fit that flow)* |
| warn_on_weekend | boolean NOT NULL DEFAULT true | UI-only flag (`TimesheetEntry.is_weekend`), not a hard block |
| require_finance_approval | boolean NOT NULL DEFAULT false | adds the optional second approval step |
| reminder_enabled | boolean NOT NULL DEFAULT false | opt-in; when on, `run_daily_digest` re-fires a "please submit your timesheet" notification + email every day the condition below holds — NOT exactly-once like the anniversary/document-expiry digests *(migration 0016)* |
| reminder_after_days | int NOT NULL DEFAULT 3 | days since an employee's last submission (or since `joining_date` if they've never submitted) before the reminder starts *(migration 0016)* |
| created_at, updated_at | timestamptz | |

### `timesheet_submission` *(Phase 4)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id NOT NULL | |
| period_start, period_end | date NOT NULL | `UNIQUE(employee_id, period_start, period_end)` — one submission per employee per period; rejected submissions are reused (status reset) rather than duplicated on resubmit |
| status | varchar(20) NOT NULL DEFAULT 'submitted' | submitted → (manager_approved, only if `require_finance_approval`) → approved; or → rejected at either step |
| submitted_at | timestamptz NOT NULL | |
| manager_approved_by, manager_approved_at | uuid FK → user_account.id / timestamptz, NULL | |
| finance_approved_by, finance_approved_at | uuid FK → user_account.id / timestamptz, NULL | only set when `require_finance_approval` |
| rejected_by, rejected_at, rejection_reason | uuid FK / timestamptz / varchar(500), NULL | |
| created_at, updated_at | timestamptz | |

### `timesheet_entry` *(Phase 4)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id NOT NULL | |
| project_id | uuid FK → project.id NOT NULL, `ON DELETE RESTRICT` | must be a project the employee is a `project_member` of (service-layer check); `RESTRICT` because Project's hard delete would otherwise silently destroy logged-hours history — `project_service.delete_project` checks for existing entries first and returns 409 |
| submission_id | uuid FK → timesheet_submission.id NULL, `ON DELETE SET NULL` | null while still a draft; set when the period is submitted |
| entry_date | date NOT NULL | `UNIQUE(employee_id, entry_date, project_id)` — duplicate-entry prevention |
| hours | numeric(4,2) NOT NULL | |
| is_billable | boolean NOT NULL DEFAULT true | |
| work_type | varchar(20) NOT NULL DEFAULT 'office' | office / remote / client_site |
| description | varchar(500) NULL | required when `require_description` is set |
| created_at, updated_at | timestamptz | |

Entry status (`draft`/`submitted`/`manager_approved`/`approved`/`rejected`) is not its own column — it's a computed property that reads the linked submission's status (or `"draft"` if `submission_id` is null), so the two can never drift out of sync.

### `leave_type` *(Phase 5)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| name | varchar(100) NOT NULL | `UNIQUE(company_id, name)` |
| is_paid | boolean NOT NULL DEFAULT true | |
| annual_quota_days | int NULL | `NULL` = unlimited/untracked (e.g. Unpaid Leave) — skips balance enforcement entirely |
| max_carry_forward_days | int NOT NULL DEFAULT 0 | cap applied by the carry-forward job, not enforced at request time |
| requires_attachment | boolean NOT NULL DEFAULT false | e.g. Sick Leave requiring a medical certificate |
| created_at, updated_at | timestamptz | |

### `holiday_calendar` *(Phase 5)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| date | date NOT NULL | `UNIQUE(company_id, date, location)` *(migration 0009)* |
| name | varchar(150) NOT NULL | |
| location | varchar(100) NULL | `NULL` = applies company-wide to every employee; set (e.g. `"India"`) = only excluded from business-day math and shown on the calendar for employees whose `employee.location` matches exactly *(migration 0009)* |
| created_at, updated_at | timestamptz | |

Two holidays can share the same date as long as their `location` differs (e.g. a company-wide holiday and an India-only one on the same day) — Postgres treats `NULL` as distinct from itself for uniqueness purposes, so the service layer additionally checks for an exact `(date, location)` duplicate (including two `NULL`-location rows) before insert, rather than relying on the DB constraint alone.

### `leave_balance` *(Phase 5)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id NOT NULL | |
| leave_type_id | uuid FK → leave_type.id NOT NULL | `UNIQUE(employee_id, leave_type_id, year)` |
| year | int NOT NULL | |
| granted | numeric(5,1) NOT NULL DEFAULT 0 | seeded from `leave_type.annual_quota_days` when the row is first created |
| carried_forward | numeric(5,1) NOT NULL DEFAULT 0 | set by the carry-forward action, capped at `max_carry_forward_days` |
| adjustment | numeric(5,1) NOT NULL DEFAULT 0 | manual admin correction, reserved for future use — not yet exposed in the UI |
| created_at, updated_at | timestamptz | |

`used` and `available` are never stored — `used` is computed by summing `leave_request.days_count` for that employee/type/year across `approved` requests, and `available = granted + carried_forward + adjustment - used`, matching the "compute from source records" approach already used for Timesheets' entry status.

### `leave_request` *(Phase 5)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id NOT NULL | who the leave is for — may differ from the filer when filed on behalf of another employee |
| leave_type_id | uuid FK → leave_type.id NOT NULL, `ON DELETE RESTRICT` | mirrors `timesheet_entry.project_id` — a leave type with requests logged against it can't be hard-deleted |
| start_date, end_date | date NOT NULL | inclusive range; full-day only (no half-day/hourly granularity — see ROADMAP.md) |
| days_count | int NOT NULL | business days in the range, excluding weekends and `holiday_calendar` dates |
| reason | varchar(500) NULL | |
| attachment_file_key, attachment_original_filename | varchar NULL | object key in the S3/MinIO bucket, same pattern as `employee_document` |
| status | varchar(20) NOT NULL DEFAULT 'pending' | pending → (manager_approved, only if `company.require_hr_leave_approval`) → approved; or → rejected/cancelled at any open step |
| manager_approved_by, manager_approved_at | uuid FK → user_account.id / timestamptz, NULL | |
| hr_approved_by, hr_approved_at | uuid FK → user_account.id / timestamptz, NULL | only set when `require_hr_leave_approval` |
| rejected_by, rejected_at, rejection_reason | uuid FK / timestamptz / varchar(500), NULL | |
| cancelled_at | timestamptz NULL | self-service cancel, or by anyone holding `leave.approve` on the employee's behalf |
| created_at, updated_at | timestamptz | |

No two open (`pending`/`manager_approved`/`approved`) requests for the same employee may have overlapping date ranges, regardless of leave type — enforced at the service layer, not a DB constraint.

### `asset_type` *(Phase 6)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| name | varchar(100) NOT NULL | `UNIQUE(company_id, name)` |
| created_at, updated_at | timestamptz | |

### `asset` *(Phase 6)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| asset_type_id | uuid FK → asset_type.id NOT NULL, `ON DELETE RESTRICT` | an asset type with assets against it can't be hard-deleted, same pattern as `leave_type`/`project` |
| asset_tag | varchar(100) NOT NULL | `UNIQUE(company_id, asset_tag)` — serial number / tag |
| name | varchar(150) NOT NULL | |
| purchase_date, warranty_expiry | date NULL | plain dates — no expiry alerting this phase (needs Phase 7's notification infra) |
| status | varchar(20) NOT NULL DEFAULT 'available' | available / assigned / retired / lost / damaged — `assigned` is kept in sync by the assign/return actions; the other three are edited directly, since they aren't assignment events |
| notes | varchar(1000) NULL | |
| created_at, updated_at | timestamptz | |

### `asset_assignment` *(Phase 6)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| asset_id | uuid FK → asset.id NOT NULL, `ON DELETE CASCADE` | |
| employee_id | uuid FK → employee.id NOT NULL | |
| assigned_at | timestamptz NOT NULL | |
| assigned_by | uuid FK → user_account.id NULL | |
| returned_at, returned_by | timestamptz / uuid FK → user_account.id, NULL | `NULL` = still open (the asset's current holder) |
| created_at, updated_at | timestamptz | |

A ledger, not a mutable "current holder" column on `asset` — same "compute from source records" approach as Leave's balance ledger and Timesheets' entry status. "Who has this asset now" is the row with `returned_at IS NULL`; "history per employee" is every row for that `employee_id`. At most one open assignment per asset at a time, enforced at the service layer (mirrors Leave's overlap-prevention check) — assigning a non-`available` asset, or returning one with no open assignment, is rejected (`409`). Unlike Timesheets/Leave, there's no approval step here: Admin/HR assign and return directly.

### `attendance_shift_config` *(Phase 9a)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | one row per company, lazily created on first access — same "get-or-create" pattern as `timesheet_period_config` |
| shift_start | time NOT NULL DEFAULT 09:00 | |
| shift_end | time NOT NULL DEFAULT 18:00 | |
| grace_period_minutes | int NOT NULL DEFAULT 15 | how late a check-in can be before `attendance_record.is_late` is set |
| created_at, updated_at | timestamptz | |

### `attendance_record` *(Phase 9a)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| employee_id | uuid FK → employee.id NOT NULL | `UNIQUE(employee_id, attendance_date)` — one row per employee per day |
| attendance_date | date NOT NULL | |
| check_in_at | timestamptz NULL | set by `POST /attendance/check-in`; the row itself is only created at check-in time |
| check_out_at | timestamptz NULL | set by `POST /attendance/check-out` |
| is_late | boolean NOT NULL DEFAULT false | computed at check-in against `attendance_shift_config.shift_start + grace_period_minutes` |
| overtime_hours | numeric(4,2) NOT NULL DEFAULT 0 | computed at check-out against `shift_end` |
| created_at, updated_at | timestamptz | |

There's no "absent" status stored anywhere — absence is implicit (no row for that employee/day), not synthesized by a background job. `check_in_at`/`check_out_at` are stored as UTC-aware timestamps but compared against the plain wall-clock `shift_start`/`shift_end` with no per-company timezone conversion — there's no timezone field anywhere in this app yet (the same gap Timesheets/Leave already have), so late/overtime detection is only accurate for companies operating in UTC until one is added.

### `saved_report` *(Phase 7)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| name | varchar(150) NOT NULL | `UNIQUE(company_id, name)` |
| module | varchar(20) NOT NULL | `employee` \| `department` \| `project` \| `timesheet` \| `leave` \| `asset` \| `attendance` |
| filters | jsonb NOT NULL DEFAULT '{}' | shape depends on `module` — validated against that module's Pydantic filter schema on every read/write, never trusted blindly |
| created_by | uuid FK → user_account.id NULL | |
| created_at, updated_at | timestamptz | |

A saved *filter set*, not a generic query — there's no `columns` field; every module reuses that module's own fixed export column set (`Employee`/`Department`/`Project`/`Timesheet`/`Leave`/`Asset` report rows are produced by the exact same `report_rows()` method each module's own CSV export already used since its own phase, not a second query engine). Saved reports are company-shared (visible to anyone with `report.view`), not private to their creator — same as Leave types or holidays.

### `notification` *(Phase 7b)*
| Column | Type | Notes |
|---|---|---|
| id | uuid PK | |
| company_id | uuid FK → company.id NOT NULL | |
| user_id | uuid FK → user_account.id NOT NULL, `ON DELETE CASCADE` | the recipient |
| type | varchar(50) NOT NULL | e.g. `leave.submitted`, `leave.approved`, `timesheet.rejected`, `asset.assigned`, `onboarding.submitted` |
| title | varchar(200) NOT NULL | |
| body | varchar(500) NULL | |
| entity_type, entity_id | varchar(50) / uuid, NULL | what the notification is about, for the frontend to link to — a loose reference, not a real FK (the target could be any module) |
| is_read | boolean NOT NULL DEFAULT false | |
| created_at, updated_at | timestamptz | |

Always created synchronously inside the same request/transaction as the action that triggered it (leave/timesheet submit+approve+reject, asset assign, onboarding submission), the same "no background indirection for in-process logic" pattern Celery is deliberately *not* used for here — see API_CONTRACTS.md. A live push over `/api/v1/notifications/ws` is best-effort on top of the persisted row (an in-process connection registry, no Redis pub/sub yet — see ROADMAP.md); the REST API is always the source of truth regardless of whether the push was delivered.

### `role`, `permission`, `role_permission`, `user_role`
Standard RBAC join tables as diagrammed above. `permission.module + permission.action` is `UNIQUE`. `role_permission(role_id, permission_id)` composite PK. `user_role(user_id, role_id)` composite PK.

### `audit_log`
Append-only; no `updated_at`/`deleted_at`. Indexed on `(company_id, entity_type, entity_id)` and `(company_id, created_at)`.

---

## Indexes

- `employee(company_id, status)` — directory filtering
- `employee(company_id, department_id)`
- `employee(company_id, manager_id)`
- `user_account(email)` unique
- `department(company_id, parent_department_id)`
- `audit_log(company_id, created_at DESC)`
- `employee_document(employee_id)`, `employee_document(company_id)` *(Phase 2)*
- `onboarding_invite(token_hash)` unique — the hot lookup path for every public onboarding request *(Phase 2)*
- `project(company_id, status)` — implicit via the `UNIQUE(company_id, name)` constraint plus status filtering in list queries *(Phase 3)*
- `timesheet_entry(employee_id)`, `timesheet_entry(project_id)`, `timesheet_entry(submission_id)`, `timesheet_entry(entry_date)` *(Phase 4)*
- `timesheet_submission(employee_id)` — the hot lookup path for "my submissions" and the manager approval queue *(Phase 4)*
- `leave_request(employee_id)`, `leave_request(leave_type_id)`, `leave_request(start_date)` *(Phase 5)*
- `leave_balance(employee_id, leave_type_id, year)` — implicit via the unique constraint, the hot lookup path for balance enforcement at request-creation time *(Phase 5)*
- `asset(asset_type_id)`, `asset_assignment(asset_id)`, `asset_assignment(employee_id)` *(Phase 6)*
- `saved_report(company_id, name)` — implicit via the unique constraint *(Phase 7)*
- `notification(user_id, is_read)` — the hot lookup path for the unread-count badge and the "unread only" feed filter *(Phase 7b)*

## Row-Level Security

```sql
ALTER TABLE employee ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON employee
  USING (company_id = current_setting('app.current_company_id', true)::uuid);
-- mirrored on department, role (where company_id is not null), audit_log,
-- (Phase 2) document_type, employee_document, onboarding_invite,
-- (Phase 3) client, project — NOT project_member, which is a pure join
-- table without its own company_id (see above) — and
-- (Phase 4) timesheet_period_config, timesheet_submission, timesheet_entry,
-- (Phase 5) leave_type, holiday_calendar, leave_balance, leave_request, and
-- (Phase 6) asset_type, asset, asset_assignment,
-- (Phase 7) saved_report, and
-- (Phase 7b) notification
```

Applied to every tenant-scoped table as defense-in-depth behind the repository-layer enforcement described in [LLD.md §4](./LLD.md#4-multi-tenant-enforcement--tenantscopedrepository). See [HLD.md §4](./HLD.md#4-multi-tenancy-strategy) for the caveat that this is currently inert in the local Docker Compose setup (superuser Postgres role) and needs a dedicated non-superuser app role to act as a real second layer in production.
