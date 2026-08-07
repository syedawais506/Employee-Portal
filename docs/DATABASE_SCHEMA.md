# Database Schema — Phase 1

PostgreSQL 16. All tenant-owned tables carry `company_id`. UUID primary keys (`uuid_generate_v4()` / `gen_random_uuid()`). All tables have `created_at`, `updated_at`; soft-deletable tables also have `deleted_at`.

## ER Diagram (Phase 1 tables, solid) + Reserved Future Tables (dashed)

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

> Future-phase tables (`project`, `timesheet`, `leave_request`, `leave_balance`, `asset`, `employee_document`, `onboarding_task`, `notification`) are specified in [ROADMAP.md](./ROADMAP.md) with their own migrations when their phase begins, so Phase 1 does not carry speculative, unused tables. Foreign keys they will need (`employee.id`, `department.id`, `company.id`) already exist.

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
| created_at, updated_at | timestamptz | |
| deleted_at | timestamptz NULL | |

### `role`, `permission`, `role_permission`, `user_role`
Standard RBAC join tables as diagrammed above. `permission.module + permission.action` is `UNIQUE`. `role_permission(role_id, permission_id)` composite PK. `user_role(user_id, role_id)` composite PK.

### `audit_log`
Append-only; no `updated_at`/`deleted_at`. Indexed on `(company_id, entity_type, entity_id)` and `(company_id, created_at)`.

---

## Indexes (Phase 1)

- `employee(company_id, status)` — directory filtering
- `employee(company_id, department_id)`
- `employee(company_id, manager_id)`
- `user_account(email)` unique (citext)
- `department(company_id, parent_department_id)`
- `audit_log(company_id, created_at DESC)`

## Row-Level Security

```sql
ALTER TABLE employee ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON employee
  USING (company_id = current_setting('app.current_company_id', true)::uuid);
-- mirrored on department, role (where company_id is not null), audit_log
```

Applied to every tenant-scoped table as defense-in-depth behind the repository-layer enforcement described in [LLD.md §4](./LLD.md#4-multi-tenant-enforcement--tenantscopedrepository).
