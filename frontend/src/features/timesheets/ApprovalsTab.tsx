import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Checkbox,
  Chip,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import {
  approveTimesheetSubmission,
  bulkApproveTimesheetSubmissions,
  listTimesheetSubmissions,
  rejectTimesheetSubmission,
} from "@/api/timesheets";
import { RejectSubmissionDialog } from "@/features/timesheets/RejectSubmissionDialog";
import type { TimesheetSubmission } from "@/types";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  submitted: "info",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
};

export function ApprovalsTab() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("submitted");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selected, setSelected] = useState<string[]>([]);
  const [rejecting, setRejecting] = useState<TimesheetSubmission | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["timesheets", "submissions", "queue", statusFilter, page, pageSize],
    queryFn: () => listTimesheetSubmissions(page + 1, pageSize, statusFilter || undefined),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["timesheets", "submissions"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard", "timesheet"] });
    setSelected([]);
  };

  const approveMutation = useMutation({
    mutationFn: approveTimesheetSubmission,
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => rejectTimesheetSubmission(id, reason),
    onSuccess: () => {
      invalidate();
      setRejecting(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const bulkApproveMutation = useMutation({
    mutationFn: bulkApproveTimesheetSubmissions,
    onSuccess: (result) => {
      invalidate();
      if (result.failed.length > 0) {
        setErrorMessage(`${result.failed.length} submission(s) could not be approved.`);
      }
    },
  });

  const items = data?.items ?? [];
  const allSelected = items.length > 0 && selected.length === items.length;

  return (
    <>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <TextField
          select
          size="small"
          label="Status"
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value);
            setPage(0);
            setSelected([]);
          }}
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">All statuses</MenuItem>
          <MenuItem value="submitted">Submitted</MenuItem>
          <MenuItem value="manager_approved">Manager approved</MenuItem>
          <MenuItem value="approved">Approved</MenuItem>
          <MenuItem value="rejected">Rejected</MenuItem>
        </TextField>
        <Button
          variant="contained"
          disabled={selected.length === 0 || bulkApproveMutation.isPending}
          onClick={() => bulkApproveMutation.mutate(selected)}
        >
          Approve Selected ({selected.length})
        </Button>
      </Stack>

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={allSelected}
                  indeterminate={selected.length > 0 && !allSelected}
                  onChange={(event) => setSelected(event.target.checked ? items.map((s) => s.id) : [])}
                />
              </TableCell>
              <TableCell>Employee</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Total hours</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((submission) => (
              <TableRow key={submission.id} hover>
                <TableCell padding="checkbox">
                  <Checkbox
                    checked={selected.includes(submission.id)}
                    onChange={(event) =>
                      setSelected(
                        event.target.checked
                          ? [...selected, submission.id]
                          : selected.filter((id) => id !== submission.id),
                      )
                    }
                    disabled={submission.status === "approved" || submission.status === "rejected"}
                  />
                </TableCell>
                <TableCell>{submission.employee_name}</TableCell>
                <TableCell>
                  {submission.period_start} – {submission.period_end}
                </TableCell>
                <TableCell>{submission.total_hours}</TableCell>
                <TableCell>
                  <Chip label={submission.status.replace("_", " ")} size="small" color={STATUS_COLOR[submission.status]} />
                </TableCell>
                <TableCell align="right">
                  {(submission.status === "submitted" || submission.status === "manager_approved") && (
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" onClick={() => approveMutation.mutate(submission.id)}>
                        Approve
                      </Button>
                      <Button size="small" color="error" onClick={() => setRejecting(submission)}>
                        Reject
                      </Button>
                    </Stack>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">Nothing to review here.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
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
      </TableContainer>

      <RejectSubmissionDialog
        open={Boolean(rejecting)}
        loading={rejectMutation.isPending}
        onClose={() => setRejecting(null)}
        onConfirm={(reason) => rejecting && rejectMutation.mutate({ id: rejecting.id, reason })}
      />
    </>
  );
}
