import { apiClient } from "@/api/client";
import type { ReportModule, ReportPreview, SavedReport } from "@/types";
import { triggerCsvDownload } from "@/utils/downloadCsv";

export async function previewReport(module: ReportModule, filters: Record<string, unknown>): Promise<ReportPreview> {
  const response = await apiClient.post<ReportPreview>("/reports/preview", { module, filters });
  return response.data;
}

export async function exportReportCsv(module: ReportModule, filters: Record<string, unknown>): Promise<void> {
  const response = await apiClient.post<Blob>(
    "/reports/export",
    { module, filters },
    { responseType: "blob" },
  );
  triggerCsvDownload(response.data, `${module}-report.csv`);
}

export async function listSavedReports(): Promise<SavedReport[]> {
  const response = await apiClient.get<SavedReport[]>("/reports/saved");
  return response.data;
}

export async function createSavedReport(payload: {
  name: string;
  module: ReportModule;
  filters: Record<string, unknown>;
}): Promise<SavedReport> {
  const response = await apiClient.post<SavedReport>("/reports/saved", payload);
  return response.data;
}

export async function updateSavedReport(
  id: string,
  payload: { name?: string; filters?: Record<string, unknown> },
): Promise<SavedReport> {
  const response = await apiClient.patch<SavedReport>(`/reports/saved/${id}`, payload);
  return response.data;
}

export async function deleteSavedReport(id: string): Promise<void> {
  await apiClient.delete(`/reports/saved/${id}`);
}

export async function runSavedReport(id: string): Promise<ReportPreview> {
  const response = await apiClient.post<ReportPreview>(`/reports/saved/${id}/run`);
  return response.data;
}

export async function exportSavedReportCsv(id: string, name: string): Promise<void> {
  const response = await apiClient.get<Blob>(`/reports/saved/${id}/export`, { responseType: "blob" });
  triggerCsvDownload(response.data, `${name}.csv`);
}
