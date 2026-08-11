import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Button,
  Card,
  CardContent,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { downloadTimesheetExportCsv, getTimesheetDashboard } from "@/api/timesheets";

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

export function TimesheetDashboardTab() {
  const [exporting, setExporting] = useState(false);
  const { data } = useQuery({ queryKey: ["timesheets", "dashboard"], queryFn: () => getTimesheetDashboard() });

  async function handleExport() {
    setExporting(true);
    try {
      await downloadTimesheetExportCsv();
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <Stack direction="row" justifyContent="flex-end" sx={{ mb: 2 }}>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleExport} disabled={exporting}>
          Export CSV
        </Button>
      </Stack>

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
