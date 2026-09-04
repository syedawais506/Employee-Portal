import { apiClient } from "@/api/client";
import type { EmployeeDetail, EmployeeSummary, Page } from "@/types";
import { triggerCsvDownload } from "@/utils/downloadCsv";

export interface EmployeeListFilters {
  search?: string;
  department_id?: string;
  status?: string;
  page: number;
  page_size: number;
}

export interface EmployeeInput {
  email: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  department_id?: string | null;
  designation?: string | null;
  manager_id?: string | null;
  employment_type: string;
  location?: string | null;
  joining_date?: string | null;
  role_ids?: string[];
}

export type EmployeeUpdateInput = Partial<Omit<EmployeeInput, "email" | "role_ids">> & { status?: string };

export async function listEmployees(filters: EmployeeListFilters): Promise<Page<EmployeeSummary>> {
  const response = await apiClient.get<Page<EmployeeSummary>>("/employees", { params: filters });
  return response.data;
}

export async function getEmployee(id: string): Promise<EmployeeDetail> {
  const response = await apiClient.get<EmployeeDetail>(`/employees/${id}`);
  return response.data;
}

export async function createEmployee(payload: EmployeeInput): Promise<EmployeeDetail> {
  const response = await apiClient.post<EmployeeDetail>("/employees", payload);
  return response.data;
}

export async function updateEmployee(id: string, payload: EmployeeUpdateInput): Promise<EmployeeDetail> {
  const response = await apiClient.patch<EmployeeDetail>(`/employees/${id}`, payload);
  return response.data;
}

export async function deleteEmployee(id: string): Promise<void> {
  await apiClient.delete(`/employees/${id}`);
}

export async function setEmployeeRoles(id: string, roleIds: string[]): Promise<EmployeeDetail> {
  const response = await apiClient.put<EmployeeDetail>(`/employees/${id}/roles`, { role_ids: roleIds });
  return response.data;
}

export async function getMyProfile(): Promise<EmployeeDetail> {
  const response = await apiClient.get<EmployeeDetail>("/employees/me");
  return response.data;
}

export interface EmployeeExportFilters {
  search?: string;
  departmentId?: string;
  status?: string;
  managerId?: string;
  employmentType?: string;
  location?: string;
  joiningDateFrom?: string;
  joiningDateTo?: string;
}

export async function downloadEmployeesExportCsv(filters: EmployeeExportFilters = {}): Promise<void> {
  const response = await apiClient.get<Blob>("/employees/export", {
    params: {
      search: filters.search,
      department_id: filters.departmentId,
      status: filters.status,
      manager_id: filters.managerId,
      employment_type: filters.employmentType,
      location: filters.location,
      joining_date_from: filters.joiningDateFrom,
      joining_date_to: filters.joiningDateTo,
    },
    responseType: "blob",
  });
  triggerCsvDownload(response.data, "employees-export.csv");
}
