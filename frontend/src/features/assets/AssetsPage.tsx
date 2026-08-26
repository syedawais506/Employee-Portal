import { useState } from "react";
import { Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { AllAssetsTab } from "@/features/assets/AllAssetsTab";
import { AssetTypesTab } from "@/features/assets/AssetTypesTab";
import { MyAssetsTab } from "@/features/assets/MyAssetsTab";
import { useAuthStore } from "@/store/authStore";

type TabValue = "mine" | "all" | "types";

export function AssetsPage() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canView = hasPermission("asset", "view");
  const [tab, setTab] = useState<TabValue>(canView ? "all" : "mine");

  return (
    <>
      <PageHeader title="Assets" subtitle="Track company equipment and who currently has it." />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab value="mine" label="My Assets" />
        {canView && <Tab value="all" label="All Assets" />}
        {canView && <Tab value="types" label="Asset Types" />}
      </Tabs>
      {tab === "mine" && <MyAssetsTab />}
      {tab === "all" && canView && <AllAssetsTab />}
      {tab === "types" && canView && <AssetTypesTab />}
    </>
  );
}
