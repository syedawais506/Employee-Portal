import { useState } from "react";
import { Alert, Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { AttendanceSettingsTab } from "@/features/attendance/AttendanceSettingsTab";
import { CompanyAttendanceTab } from "@/features/attendance/CompanyAttendanceTab";
import { MyAttendanceTab } from "@/features/attendance/MyAttendanceTab";
import { TodayTab } from "@/features/attendance/TodayTab";
import { useAuthStore } from "@/store/authStore";

type TabValue = "mine" | "today" | "company" | "settings";

export function AttendancePage() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const attendanceEnabled = useAuthStore((state) => state.user?.attendance_enabled ?? true);
  const canView = hasPermission("attendance", "view");
  const canConfigure = hasPermission("attendance", "configure");

  const [tab, setTab] = useState<TabValue>("mine");

  return (
    <>
      <PageHeader title="Attendance" subtitle="Check in and out, and track who's in today." />
      {!attendanceEnabled && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Attendance tracking is currently disabled for your company.
          {canConfigure ? " Turn it back on from the Settings tab below." : " Contact your Admin if you need it."}
        </Alert>
      )}
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        {attendanceEnabled && <Tab value="mine" label="My Attendance" />}
        {attendanceEnabled && canView && <Tab value="today" label="Today" />}
        {attendanceEnabled && canView && <Tab value="company" label="Company Attendance" />}
        {canConfigure && <Tab value="settings" label="Settings" />}
      </Tabs>
      {attendanceEnabled && tab === "mine" && <MyAttendanceTab />}
      {attendanceEnabled && tab === "today" && canView && <TodayTab />}
      {attendanceEnabled && tab === "company" && canView && <CompanyAttendanceTab />}
      {(tab === "settings" || !attendanceEnabled) && canConfigure && <AttendanceSettingsTab />}
    </>
  );
}
