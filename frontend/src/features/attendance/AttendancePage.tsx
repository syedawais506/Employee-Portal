import { useState } from "react";
import { Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { AttendanceSettingsTab } from "@/features/attendance/AttendanceSettingsTab";
import { CompanyAttendanceTab } from "@/features/attendance/CompanyAttendanceTab";
import { MyAttendanceTab } from "@/features/attendance/MyAttendanceTab";
import { TodayTab } from "@/features/attendance/TodayTab";
import { useAuthStore } from "@/store/authStore";

type TabValue = "mine" | "today" | "company" | "settings";

export function AttendancePage() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canView = hasPermission("attendance", "view");
  const canConfigure = hasPermission("attendance", "configure");

  const [tab, setTab] = useState<TabValue>("mine");

  return (
    <>
      <PageHeader title="Attendance" subtitle="Check in and out, and track who's in today." />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab value="mine" label="My Attendance" />
        {canView && <Tab value="today" label="Today" />}
        {canView && <Tab value="company" label="Company Attendance" />}
        {canConfigure && <Tab value="settings" label="Settings" />}
      </Tabs>
      {tab === "mine" && <MyAttendanceTab />}
      {tab === "today" && canView && <TodayTab />}
      {tab === "company" && canView && <CompanyAttendanceTab />}
      {tab === "settings" && canConfigure && <AttendanceSettingsTab />}
    </>
  );
}
