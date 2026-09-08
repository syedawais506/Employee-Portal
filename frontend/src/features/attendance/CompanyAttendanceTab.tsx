import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Button,
  Chip,
  Grid,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
} from "@mui/material";

import { downloadAttendanceExportCsv, listAttendance } from "@/api/attendance";
import { listEmployees } from "@/api/employees";
import { useAuthStore } from "@/store/authStore";
import type { AttendanceStatus } from "@/types";

const STATUS_COLOR: Record<AttendanceStatus, "success" | "info" | "default"> = {
  checked_in: "info",
  checked_out: "success",
  not_checked_in: "default",
};

function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function CompanyAttendanceTab() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canExport = hasPermission("attendance", "export");

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [exporting, setExporting] = useState(false);

  const filters = { dateFrom: dateFrom || undefined, dateTo: dateTo || undefined, employeeId: employeeId || undefined };

  const { data } = useQuery({
    queryKey: ["attendance", "list", page, pageSize, filters],
    queryFn: () => listAttendance(page + 1, pageSize, filters),
  });

  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });

  async function handleExport() {
    setExporting(true);
    try {
      await downloadAttendanceExportCsv(filters);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <TextField
            label="Date from"
            type="date"
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
          />
        </Grid>
        <Grid item xs={12} sm={3}>
          <TextField
            label="Date to"
            type="date"
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
          />
        </Grid>
        <Grid item xs={12} sm={3}>
          <TextField
            select
            label="Employee"
            fullWidth
            size="small"
            value={employeeId}
            onChange={(event) => setEmployeeId(event.target.value)}
          >
            <MenuItem value="">All employees</MenuItem>
            {(employees?.items ?? []).map((employee) => (
              <MenuItem key={employee.id} value={employee.id}>
                {employee.first_name} {employee.last_name}
              </MenuItem>
            ))}
          </TextField>
        </Grid>
        {canExport && (
          <Grid item xs={12} sm={3}>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              fullWidth
              onClick={handleExport}
              disabled={exporting}
            >
              Export CSV
            </Button>
          </Grid>
        )}
      </Grid>

      <Paper variant="outlined">
        <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Employee</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Check In</TableCell>
              <TableCell>Check Out</TableCell>
              <TableCell>Late</TableCell>
              <TableCell>Overtime</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((record) => (
              <TableRow key={record.id} hover>
                <TableCell>{record.employee_name}</TableCell>
                <TableCell>{record.attendance_date}</TableCell>
                <TableCell>{formatTime(record.check_in_at)}</TableCell>
                <TableCell>{formatTime(record.check_out_at)}</TableCell>
                <TableCell>{record.is_late ? "Yes" : "No"}</TableCell>
                <TableCell>{Number(record.overtime_hours) > 0 ? `${record.overtime_hours}h` : "—"}</TableCell>
                <TableCell>
                  <Chip label={record.status.replace("_", " ")} size="small" color={STATUS_COLOR[record.status]} />
                </TableCell>
              </TableRow>
            ))}
            {(data?.items ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No attendance records match these filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={data?.total ?? 0}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(event) => {
            setPageSize(Number(event.target.value));
            setPage(0);
          }}
        />
      </Paper>
    </>
  );
}
