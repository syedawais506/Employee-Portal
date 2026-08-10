import { useState } from "react";
import { Tab, Tabs } from "@mui/material";

import { PageHeader } from "@/components/PageHeader";
import { ClientsTab } from "@/features/projects/ClientsTab";
import { ProjectListPage } from "@/features/projects/ProjectListPage";

export function ProjectsPage() {
  const [tab, setTab] = useState<"projects" | "clients">("projects");

  return (
    <>
      <PageHeader title="Projects" subtitle="Track projects, budgets, and who's assigned to what." />
      <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{ mb: 3 }}>
        <Tab value="projects" label="Projects" />
        <Tab value="clients" label="Clients" />
      </Tabs>
      {tab === "projects" && <ProjectListPage />}
      {tab === "clients" && <ClientsTab />}
    </>
  );
}
