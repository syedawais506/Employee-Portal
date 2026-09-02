import { useQuery } from "@tanstack/react-query";
import { Chip, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import { getTodayAttendance } from "@/api/attendance";
import type { AttendanceStatus } from "@/types";

const STATUS_LABEL: Record<AttendanceStatus, string> = {
  checked_in: "Checked in",
  checked_out: "Checked out",
  not_checked_in: "Not checked in",
};

const STATUS_COLOR: Record<AttendanceStatus, "success" | "info" | "default"> = {
  checked_in: "info",
  checked_out: "success",
  not_checked_in: "default",
};

function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function TodayTab() {
  const { data: entries } = useQuery({ queryKey: ["attendance", "today"], queryFn: getTodayAttendance });

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Every active employee, whether or not they've checked in yet today.
      </Typography>
      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Employee</TableCell>
              <TableCell>Check In</TableCell>
              <TableCell>Check Out</TableCell>
              <TableCell>Late</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(entries ?? []).map((entry) => (
              <TableRow key={entry.employee_id} hover>
                <TableCell>{entry.employee_name}</TableCell>
                <TableCell>{formatTime(entry.check_in_at)}</TableCell>
                <TableCell>{formatTime(entry.check_out_at)}</TableCell>
                <TableCell>{entry.is_late ? "Yes" : "No"}</TableCell>
                <TableCell>
                  <Chip label={STATUS_LABEL[entry.status]} size="small" color={STATUS_COLOR[entry.status]} />
                </TableCell>
              </TableRow>
            ))}
            {(entries ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No active employees.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
}
