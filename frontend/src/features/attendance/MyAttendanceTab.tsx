import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { checkIn, checkOut, listMyAttendance } from "@/api/attendance";
import type { AttendanceStatus } from "@/types";

const STATUS_COLOR: Record<AttendanceStatus, "success" | "info" | "default"> = {
  checked_in: "info",
  checked_out: "success",
  not_checked_in: "default",
};

function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function MyAttendanceTab() {
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { dateFrom, dateTo, today } = useMemo(() => {
    const now = new Date();
    const from = new Date(now);
    from.setDate(from.getDate() - 13);
    return { dateFrom: toISODate(from), dateTo: toISODate(now), today: toISODate(now) };
  }, []);

  const { data: records } = useQuery({
    queryKey: ["attendance", "mine", dateFrom, dateTo],
    queryFn: () => listMyAttendance(dateFrom, dateTo),
  });

  const todayRecord = records?.find((record) => record.attendance_date === today) ?? null;

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["attendance", "mine"] });

  const checkInMutation = useMutation({
    mutationFn: checkIn,
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const checkOutMutation = useMutation({
    mutationFn: checkOut,
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  return (
    <>
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 3, mb: 4, maxWidth: 480 }}>
        <Typography variant="h3" sx={{ mb: 2 }}>
          Today
        </Typography>
        {!todayRecord && (
          <Stack spacing={2}>
            <Typography color="text.secondary">You haven't checked in yet today.</Typography>
            <Button variant="contained" onClick={() => checkInMutation.mutate()} disabled={checkInMutation.isPending}>
              Check In
            </Button>
          </Stack>
        )}
        {todayRecord && todayRecord.status === "checked_in" && (
          <Stack spacing={2}>
            <Box>
              <Typography color="text.secondary">Checked in at {formatTime(todayRecord.check_in_at)}</Typography>
              {todayRecord.is_late && <Chip label="Late" size="small" color="warning" sx={{ mt: 1 }} />}
            </Box>
            <Button
              variant="contained"
              color="secondary"
              onClick={() => checkOutMutation.mutate()}
              disabled={checkOutMutation.isPending}
            >
              Check Out
            </Button>
          </Stack>
        )}
        {todayRecord && todayRecord.status === "checked_out" && (
          <Stack spacing={1}>
            <Typography color="text.secondary">
              Checked in {formatTime(todayRecord.check_in_at)} · Checked out {formatTime(todayRecord.check_out_at)}
            </Typography>
            <Stack direction="row" spacing={1}>
              {todayRecord.is_late && <Chip label="Late" size="small" color="warning" />}
              {Number(todayRecord.overtime_hours) > 0 && (
                <Chip label={`${todayRecord.overtime_hours}h overtime`} size="small" color="info" />
              )}
            </Stack>
          </Stack>
        )}
      </Paper>

      <Typography variant="h3" sx={{ mb: 1.5 }}>
        Last 14 Days
      </Typography>
      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Check In</TableCell>
              <TableCell>Check Out</TableCell>
              <TableCell>Late</TableCell>
              <TableCell>Overtime</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(records ?? []).map((record) => (
              <TableRow key={record.id} hover>
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
            {(records ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No attendance history yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
}
