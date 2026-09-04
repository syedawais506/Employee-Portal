import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Box, Card, CardContent, Chip, Grid, Stack, Typography } from "@mui/material";

import { listCompanies } from "@/api/companies";
import { listDepartments } from "@/api/departments";
import { listEmployees } from "@/api/employees";
import { getLeaveDashboard, listMyLeaveRequests } from "@/api/leave";
import { listMyProjects, listProjects } from "@/api/projects";
import { getTimesheetDashboard, listMyTimesheetEntries } from "@/api/timesheets";
import { PageHeader } from "@/components/PageHeader";
import { useAuthStore } from "@/store/authStore";
import type { EmployeeSummary } from "@/types";
import { computePeriodBounds, toISODate } from "@/utils/timesheetPeriod";

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

interface ListCardItem {
  id: string;
  primary: string;
  secondary: string;
}

function ListCard({ title, emptyLabel, items }: { title: string; emptyLabel: string; items: ListCardItem[] }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="h3" sx={{ mb: 1.5 }}>
          {title}
        </Typography>
        {items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {emptyLabel}
          </Typography>
        ) : (
          <Stack spacing={1}>
            {items.map((item) => (
              <Stack key={item.id} direction="row" justifyContent="space-between" spacing={2}>
                <Typography variant="body2">{item.primary}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
                  {item.secondary}
                </Typography>
              </Stack>
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function daysSince(dateStr: string, today: Date): number {
  const date = new Date(`${dateStr}T00:00:00`);
  return Math.round((startOfDay(today).getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
}

// Compares only month/day, wrapping into next year when this year's date has already passed.
function daysUntilNextAnniversary(dateStr: string, today: Date): number {
  const anniversary = new Date(`${dateStr}T00:00:00`);
  const start = startOfDay(today);
  let next = new Date(start.getFullYear(), anniversary.getMonth(), anniversary.getDate());
  if (next.getTime() < start.getTime()) {
    next = new Date(start.getFullYear() + 1, anniversary.getMonth(), anniversary.getDate());
  }
  return Math.round((next.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
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
  const canViewProjects = hasPermission("project", "view");

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

  // Widget-only fetch (new hires / birthdays), capped like every other list
  // query in this app — companies past 100 active employees only see the
  // first page's worth reflected here.
  const { data: employeesForWidgets } = useQuery({
    queryKey: ["dashboard", "employees", "widgets"],
    queryFn: () => listEmployees({ page: 1, page_size: 100, status: "active" }),
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
    enabled: canViewProjects,
  });

  const { data: myProjects } = useQuery({
    queryKey: ["dashboard", "my-projects"],
    queryFn: () => listMyProjects(),
    enabled: !canViewProjects,
  });

  const canApproveTimesheets = hasPermission("timesheet", "approve");
  const canViewTimesheetDashboard = canApproveTimesheets || hasPermission("timesheet", "export");
  const canLogTimesheets = hasPermission("timesheet", "view") && !canViewTimesheetDashboard;

  const { data: timesheetDashboard } = useQuery({
    queryKey: ["dashboard", "timesheet"],
    queryFn: () => getTimesheetDashboard(),
    enabled: canViewTimesheetDashboard,
  });

  const [weekStart, weekEnd] = computePeriodBounds("weekly", 0, new Date());
  const { data: myWeekEntries } = useQuery({
    queryKey: ["dashboard", "my-timesheet-week"],
    queryFn: () => listMyTimesheetEntries(toISODate(weekStart), toISODate(weekEnd)),
    enabled: canLogTimesheets,
  });
  const myWeekHours = (myWeekEntries ?? []).reduce((sum, e) => sum + Number(e.hours), 0);

  const canApproveLeave = hasPermission("leave", "approve");
  const canRequestLeave = hasPermission("leave", "view") && !canApproveLeave;

  const { data: leaveDashboard } = useQuery({
    queryKey: ["dashboard", "leave"],
    queryFn: () => getLeaveDashboard(),
    enabled: canApproveLeave,
  });

  const { data: myPendingLeave } = useQuery({
    queryKey: ["dashboard", "my-leave-pending"],
    queryFn: () => listMyLeaveRequests("pending"),
    enabled: canRequestLeave,
  });

  const comingSoonCard = hasPermission("employee", "import") ? { title: "Onboarding Queue", phase: "Phase 2" } : null;

  // Admin-only insight, same signal already used to gate the Integrations page.
  const canViewHeadcountByProject = hasPermission("company", "configure");
  const projectHeadcounts = (allProjects?.items ?? []).map((project) => ({
    name: project.name,
    count: project.member_count,
  }));

  const myProjectItems: ListCardItem[] = (myProjects ?? []).map((project) => ({
    id: project.id,
    primary: project.name,
    secondary: project.role_on_project === "manager" ? "Manager" : "Member",
  }));

  const today = new Date();
  const newHireItems: ListCardItem[] = (employeesForWidgets?.items ?? [])
    .map((employee): { employee: EmployeeSummary; days: number | null } => ({
      employee,
      days: employee.joining_date ? daysSince(employee.joining_date, today) : null,
    }))
    .filter((entry): entry is { employee: EmployeeSummary; days: number } => entry.days !== null && entry.days >= 0 && entry.days <= 7)
    .sort((a, b) => a.days - b.days)
    .map(({ employee, days }) => ({
      id: employee.id,
      primary: `${employee.first_name} ${employee.last_name}`,
      secondary: days === 0 ? "Joined today" : `Joined ${days} day${days === 1 ? "" : "s"} ago`,
    }));

  const birthdayItems: ListCardItem[] = (employeesForWidgets?.items ?? [])
    .map((employee): { employee: EmployeeSummary; days: number | null } => ({
      employee,
      days: employee.birth_date ? daysUntilNextAnniversary(employee.birth_date, today) : null,
    }))
    .filter((entry): entry is { employee: EmployeeSummary; days: number } => entry.days !== null && entry.days <= 7)
    .sort((a, b) => a.days - b.days)
    .map(({ employee, days }) => ({
      id: employee.id,
      primary: `${employee.first_name} ${employee.last_name}`,
      secondary: days === 0 ? "Today!" : `In ${days} day${days === 1 ? "" : "s"}`,
    }));

  const showChartRow = canViewHeadcountByProject || Boolean(comingSoonCard);

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
        {canViewProjects && (
          <Grid item xs={12} sm={4}>
            <KpiCard
              label="Active Projects"
              value={allProjects?.items.filter((p) => p.status === "active").length ?? "—"}
              helper={allProjects ? `${allProjects.total} total` : undefined}
            />
          </Grid>
        )}
        {canViewTimesheetDashboard && (
          <Grid item xs={12} sm={4}>
            <KpiCard
              label="Pending Timesheet Approvals"
              value={timesheetDashboard?.pending_count ?? "—"}
              helper={
                timesheetDashboard
                  ? `${timesheetDashboard.rejected_count} rejected, ${timesheetDashboard.late_count} late`
                  : undefined
              }
            />
          </Grid>
        )}
        {canLogTimesheets && (
          <Grid item xs={12} sm={4}>
            <KpiCard label="My Hours This Week" value={myWeekHours.toFixed(2)} helper="Log time in Timesheets" />
          </Grid>
        )}
        {canApproveLeave && (
          <Grid item xs={12} sm={4}>
            <KpiCard
              label="Pending Leave Requests"
              value={leaveDashboard?.pending_count ?? "—"}
              helper={leaveDashboard ? `${leaveDashboard.on_leave_today_count} on leave today` : undefined}
            />
          </Grid>
        )}
        {canRequestLeave && (
          <Grid item xs={12} sm={4}>
            <KpiCard
              label="My Pending Leave Requests"
              value={myPendingLeave?.length ?? "—"}
              helper="Request time off in Leave"
            />
          </Grid>
        )}
      </Grid>

      {showChartRow && (
        <Grid container spacing={2}>
          {canViewHeadcountByProject && (
            <Grid item xs={12} md={comingSoonCard ? 8 : 12}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h3" sx={{ mb: 2 }}>
                    Headcount by Project
                  </Typography>
                  <Box sx={{ width: "100%", height: 280 }}>
                    <ResponsiveContainer>
                      <BarChart data={projectHeadcounts}>
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
          )}
          {comingSoonCard && (
            <Grid item xs={12} md={canViewHeadcountByProject ? 4 : 12}>
              <ComingSoonCard title={comingSoonCard.title} phase={comingSoonCard.phase} />
            </Grid>
          )}
        </Grid>
      )}

      <Grid container spacing={2}>
        {!canViewProjects && (
          <Grid item xs={12} md={4}>
            <ListCard title="My Projects" emptyLabel="You're not assigned to any projects yet." items={myProjectItems} />
          </Grid>
        )}
        {hasPermission("employee", "view") && (
          <>
            <Grid item xs={12} md={4}>
              <ListCard
                title="New Hires (Last 7 Days)"
                emptyLabel="No new hires in the last 7 days."
                items={newHireItems}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <ListCard
                title="Birthdays This Week"
                emptyLabel="No birthdays coming up this week."
                items={birthdayItems}
              />
            </Grid>
          </>
        )}
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
