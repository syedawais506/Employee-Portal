import { apiClient } from "@/api/client";
import type { MyProject, Page, ProjectDetail, ProjectRole, ProjectSummary } from "@/types";
import { triggerCsvDownload } from "@/utils/downloadCsv";

export interface ProjectMemberInput {
  employee_id: string;
  role_on_project: ProjectRole;
}

export interface ProjectInput {
  name: string;
  client_id?: string | null;
  budget?: string | null;
  is_billable: boolean;
  start_date?: string | null;
  end_date?: string | null;
  member_ids?: ProjectMemberInput[];
}

export type ProjectUpdateInput = Partial<Omit<ProjectInput, "member_ids">> & { status?: string };

export async function listProjects(page: number, pageSize: number, status?: string): Promise<Page<ProjectSummary>> {
  const response = await apiClient.get<Page<ProjectSummary>>("/projects", {
    params: { page, page_size: pageSize, status },
  });
  return response.data;
}

export async function getProject(id: string): Promise<ProjectDetail> {
  const response = await apiClient.get<ProjectDetail>(`/projects/${id}`);
  return response.data;
}

export async function createProject(payload: ProjectInput): Promise<ProjectDetail> {
  const response = await apiClient.post<ProjectDetail>("/projects", payload);
  return response.data;
}

export async function updateProject(id: string, payload: ProjectUpdateInput): Promise<ProjectDetail> {
  const response = await apiClient.patch<ProjectDetail>(`/projects/${id}`, payload);
  return response.data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/projects/${id}`);
}

export async function addProjectMember(projectId: string, payload: ProjectMemberInput): Promise<ProjectDetail> {
  const response = await apiClient.post<ProjectDetail>(`/projects/${projectId}/members`, payload);
  return response.data;
}

export async function removeProjectMember(projectId: string, employeeId: string): Promise<ProjectDetail> {
  const response = await apiClient.delete<ProjectDetail>(`/projects/${projectId}/members/${employeeId}`);
  return response.data;
}

export async function listMyProjects(): Promise<MyProject[]> {
  const response = await apiClient.get<MyProject[]>("/projects/mine");
  return response.data;
}

export interface ProjectExportFilters {
  status?: string;
  clientId?: string;
  isBillable?: boolean;
  startDateFrom?: string;
  startDateTo?: string;
}

export async function downloadProjectsExportCsv(filters: ProjectExportFilters = {}): Promise<void> {
  const response = await apiClient.get<Blob>("/projects/export", {
    params: {
      status: filters.status,
      client_id: filters.clientId,
      is_billable: filters.isBillable,
      start_date_from: filters.startDateFrom,
      start_date_to: filters.startDateTo,
    },
    responseType: "blob",
  });
  triggerCsvDownload(response.data, "projects-export.csv");
}
