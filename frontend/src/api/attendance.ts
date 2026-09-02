import { apiClient } from "@/api/client";
import type { AttendanceRecord, AttendanceShiftConfig, Page, TodayAttendanceEntry } from "@/types";
import { triggerCsvDownload } from "@/utils/downloadCsv";

export async function getAttendanceSettings(): Promise<AttendanceShiftConfig> {
  const response = await apiClient.get<AttendanceShiftConfig>("/attendance/settings");
  return response.data;
}

export interface AttendanceSettingsUpdateInput {
  shift_start?: string;
  shift_end?: string;
  grace_period_minutes?: number;
}

export async function updateAttendanceSettings(payload: AttendanceSettingsUpdateInput): Promise<AttendanceShiftConfig> {
  const response = await apiClient.patch<AttendanceShiftConfig>("/attendance/settings", payload);
  return response.data;
}

export async function checkIn(): Promise<AttendanceRecord> {
  const response = await apiClient.post<AttendanceRecord>("/attendance/check-in");
  return response.data;
}

export async function checkOut(): Promise<AttendanceRecord> {
  const response = await apiClient.post<AttendanceRecord>("/attendance/check-out");
  return response.data;
}

export async function listMyAttendance(dateFrom: string, dateTo: string): Promise<AttendanceRecord[]> {
  const response = await apiClient.get<AttendanceRecord[]>("/attendance/mine", {
    params: { date_from: dateFrom, date_to: dateTo },
  });
  return response.data;
}

export async function getTodayAttendance(): Promise<TodayAttendanceEntry[]> {
  const response = await apiClient.get<TodayAttendanceEntry[]>("/attendance/today");
  return response.data;
}

export interface AttendanceQueryFilters {
  dateFrom?: string;
  dateTo?: string;
  employeeId?: string;
}

export async function listAttendance(
  page: number,
  pageSize: number,
  filters: AttendanceQueryFilters = {},
): Promise<Page<AttendanceRecord>> {
  const response = await apiClient.get<Page<AttendanceRecord>>("/attendance", {
    params: {
      page,
      page_size: pageSize,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      employee_id: filters.employeeId,
    },
  });
  return response.data;
}

export async function downloadAttendanceExportCsv(filters: AttendanceQueryFilters = {}): Promise<void> {
  const response = await apiClient.get<Blob>("/attendance/export", {
    params: { date_from: filters.dateFrom, date_to: filters.dateTo, employee_id: filters.employeeId },
    responseType: "blob",
  });
  triggerCsvDownload(response.data, "attendance-export.csv");
}
