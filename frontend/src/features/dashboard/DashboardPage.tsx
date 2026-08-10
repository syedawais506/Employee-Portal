import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Box, Card, CardContent, Chip, Grid, Stack, Typography } from "@mui/material";

import { listCompanies } from "@/api/companies";
import { listDepartments } from "@/api/departments";
import { listEmployees } from "@/api/employees";
import { listProjects } from "@/api/projects";
import { PageHeader } from "@/components/PageHeader";
import { useAuthStore } from "@/store/authStore";

function KpiCard({ label, value, helper }: { label: string; value: string | number; helper?: string }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.5 }}>
          {value}
        </Typography>
        {helper && (
          <Typography variant="caption" color="text.secondary">
            {helper}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

function ComingSoonCard({ title, phase }: { title: string; phase: string }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h3">{title}</Typography>
          <Chip label={phase} size="small" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          This widget will populate once the module ships — see docs/ROADMAP.md.
        </Typography>
      </CardContent>
    </Card>
  );
}

function SuperAdminDashboard() {
  const { data } = useQuery({
    queryKey: ["dashboard", "companies"],
    queryFn: () => listCompanies(1, 100),
  });

  return (
    <Stack spacing={3}>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <KpiCard label="Total Companies" value={data?.total ?? "—"} />
        </Grid>
        <Grid item xs={12} sm={4}>
          <KpiCard
            label="Active Companies"
            value={data?.items.filter((c) => c.status === "active").length ?? "—"}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <KpiCard label="Suspended Companies" value={data?.items.filter((c) => c.status !== "active").length ?? "—"} />
        </Grid>
      </Grid>
    </Stack>
  );
}

function TenantDashboard() {
  const hasPermission = useAuthStore((state) => state.hasPermission);

  const { data: totalEmployees } = useQuery({
    queryKey: ["dashboard", "employees", "total"],
    queryFn: () => listEmployees({ page: 1, page_size: 1 }),
    enabled: hasPermission("employee", "view"),
  });

  const { data: activeEmployees } = useQuery({
    queryKey: ["dashboard", "employees", "active"],
    queryFn: () => listEmployees({ page: 1, page_size: 1, status: "active" }),
    enabled: hasPermission("employee", "view"),
  });

  const { data: departments } = useQuery({
    queryKey: ["dashboard", "departments"],
    queryFn: () => listDepartments(1, 50),
    enabled: hasPermission("department", "view"),
  });

  const { data: allProjects } = useQuery({
    queryKey: ["dashboard", "projects"],
    queryFn: () => listProjects(1, 100),
    enabled: hasPermission("project", "view"),
  });

  const { data: departmentCounts } = useQuery({
    queryKey: ["dashboard", "department-counts", departments?.items.map((d) => d.id)],
    queryFn: async () => {
      const results = await Promise.all(
        (departments?.items ?? []).map(async (dept) => {
          const page = await listEmployees({ page: 1, page_size: 1, department_id: dept.id });
          return { name: dept.name, count: page.total };
        }),
      );
      return results;
    },
    enabled: Boolean(departments?.items.length),
  });

  const comingSoonCard = hasPermission("timesheet", "approve") || hasPermission("leave", "approve")
    ? { title: "Pending Approvals", phase: "Phase 4–5" }
    : hasPermission("employee", "import")
      ? { title: "Onboarding Queue", phase: "Phase 2" }
      : hasPermission("timesheet", "export")
        ? { title: "Billing & Utilization", phase: "Phase 7" }
        : { title: "My Timesheet & Leave", phase: "Phase 4–5" };

  return (
    <Stack spacing={3}>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <KpiCard label="Total Employees" value={totalEmployees?.total ?? "—"} />
        </Grid>
        <Grid item xs={12} sm={4}>
          <KpiCard
            label="Active Employees"
            value={activeEmployees?.total ?? "—"}
            helper={totalEmployees ? `${totalEmployees.total} total` : undefined}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <KpiCard label="Departments" value={departments?.total ?? "—"} />
        </Grid>
        {hasPermission("project", "view") && (
          <Grid item xs={12} sm={4}>
            <KpiCard
              label="Active Projects"
              value={allProjects?.items.filter((p) => p.status === "active").length ?? "—"}
              helper={allProjects ? `${allProjects.total} total` : undefined}
            />
          </Grid>
        )}
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h3" sx={{ mb: 2 }}>
                Headcount by Department
              </Typography>
              <Box sx={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={departmentCounts ?? []}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <ComingSoonCard title={comingSoonCard.title} phase={comingSoonCard.phase} />
        </Grid>
      </Grid>
    </Stack>
  );
}

export function DashboardPage() {
  const user = useAuthStore((state) => state.user);

  return (
    <Box>
      <PageHeader
        title={`Welcome back${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        subtitle="Here's what's happening across your organization."
      />
      {user?.is_super_admin ? <SuperAdminDashboard /> : <TenantDashboard />}
    </Box>
  );
}
