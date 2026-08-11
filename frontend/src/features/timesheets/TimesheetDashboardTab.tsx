import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Button,
  Card,
  CardContent,
  Grid,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { listEmployees } from "@/api/employees";
import { listProjects } from "@/api/projects";
import { downloadTimesheetExportCsv, getTimesheetDashboard } from "@/api/timesheets";
import { EMPLOYEE_LOCATIONS } from "@/types";

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.5 }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

interface ExportFilters {
  dateFrom: string;
  dateTo: string;
  employeeId: string;
  projectId: string;
  location: string;
}

const EMPTY_FILTERS: ExportFilters = { dateFrom: "", dateTo: "", employeeId: "", projectId: "", location: "" };

export function TimesheetDashboardTab() {
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState<ExportFilters>(EMPTY_FILTERS);
  const { data } = useQuery({ queryKey: ["timesheets", "dashboard"], queryFn: () => getTimesheetDashboard() });

  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 200 }),
  });
  const { data: projects } = useQuery({
    queryKey: ["projects", "all"],
    queryFn: () => listProjects(1, 200),
  });

  function updateFilter<K extends keyof ExportFilters>(key: K, value: ExportFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  async function handleExport() {
    setExporting(true);
    try {
      await downloadTimesheetExportCsv({
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        employeeId: filters.employeeId || undefined,
        projectId: filters.projectId || undefined,
        location: filters.location || undefined,
      });
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <Paper variant="outlined" sx={{ p: 2.5, mb: 3 }}>
        <Typography variant="h3" sx={{ mb: 2 }}>
          Export
        </Typography>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={6} sm={3} md={2}>
            <TextField
              type="date"
              label="From"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.dateFrom}
              onChange={(event) => updateFilter("dateFrom", event.target.value)}
            />
          </Grid>
          <Grid item xs={6} sm={3} md={2}>
            <TextField
              type="date"
              label="To"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.dateTo}
              onChange={(event) => updateFilter("dateTo", event.target.value)}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              label="Project"
              fullWidth
              size="small"
              value={filters.projectId}
              onChange={(event) => updateFilter("projectId", event.target.value)}
            >
              <MenuItem value="">All projects</MenuItem>
              {(projects?.items ?? []).map((project) => (
                <MenuItem key={project.id} value={project.id}>
                  {project.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              label="Employee"
              fullWidth
              size="small"
              value={filters.employeeId}
              onChange={(event) => updateFilter("employeeId", event.target.value)}
            >
              <MenuItem value="">All employees</MenuItem>
              {(employees?.items ?? []).map((employee) => (
                <MenuItem key={employee.id} value={employee.id}>
                  {employee.first_name} {employee.last_name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <TextField
              select
              label="Location"
              fullWidth
              size="small"
              value={filters.location}
              onChange={(event) => updateFilter("location", event.target.value)}
            >
              <MenuItem value="">All locations</MenuItem>
              {EMPLOYEE_LOCATIONS.map((location) => (
                <MenuItem key={location} value={location}>
                  {location}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>
        <Stack direction="row" spacing={1.5} sx={{ mt: 2 }}>
          <Button variant="contained" startIcon={<DownloadIcon />} onClick={handleExport} disabled={exporting}>
            Export CSV
          </Button>
          <Button onClick={() => setFilters(EMPTY_FILTERS)} disabled={exporting}>
            Clear filters
          </Button>
        </Stack>
      </Paper>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <KpiCard label="Pending Approvals" value={data?.pending_count ?? "—"} />
        </Grid>
        <Grid item xs={12} sm={3}>
          <KpiCard label="Rejected" value={data?.rejected_count ?? "—"} />
        </Grid>
        <Grid item xs={12} sm={3}>
          <KpiCard label="Late Submissions" value={data?.late_count ?? "—"} />
        </Grid>
        <Grid item xs={12} sm={3}>
          <KpiCard label="Billable %" value={data ? `${data.billable_percentage}%` : "—"} />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h3" sx={{ mb: 1.5 }}>
              Hours by Project
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Project</TableCell>
                  <TableCell align="right">Hours</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(data?.hours_by_project ?? []).map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.name}</TableCell>
                    <TableCell align="right">{row.hours}</TableCell>
                  </TableRow>
                ))}
                {(data?.hours_by_project ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} align="center" sx={{ color: "text.secondary" }}>
                      No hours logged yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h3" sx={{ mb: 1.5 }}>
              Hours by Employee
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Employee</TableCell>
                  <TableCell align="right">Hours</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(data?.hours_by_employee ?? []).map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.name}</TableCell>
                    <TableCell align="right">{row.hours}</TableCell>
                  </TableRow>
                ))}
                {(data?.hours_by_employee ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} align="center" sx={{ color: "text.secondary" }}>
                      No hours logged yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Paper>
        </Grid>
      </Grid>
    </>
  );
}
