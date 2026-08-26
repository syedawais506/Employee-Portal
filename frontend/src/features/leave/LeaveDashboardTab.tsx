import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import DownloadIcon from "@mui/icons-material/Download";
import { Button, Card, CardContent, Grid, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";

import { listEmployees } from "@/api/employees";
import { downloadLeaveExportCsv, getLeaveDashboard, listLeaveTypes } from "@/api/leave";

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
  leaveTypeId: string;
  status: string;
}

const EMPTY_FILTERS: ExportFilters = { dateFrom: "", dateTo: "", employeeId: "", leaveTypeId: "", status: "" };

export function LeaveDashboardTab() {
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState<ExportFilters>(EMPTY_FILTERS);
  const { data } = useQuery({ queryKey: ["dashboard", "leave"], queryFn: getLeaveDashboard });
  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });
  const { data: leaveTypes } = useQuery({ queryKey: ["leave", "types"], queryFn: listLeaveTypes });

  function updateFilter<K extends keyof ExportFilters>(key: K, value: ExportFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  async function handleExport() {
    setExporting(true);
    try {
      await downloadLeaveExportCsv({
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        employeeId: filters.employeeId || undefined,
        leaveTypeId: filters.leaveTypeId || undefined,
        status: filters.status || undefined,
      });
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6}>
          <KpiCard label="Pending Leave Requests" value={data?.pending_count ?? "—"} />
        </Grid>
        <Grid item xs={12} sm={6}>
          <KpiCard label="On Leave Today" value={data?.on_leave_today_count ?? "—"} />
        </Grid>
      </Grid>

      <Paper variant="outlined" sx={{ p: 2.5 }}>
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
              label="Leave type"
              fullWidth
              size="small"
              value={filters.leaveTypeId}
              onChange={(event) => updateFilter("leaveTypeId", event.target.value)}
            >
              <MenuItem value="">All types</MenuItem>
              {(leaveTypes ?? []).map((leaveType) => (
                <MenuItem key={leaveType.id} value={leaveType.id}>
                  {leaveType.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <TextField
              select
              label="Status"
              fullWidth
              size="small"
              value={filters.status}
              onChange={(event) => updateFilter("status", event.target.value)}
            >
              <MenuItem value="">All statuses</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="manager_approved">Awaiting HR</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="rejected">Rejected</MenuItem>
              <MenuItem value="cancelled">Cancelled</MenuItem>
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
    </>
  );
}
