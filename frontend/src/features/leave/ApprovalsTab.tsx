import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Chip,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Tabs,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { approveLeaveRequest, listLeaveRequests, rejectLeaveRequest, type LeaveBucket } from "@/api/leave";
import { RejectLeaveRequestDialog } from "@/features/leave/RejectLeaveRequestDialog";
import type { LeaveRequest } from "@/types";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  pending: "warning",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
  cancelled: "default",
};

// "Pending" spans two statuses (awaiting the Manager step, or awaiting the
// optional HR sign-off step) — leave.approve covers both steps, so a single
// merged, unpaginated fetch keeps this simple rather than juggling two
// paginated queries for what's normally a small queue.
export function ApprovalsTab() {
  const queryClient = useQueryClient();
  const [bucket, setBucket] = useState<LeaveBucket>("pending");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [rejecting, setRejecting] = useState<LeaveRequest | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: pendingStage } = useQuery({
    queryKey: ["leave", "requests", "queue", "pending"],
    queryFn: () => listLeaveRequests(1, 100, { status: "pending" }),
    enabled: bucket === "pending",
  });
  const { data: managerApprovedStage } = useQuery({
    queryKey: ["leave", "requests", "queue", "manager_approved"],
    queryFn: () => listLeaveRequests(1, 100, { status: "manager_approved" }),
    enabled: bucket === "pending",
  });
  const { data: paginated, isLoading } = useQuery({
    queryKey: ["leave", "requests", "queue", bucket, page, pageSize],
    queryFn: () => listLeaveRequests(page + 1, pageSize, { status: bucket }),
    enabled: bucket !== "pending",
  });

  const items = bucket === "pending" ? [...(pendingStage?.items ?? []), ...(managerApprovedStage?.items ?? [])] : paginated?.items ?? [];
  const total = bucket === "pending" ? items.length : paginated?.total ?? 0;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["leave", "requests"] });
    queryClient.invalidateQueries({ queryKey: ["leave", "balances"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "leave"] });
  };

  const approveMutation = useMutation({
    mutationFn: approveLeaveRequest,
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => rejectLeaveRequest(id, reason),
    onSuccess: () => {
      invalidate();
      setRejecting(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  return (
    <>
      <Tabs
        value={bucket}
        onChange={(_, value) => {
          setBucket(value);
          setPage(0);
        }}
        sx={{ mb: 2 }}
      >
        <Tab value="pending" label="Pending" />
        <Tab value="approved" label="Approved" />
        <Tab value="rejected" label="Rejected" />
      </Tabs>

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Employee</TableCell>
              <TableCell>Leave type</TableCell>
              <TableCell>Dates</TableCell>
              <TableCell>Days</TableCell>
              <TableCell>Status</TableCell>
              {bucket === "rejected" && <TableCell>Reason</TableCell>}
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((request) => (
              <TableRow key={request.id} hover>
                <TableCell>{request.employee_name}</TableCell>
                <TableCell>{request.leave_type_name}</TableCell>
                <TableCell>
                  {request.start_date} – {request.end_date}
                </TableCell>
                <TableCell>{request.days_count}</TableCell>
                <TableCell>
                  <Chip label={request.status.replace("_", " ")} size="small" color={STATUS_COLOR[request.status]} />
                </TableCell>
                {bucket === "rejected" && <TableCell>{request.rejection_reason ?? "—"}</TableCell>}
                <TableCell align="right">
                  {bucket === "pending" && (
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" onClick={() => approveMutation.mutate(request.id)}>
                        Approve
                      </Button>
                      <Button size="small" color="error" onClick={() => setRejecting(request)}>
                        Reject
                      </Button>
                    </Stack>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">Nothing to review here.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        {bucket !== "pending" && (
          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(0);
            }}
          />
        )}
      </TableContainer>

      <RejectLeaveRequestDialog
        open={Boolean(rejecting)}
        loading={rejectMutation.isPending}
        onClose={() => setRejecting(null)}
        onConfirm={(reason) => rejecting && rejectMutation.mutate({ id: rejecting.id, reason })}
      />
    </>
  );
}
