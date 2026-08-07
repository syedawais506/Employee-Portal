# Database Schema — Phase 1 & 2

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

> Further future-phase tables (`project`, `timesheet`, `leave_request`, `leave_balance`, `asset`, `notification`) are specified in [ROADMAP.md](./ROADMAP.md) with their own migrations when their phase begins, so this schema doesn't carry speculative, unused tables ahead of need. Foreign keys they will need (`employee.id`, `department.id`, `company.id`) already exist.

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
| joining_date | date NULL | |
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

## Row-Level Security

```sql
ALTER TABLE employee ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON employee
  USING (company_id = current_setting('app.current_company_id', true)::uuid);
-- mirrored on department, role (where company_id is not null), audit_log,
-- and (Phase 2) document_type, employee_document, onboarding_invite
```

Applied to every tenant-scoped table as defense-in-depth behind the repository-layer enforcement described in [LLD.md §4](./LLD.md#4-multi-tenant-enforcement--tenantscopedrepository). See [HLD.md §4](./HLD.md#4-multi-tenancy-strategy) for the caveat that this is currently inert in the local Docker Compose setup (superuser Postgres role) and needs a dedicated non-superuser app role to act as a real second layer in production.
