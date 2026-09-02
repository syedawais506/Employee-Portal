import { useState } from "react";
import { Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import { BrandingAndTourSettingsPage } from "@/features/onboarding/BrandingAndTourSettingsPage";
import { DocumentTypeSettingsPage } from "@/features/onboarding/DocumentTypeSettingsPage";
import { OnboardingQueuePage } from "@/features/onboarding/OnboardingQueuePage";
import { useAuthStore } from "@/store/authStore";

export function OnboardingPage() {
  const canConfigure = useAuthStore((state) => state.hasPermission("onboarding", "configure"));
  const [tab, setTab] = useState<"queue" | "settings" | "branding">("queue");

  return (
    <>
      <PageHeader title="Onboarding" subtitle="Review new hires and configure the document checklist." />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab value="queue" label="Review Queue" />
        {canConfigure && <Tab value="settings" label="Document Checklist" />}
        {canConfigure && <Tab value="branding" label="Branding & Tour" />}
      </Tabs>
      {tab === "queue" && <OnboardingQueuePage />}
      {tab === "settings" && (
        <PermissionGate module="onboarding" action="configure">
          <DocumentTypeSettingsPage />
        </PermissionGate>
      )}
      {tab === "branding" && (
        <PermissionGate module="onboarding" action="configure">
          <BrandingAndTourSettingsPage />
        </PermissionGate>
      )}
    </>
  );
}
