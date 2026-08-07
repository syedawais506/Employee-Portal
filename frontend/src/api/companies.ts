import { apiClient } from "@/api/client";
import type { Company, Page } from "@/types";

export interface CompanyInput {
  name: string;
  slug: string;
  admin_email: string;
  admin_first_name: string;
  admin_last_name: string;
}

export async function listCompanies(page: number, pageSize: number, search?: string): Promise<Page<Company>> {
  const response = await apiClient.get<Page<Company>>("/companies", {
    params: { page, page_size: pageSize, search },
  });
  return response.data;
}

export async function createCompany(payload: CompanyInput): Promise<Company> {
  const response = await apiClient.post<Company>("/companies", payload);
  return response.data;
}

export async function updateCompanyStatus(id: string, status: string): Promise<Company> {
  const response = await apiClient.patch<Company>(`/companies/${id}`, { status });
  return response.data;
}
