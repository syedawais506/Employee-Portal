import { apiClient } from "@/api/client";
import type { EmployeeDocument, OnboardingContext, OnboardingQueueEntry } from "@/types";

export async function getOnboardingContext(token: string): Promise<OnboardingContext> {
  const response = await apiClient.get<OnboardingContext>(`/onboarding/${token}`);
  return response.data;
}

export async function setOnboardingPassword(token: string, password: string): Promise<void> {
  await apiClient.post(`/onboarding/${token}/password`, { password });
}

export async function uploadOnboardingDocument(
  token: string,
  documentTypeId: string,
  file: File,
): Promise<EmployeeDocument> {
  const formData = new FormData();
  formData.append("document_type_id", documentTypeId);
  formData.append("file", file);
  const response = await apiClient.post<EmployeeDocument>(`/onboarding/${token}/documents`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function getOnboardingQueue(): Promise<OnboardingQueueEntry[]> {
  const response = await apiClient.get<OnboardingQueueEntry[]>("/onboarding/queue");
  return response.data;
}

export async function listEmployeeDocuments(employeeId: string): Promise<EmployeeDocument[]> {
  const response = await apiClient.get<EmployeeDocument[]>(`/employees/${employeeId}/documents`);
  return response.data;
}

export async function reviewEmployeeDocument(
  employeeId: string,
  documentId: string,
  approve: boolean,
  notes?: string,
): Promise<EmployeeDocument> {
  const response = await apiClient.post<EmployeeDocument>(
    `/employees/${employeeId}/documents/${documentId}/review`,
    { approve, notes },
  );
  return response.data;
}

export async function getDocumentDownloadUrl(employeeId: string, documentId: string): Promise<string> {
  const response = await apiClient.get<{ url: string }>(`/employees/${employeeId}/documents/${documentId}/download`);
  return response.data.url;
}

export async function hrApproveOnboarding(employeeId: string): Promise<{ onboarding_status: string }> {
  const response = await apiClient.post(`/employees/${employeeId}/onboarding/hr-approve`);
  return response.data;
}

export async function adminApproveOnboarding(employeeId: string): Promise<{ onboarding_status: string }> {
  const response = await apiClient.post(`/employees/${employeeId}/onboarding/approve`);
  return response.data;
}
