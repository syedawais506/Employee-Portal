export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown> | null;
  };
}

export interface CurrentUser {
  id: string;
  email: string;
  company_id: string | null;
  is_super_admin: boolean;
  is_verified: boolean;
  permissions: string[];
  employee_id: string | null;
  full_name: string | null;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  status: string;
}

export interface Department {
  id: string;
  name: string;
  parent_department_id: string | null;
  cost_center_code: string | null;
}

export interface PermissionGrant {
  module: string;
  action: string;
  granted: boolean;
}

export interface Role {
  id: string;
  name: string;
  is_system: boolean;
  permissions: PermissionGrant[];
}

export interface PermissionCatalogEntry {
  module: string;
  actions: string[];
}

export interface DepartmentRef {
  id: string;
  name: string;
}

export interface ManagerRef {
  id: string;
  first_name: string;
  last_name: string;
}

export interface EmployeeSummary {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  designation: string | null;
  department: DepartmentRef | null;
  status: string;
  employment_type: string;
  onboarding_status: string;
}

export interface EmployeeDetail {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  department: DepartmentRef | null;
  designation: string | null;
  manager: ManagerRef | null;
  employment_type: string;
  joining_date: string | null;
  status: string;
  onboarding_status: string;
}

export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";
export type EmployeeStatus = "active" | "on_leave" | "exited";
export type OnboardingStatus = "invited" | "submitted" | "hr_approved" | "completed";

export interface DocumentType {
  id: string;
  name: string;
  is_required: boolean;
  sort_order: number;
}

export interface EmployeeDocument {
  id: string;
  document_type_id: string;
  document_type_name: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: "pending" | "approved" | "rejected";
  review_notes: string | null;
  uploaded_at: string;
  reviewed_at: string | null;
}

export interface OnboardingContext {
  employee: {
    first_name: string;
    last_name: string;
    email: string;
    company_name: string;
    onboarding_status: OnboardingStatus;
  };
  document_types: DocumentType[];
  uploaded_documents: EmployeeDocument[];
  password_already_set: boolean;
  expires_at: string;
}

export interface OnboardingQueueEntry {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  onboarding_status: OnboardingStatus;
}

export interface Client {
  id: string;
  name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
}

export type ProjectStatus = "active" | "on_hold" | "completed" | "cancelled";
export type ProjectRole = "manager" | "member";

export interface ProjectMember {
  employee_id: string;
  first_name: string;
  last_name: string;
  role_on_project: ProjectRole;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: ProjectStatus;
  is_billable: boolean;
  start_date: string | null;
  end_date: string | null;
  member_count: number;
  client: Client | null;
}

export interface ProjectDetail {
  id: string;
  name: string;
  client: Client | null;
  budget: string | null;
  is_billable: boolean;
  start_date: string | null;
  end_date: string | null;
  status: ProjectStatus;
  members: ProjectMember[];
}

export interface MyProject {
  id: string;
  name: string;
  status: ProjectStatus;
  role_on_project: ProjectRole;
  start_date: string | null;
  end_date: string | null;
}

export type TimesheetPeriodType = "daily" | "weekly" | "monthly";
export type TimesheetWorkType = "office" | "remote" | "client_site";
export type TimesheetEntryStatus = "draft" | "submitted" | "manager_approved" | "approved" | "rejected";

export interface TimesheetPeriodConfig {
  id: string;
  period_type: TimesheetPeriodType;
  week_start_day: number;
  min_hours_per_day: string | null;
  max_hours_per_day: string | null;
  require_project_and_description: boolean;
  warn_on_weekend: boolean;
  require_finance_approval: boolean;
}

export interface TimesheetEntry {
  id: string;
  project_id: string;
  project_name: string;
  entry_date: string;
  hours: string;
  is_billable: boolean;
  work_type: TimesheetWorkType;
  description: string | null;
  status: TimesheetEntryStatus;
  is_weekend: boolean;
  submission_id: string | null;
}

export interface TimesheetSubmission {
  id: string;
  employee_id: string;
  employee_name: string;
  period_start: string;
  period_end: string;
  status: TimesheetEntryStatus;
  submitted_at: string;
  manager_approved_at: string | null;
  finance_approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  total_hours: string;
  entries: TimesheetEntry[];
}

export interface HoursByBucket {
  id: string;
  name: string;
  hours: string;
}

export interface TimesheetDashboard {
  pending_count: number;
  rejected_count: number;
  late_count: number;
  billable_percentage: number;
  hours_by_project: HoursByBucket[];
  hours_by_employee: HoursByBucket[];
}
