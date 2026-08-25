import { useState } from "react";
import { Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { ApprovalsTab } from "@/features/leave/ApprovalsTab";
import { BalancesTab } from "@/features/leave/BalancesTab";
import { LeaveDashboardTab } from "@/features/leave/LeaveDashboardTab";
import { LeaveSettingsTab } from "@/features/leave/LeaveSettingsTab";
import { MyLeaveTab } from "@/features/leave/MyLeaveTab";
import { useAuthStore } from "@/store/authStore";

type TabValue = "mine" | "balances" | "approvals" | "dashboard" | "settings";

export function LeavePage() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canApprove = hasPermission("leave", "approve");
  const canConfigure = hasPermission("leave", "configure");

  const [tab, setTab] = useState<TabValue>("mine");

  return (
    <>
      <PageHeader title="Leave" subtitle="Request time off, track balances, and review approvals." />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab value="mine" label="My Leave" />
        <Tab value="balances" label="Balances" />
        {canApprove && <Tab value="approvals" label="Approvals" />}
        {canApprove && <Tab value="dashboard" label="Dashboard" />}
        {canConfigure && <Tab value="settings" label="Settings" />}
      </Tabs>
      {tab === "mine" && <MyLeaveTab />}
      {tab === "balances" && <BalancesTab />}
      {tab === "approvals" && canApprove && <ApprovalsTab />}
      {tab === "dashboard" && canApprove && <LeaveDashboardTab />}
      {tab === "settings" && canConfigure && <LeaveSettingsTab />}
    </>
  );
}
