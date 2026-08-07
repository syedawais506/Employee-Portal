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
}

export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";
export type EmployeeStatus = "active" | "on_leave" | "exited";
