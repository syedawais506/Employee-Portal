import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import {
  Alert,
  Button,
  Chip,
  IconButton,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getEmployee, listEmployees } from "@/api/employees";
import {
  cancelLeaveRequest,
  createLeaveRequest,
  listHolidays,
  listLeaveTypes,
  listMyLeaveRequests,
  type LeaveRequestInput,
} from "@/api/leave";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { LeaveCalendar } from "@/features/leave/LeaveCalendar";
import { LeaveRequestFormDialog } from "@/features/leave/LeaveRequestFormDialog";
import { useAuthStore } from "@/store/authStore";
import type { LeaveRequest } from "@/types";
import { formatPeriodLabel, getMonthGridDates, shiftPeriod, toISODate } from "@/utils/timesheetPeriod";

const WEEK_START_DAY = 0; // Monday, matching the backend's business-day calculation

type Bucket = "pending" | "approved" | "rejected";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  pending: "warning",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
  cancelled: "default",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Awaiting manager approval",
  manager_approved: "Awaiting HR sign-off",
  approved: "Approved",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

function inBucket(request: LeaveRequest, bucket: Bucket): boolean {
  if (bucket === "pending") return request.status === "pending" || request.status === "manager_approved";
  if (bucket === "approved") return request.status === "approved";
  return request.status === "rejected" || request.status === "cancelled";
}

export function MyLeaveTab() {
  const queryClient = useQueryClient();
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canActForOthers = hasPermission("leave", "approve");
  const myEmployeeId = useAuthStore((state) => state.user?.employee_id ?? null);

  const [refDate, setRefDate] = useState(new Date());
  const [bucket, setBucket] = useState<Bucket>("pending");
  const [formState, setFormState] = useState<{ open: boolean; date: string }>({
    open: false,
    date: toISODate(new Date()),
  });
  const [pendingCancel, setPendingCancel] = useState<LeaveRequest | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: leaveTypes } = useQuery({ queryKey: ["leave", "types"], queryFn: listLeaveTypes });
  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
    enabled: canActForOthers,
  });
  const { data: myRequests } = useQuery({ queryKey: ["leave", "requests", "mine"], queryFn: () => listMyLeaveRequests() });
  const { data: holidays } = useQuery({
    queryKey: ["leave", "holidays", refDate.getFullYear()],
    queryFn: () => listHolidays(refDate.getFullYear()),
  });
  const { data: myEmployee } = useQuery({
    queryKey: ["employees", myEmployeeId],
    queryFn: () => getEmployee(myEmployeeId as string),
    enabled: Boolean(myEmployeeId),
  });

  const gridDates = useMemo(() => getMonthGridDates(refDate, WEEK_START_DAY), [refDate]);

  const requestsByDate = useMemo(() => {
    const map: Record<string, LeaveRequest[]> = {};
    for (const request of myRequests ?? []) {
      if (request.status === "rejected" || request.status === "cancelled") continue;
      let cursor = new Date(request.start_date);
      const end = new Date(request.end_date);
      while (cursor <= end) {
        const iso = toISODate(cursor);
        (map[iso] ??= []).push(request);
        cursor = new Date(cursor);
        cursor.setDate(cursor.getDate() + 1);
      }
    }
    return map;
  }, [myRequests]);

  const holidaysByDate = useMemo(() => {
    const map: Record<string, string> = {};
    for (const holiday of holidays ?? []) {
      if (holiday.location !== null && holiday.location !== myEmployee?.location) continue;
      map[holiday.date] = holiday.name;
    }
    return map;
  }, [holidays, myEmployee]);

  const bucketedRequests = (myRequests ?? []).filter((r) => inBucket(r, bucket));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["leave", "requests"] });
    queryClient.invalidateQueries({ queryKey: ["leave", "balances"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "leave"] });
  };

  const createMutation = useMutation({
    mutationFn: (payload: LeaveRequestInput) => createLeaveRequest(payload),
    onSuccess: () => {
      invalidate();
      setFormState((s) => ({ ...s, open: false }));
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelLeaveRequest,
    onSuccess: () => {
      invalidate();
      setPendingCancel(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  function openCreate(dateIso: string) {
    setErrorMessage(null);
    setFormState({ open: true, date: dateIso });
  }

  return (
    <>
      <PageHeader title="My Leave" subtitle="Click a date to request time off, or review what you've already requested." />

      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }} flexWrap="wrap" gap={1}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <IconButton onClick={() => setRefDate(shiftPeriod("monthly", refDate, -1))} size="small">
            <ChevronLeftIcon />
          </IconButton>
          <Typography variant="h3">
            {formatPeriodLabel(gridDates[0], gridDates[gridDates.length - 1]).split(" – ")[0]}
          </Typography>
          <IconButton onClick={() => setRefDate(shiftPeriod("monthly", refDate, 1))} size="small">
            <ChevronRightIcon />
          </IconButton>
        </Stack>
        <Button variant="outlined" startIcon={<AddIcon />} onClick={() => openCreate(toISODate(new Date()))}>
          Request Leave
        </Button>
      </Stack>

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <LeaveCalendar
        days={gridDates}
        currentMonth={refDate.getMonth()}
        weekStartDay={WEEK_START_DAY}
        requestsByDate={requestsByDate}
        holidaysByDate={holidaysByDate}
        onDayClick={openCreate}
        onRequestClick={() => setBucket("pending")}
      />

      <Typography variant="h3" sx={{ mt: 4, mb: 1.5 }}>
        My Requests
      </Typography>
      <Tabs value={bucket} onChange={(_, value) => setBucket(value)} sx={{ mb: 2 }}>
        <Tab value="pending" label="Pending" />
        <Tab value="approved" label="Approved" />
        <Tab value="rejected" label="Rejected" />
      </Tabs>

      <Paper variant="outlined">
        <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Leave type</TableCell>
              <TableCell>Dates</TableCell>
              <TableCell>Days</TableCell>
              <TableCell>Status</TableCell>
              {bucket === "rejected" && <TableCell>Reason</TableCell>}
              {bucket === "pending" && <TableCell align="right">Actions</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {bucketedRequests.map((request) => (
              <TableRow key={request.id} hover>
                <TableCell>{request.leave_type_name}</TableCell>
                <TableCell>
                  {request.start_date} – {request.end_date}
                </TableCell>
                <TableCell>{request.days_count}</TableCell>
                <TableCell>
                  <Chip
                    label={STATUS_LABEL[request.status] ?? request.status}
                    size="small"
                    color={STATUS_COLOR[request.status]}
                  />
                </TableCell>
                {bucket === "rejected" && <TableCell>{request.rejection_reason ?? "—"}</TableCell>}
                {bucket === "pending" && (
                  <TableCell align="right">
                    <Button size="small" color="error" onClick={() => setPendingCancel(request)}>
                      Cancel
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
            {bucketedRequests.length === 0 && (
              <TableRow>
                <TableCell colSpan={bucket === "rejected" || bucket === "pending" ? 5 : 4} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">Nothing here yet.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        </TableContainer>
      </Paper>

      <LeaveRequestFormDialog
        open={formState.open}
        leaveTypes={leaveTypes ?? []}
        employees={employees?.items ?? []}
        canActForOthers={canActForOthers}
        defaultDate={formState.date}
        errorMessage={errorMessage}
        submitting={createMutation.isPending}
        onClose={() => setFormState((s) => ({ ...s, open: false }))}
        onSubmit={(values) => createMutation.mutate(values)}
      />

      <ConfirmDialog
        open={Boolean(pendingCancel)}
        title="Cancel leave request"
        description={`Cancel your ${pendingCancel?.leave_type_name ?? ""} request for ${pendingCancel?.start_date ?? ""} – ${pendingCancel?.end_date ?? ""}?`}
        confirmLabel="Cancel Request"
        destructive
        loading={cancelMutation.isPending}
        onClose={() => setPendingCancel(null)}
        onConfirm={() => pendingCancel && cancelMutation.mutate(pendingCancel.id)}
      />
    </>
  );
}
