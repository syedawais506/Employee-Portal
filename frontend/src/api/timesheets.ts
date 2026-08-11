import { apiClient } from "@/api/client";
import type {
  Page,
  TimesheetDashboard,
  TimesheetEntry,
  TimesheetPeriodConfig,
  TimesheetSubmission,
  TimesheetWorkType,
} from "@/types";

export interface TimesheetEntryInput {
  project_id: string;
  entry_date: string;
  hours: string;
  is_billable: boolean;
  work_type: TimesheetWorkType;
  description?: string | null;
}

export type TimesheetEntryUpdateInput = Partial<TimesheetEntryInput>;

export interface TimesheetConfigUpdateInput {
  period_type?: string;
  week_start_day?: number;
  min_hours_per_day?: string | null;
  max_hours_per_day?: string | null;
  require_project_and_description?: boolean;
  warn_on_weekend?: boolean;
  require_finance_approval?: boolean;
}

export async function getTimesheetConfig(): Promise<TimesheetPeriodConfig> {
  const response = await apiClient.get<TimesheetPeriodConfig>("/timesheets/config");
  return response.data;
}

export async function updateTimesheetConfig(payload: TimesheetConfigUpdateInput): Promise<TimesheetPeriodConfig> {
  const response = await apiClient.patch<TimesheetPeriodConfig>("/timesheets/config", payload);
  return response.data;
}

export async function listMyTimesheetEntries(dateFrom: string, dateTo: string): Promise<TimesheetEntry[]> {
  const response = await apiClient.get<TimesheetEntry[]>("/timesheets/entries", {
    params: { date_from: dateFrom, date_to: dateTo },
  });
  return response.data;
}

export async function createTimesheetEntry(payload: TimesheetEntryInput): Promise<TimesheetEntry> {
  const response = await apiClient.post<TimesheetEntry>("/timesheets/entries", payload);
  return response.data;
}

export async function updateTimesheetEntry(id: string, payload: TimesheetEntryUpdateInput): Promise<TimesheetEntry> {
  const response = await apiClient.patch<TimesheetEntry>(`/timesheets/entries/${id}`, payload);
  return response.data;
}

export async function deleteTimesheetEntry(id: string): Promise<void> {
  await apiClient.delete(`/timesheets/entries/${id}`);
}

export async function submitTimesheetPeriod(refDate: string): Promise<TimesheetSubmission> {
  const response = await apiClient.post<TimesheetSubmission>("/timesheets/submissions", { ref_date: refDate });
  return response.data;
}

export async function listMyTimesheetSubmissions(): Promise<TimesheetSubmission[]> {
  const response = await apiClient.get<TimesheetSubmission[]>("/timesheets/submissions/mine");
  return response.data;
}

export async function listTimesheetSubmissions(
  page: number,
  pageSize: number,
  status?: string,
): Promise<Page<TimesheetSubmission>> {
  const response = await apiClient.get<Page<TimesheetSubmission>>("/timesheets/submissions", {
    params: { page, page_size: pageSize, status },
  });
  return response.data;
}

export async function approveTimesheetSubmission(id: string): Promise<TimesheetSubmission> {
  const response = await apiClient.post<TimesheetSubmission>(`/timesheets/submissions/${id}/approve`);
  return response.data;
}

export async function rejectTimesheetSubmission(id: string, reason: string): Promise<TimesheetSubmission> {
  const response = await apiClient.post<TimesheetSubmission>(`/timesheets/submissions/${id}/reject`, { reason });
  return response.data;
}

export async function bulkApproveTimesheetSubmissions(
  submissionIds: string[],
): Promise<{ approved: string[]; failed: { id: string; reason: string }[] }> {
  const response = await apiClient.post("/timesheets/submissions/bulk-approve", { submission_ids: submissionIds });
  return response.data;
}

export async function reopenTimesheetSubmission(id: string): Promise<TimesheetSubmission> {
  const response = await apiClient.post<TimesheetSubmission>(`/timesheets/submissions/${id}/reopen`);
  return response.data;
}

export async function getTimesheetDashboard(dateFrom?: string, dateTo?: string): Promise<TimesheetDashboard> {
  const response = await apiClient.get<TimesheetDashboard>("/timesheets/dashboard", {
    params: { date_from: dateFrom, date_to: dateTo },
  });
  return response.data;
}

export async function downloadTimesheetExportCsv(dateFrom?: string, dateTo?: string): Promise<void> {
  const response = await apiClient.get<Blob>("/timesheets/export", {
    params: { date_from: dateFrom, date_to: dateTo },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "timesheet-export.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
