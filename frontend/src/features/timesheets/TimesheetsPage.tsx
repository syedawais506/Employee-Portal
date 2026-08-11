import { useState } from "react";
import { Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { ApprovalsTab } from "@/features/timesheets/ApprovalsTab";
import { MyTimesheetPage } from "@/features/timesheets/MyTimesheetPage";
import { TimesheetDashboardTab } from "@/features/timesheets/TimesheetDashboardTab";
import { TimesheetSettingsTab } from "@/features/timesheets/TimesheetSettingsTab";
import { useAuthStore } from "@/store/authStore";

type TabValue = "mine" | "approvals" | "dashboard" | "settings";

export function TimesheetsPage() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canApprove = hasPermission("timesheet", "approve");
  const canSeeDashboard = canApprove || hasPermission("timesheet", "export");
  const canConfigure = hasPermission("timesheet", "configure");

  const [tab, setTab] = useState<TabValue>("mine");

  return (
    <>
      <PageHeader title="Timesheets" subtitle="Log hours, track approvals, and review team utilization." />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab value="mine" label="My Timesheet" />
        {canApprove && <Tab value="approvals" label="Approvals" />}
        {canSeeDashboard && <Tab value="dashboard" label="Dashboard" />}
        {canConfigure && <Tab value="settings" label="Settings" />}
      </Tabs>
      {tab === "mine" && <MyTimesheetPage />}
      {tab === "approvals" && canApprove && <ApprovalsTab />}
      {tab === "dashboard" && canSeeDashboard && <TimesheetDashboardTab />}
      {tab === "settings" && canConfigure && <TimesheetSettingsTab />}
    </>
  );
}
