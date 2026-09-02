import { apiClient } from "@/api/client";
import type { CompanyTourStep } from "@/types";

export async function listTourSteps(): Promise<CompanyTourStep[]> {
  const response = await apiClient.get<CompanyTourStep[]>("/company-tour");
  return response.data;
}

export interface TourStepInput {
  title: string;
  body: string;
  sortOrder: number;
  image?: File | null;
}

export async function createTourStep(input: TourStepInput): Promise<CompanyTourStep> {
  const formData = new FormData();
  formData.append("title", input.title);
  formData.append("body", input.body);
  formData.append("sort_order", String(input.sortOrder));
  if (input.image) formData.append("image", input.image);
  const response = await apiClient.post<CompanyTourStep>("/company-tour", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export interface TourStepUpdateInput {
  title?: string;
  body?: string;
  sortOrder?: number;
}

export async function updateTourStep(id: string, input: TourStepUpdateInput): Promise<CompanyTourStep> {
  const response = await apiClient.patch<CompanyTourStep>(`/company-tour/${id}`, {
    title: input.title,
    body: input.body,
    sort_order: input.sortOrder,
  });
  return response.data;
}

export async function deleteTourStep(id: string): Promise<void> {
  await apiClient.delete(`/company-tour/${id}`);
}
