import { apiClient } from "@/api/client";
import type { Holiday, LeaveBalance, LeaveDashboard, LeaveRequest, LeaveSettings, LeaveType, Page } from "@/types";
import { triggerCsvDownload } from "@/utils/downloadCsv";

export interface LeaveTypeInput {
  name: string;
  is_paid: boolean;
  annual_quota_days: number | null;
  max_carry_forward_days: number;
  requires_attachment: boolean;
}

export type LeaveTypeUpdateInput = Partial<LeaveTypeInput>;

export async function listLeaveTypes(): Promise<LeaveType[]> {
  const response = await apiClient.get<LeaveType[]>("/leave-types");
  return response.data;
}

export async function createLeaveType(payload: LeaveTypeInput): Promise<LeaveType> {
  const response = await apiClient.post<LeaveType>("/leave-types", payload);
  return response.data;
}

export async function updateLeaveType(id: string, payload: LeaveTypeUpdateInput): Promise<LeaveType> {
  const response = await apiClient.patch<LeaveType>(`/leave-types/${id}`, payload);
  return response.data;
}

export async function deleteLeaveType(id: string): Promise<void> {
  await apiClient.delete(`/leave-types/${id}`);
}

export interface HolidayInput {
  date: string;
  name: string;
}

export async function listHolidays(year?: number): Promise<Holiday[]> {
  const response = await apiClient.get<Holiday[]>("/holidays", { params: { year } });
  return response.data;
}

export async function createHoliday(payload: HolidayInput): Promise<Holiday> {
  const response = await apiClient.post<Holiday>("/holidays", payload);
  return response.data;
}

export async function updateHoliday(id: string, payload: Partial<HolidayInput>): Promise<Holiday> {
  const response = await apiClient.patch<Holiday>(`/holidays/${id}`, payload);
  return response.data;
}

export async function deleteHoliday(id: string): Promise<void> {
  await apiClient.delete(`/holidays/${id}`);
}

export async function getLeaveSettings(): Promise<LeaveSettings> {
  const response = await apiClient.get<LeaveSettings>("/leave/settings");
  return response.data;
}

export async function updateLeaveSettings(payload: LeaveSettings): Promise<LeaveSettings> {
  const response = await apiClient.patch<LeaveSettings>("/leave/settings", payload);
  return response.data;
}

export async function listMyLeaveBalances(year?: number): Promise<LeaveBalance[]> {
  const response = await apiClient.get<LeaveBalance[]>("/leave/balances/mine", { params: { year } });
  return response.data;
}

export async function listCompanyLeaveBalances(year?: number, employeeId?: string): Promise<LeaveBalance[]> {
  const response = await apiClient.get<LeaveBalance[]>("/leave/balances", {
    params: { year, employee_id: employeeId },
  });
  return response.data;
}

export interface LeaveRequestInput {
  leave_type_id: string;
  start_date: string;
  end_date: string;
  reason?: string;
  employee_id?: string;
  file?: File | null;
}

export async function createLeaveRequest(payload: LeaveRequestInput): Promise<LeaveRequest> {
  const formData = new FormData();
  formData.append("leave_type_id", payload.leave_type_id);
  formData.append("start_date", payload.start_date);
  formData.append("end_date", payload.end_date);
  if (payload.reason) formData.append("reason", payload.reason);
  if (payload.employee_id) formData.append("employee_id", payload.employee_id);
  if (payload.file) formData.append("file", payload.file);
  const response = await apiClient.post<LeaveRequest>("/leave-requests", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export type LeaveBucket = "pending" | "approved" | "rejected";

export async function listMyLeaveRequests(status?: string): Promise<LeaveRequest[]> {
  const response = await apiClient.get<LeaveRequest[]>("/leave-requests/mine", { params: { status } });
  return response.data;
}

export interface LeaveRequestQueueFilters {
  employeeId?: string;
  leaveTypeId?: string;
  status?: string;
}

export async function listLeaveRequests(
  page: number,
  pageSize: number,
  filters: LeaveRequestQueueFilters = {},
): Promise<Page<LeaveRequest>> {
  const response = await apiClient.get<Page<LeaveRequest>>("/leave-requests", {
    params: {
      page,
      page_size: pageSize,
      employee_id: filters.employeeId,
      leave_type_id: filters.leaveTypeId,
      status: filters.status,
    },
  });
  return response.data;
}

export async function cancelLeaveRequest(id: string): Promise<LeaveRequest> {
  const response = await apiClient.post<LeaveRequest>(`/leave-requests/${id}/cancel`);
  return response.data;
}

export async function deleteLeaveRequest(id: string): Promise<void> {
  await apiClient.delete(`/leave-requests/${id}`);
}

export async function approveLeaveRequest(id: string): Promise<LeaveRequest> {
  const response = await apiClient.post<LeaveRequest>(`/leave-requests/${id}/approve`);
  return response.data;
}

export async function rejectLeaveRequest(id: string, reason: string): Promise<LeaveRequest> {
  const response = await apiClient.post<LeaveRequest>(`/leave-requests/${id}/reject`, { reason });
  return response.data;
}

export async function runLeaveCarryForward(fromYear: number, employeeId?: string): Promise<unknown> {
  const response = await apiClient.post("/leave/carry-forward", { from_year: fromYear, employee_id: employeeId });
  return response.data;
}

export async function getLeaveDashboard(): Promise<LeaveDashboard> {
  const response = await apiClient.get<LeaveDashboard>("/leave/dashboard");
  return response.data;
}

export interface LeaveExportFilters {
  dateFrom?: string;
  dateTo?: string;
  employeeId?: string;
  leaveTypeId?: string;
  status?: string;
}

export async function downloadLeaveExportCsv(filters: LeaveExportFilters = {}): Promise<void> {
  const response = await apiClient.get<Blob>("/leave/export", {
    params: {
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      employee_id: filters.employeeId,
      leave_type_id: filters.leaveTypeId,
      status: filters.status,
    },
    responseType: "blob",
  });
  triggerCsvDownload(response.data, "leave-export.csv");
}
