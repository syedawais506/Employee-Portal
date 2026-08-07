import { apiClient } from "@/api/client";
import type { Department, Page } from "@/types";

export interface DepartmentInput {
  name: string;
  parent_department_id?: string | null;
  cost_center_code?: string | null;
}

export async function listDepartments(page: number, pageSize: number): Promise<Page<Department>> {
  const response = await apiClient.get<Page<Department>>("/departments", {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function createDepartment(payload: DepartmentInput): Promise<Department> {
  const response = await apiClient.post<Department>("/departments", payload);
  return response.data;
}

export async function updateDepartment(id: string, payload: Partial<DepartmentInput>): Promise<Department> {
  const response = await apiClient.patch<Department>(`/departments/${id}`, payload);
  return response.data;
}

export async function deleteDepartment(id: string): Promise<void> {
  await apiClient.delete(`/departments/${id}`);
}
