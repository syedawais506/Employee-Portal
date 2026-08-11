import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import {
  Alert,
  Button,
  Chip,
  IconButton,
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
import { listMyProjects } from "@/api/projects";
import {
  deleteTimesheetEntry,
  getTimesheetConfig,
  listMyTimesheetEntries,
  listMyTimesheetSubmissions,
  submitTimesheetPeriod,
  updateTimesheetEntry,
  type TimesheetEntryInput,
} from "@/api/timesheets";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { TimesheetEntryFormDialog } from "@/features/timesheets/TimesheetEntryFormDialog";
import type { TimesheetEntry } from "@/types";
import { computePeriodBounds, formatPeriodLabel, shiftPeriod, toISODate } from "@/utils/timesheetPeriod";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  draft: "default",
  submitted: "info",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  submitted: "Submitted — awaiting manager approval",
  manager_approved: "Manager approved — awaiting finance sign-off",
  approved: "Approved",
  rejected: "Rejected",
};

export function DraftsTab() {
  const queryClient = useQueryClient();
  const [refDate, setRefDate] = useState(new Date());
  const [editing, setEditing] = useState<TimesheetEntry | null>(null);
  const [pendingDelete, setPendingDelete] = useState<TimesheetEntry | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: config } = useQuery({ queryKey: ["timesheets", "config"], queryFn: getTimesheetConfig });
  const { data: myProjects } = useQuery({ queryKey: ["projects", "mine"], queryFn: listMyProjects });

  const periodType = config?.period_type ?? "weekly";
  const [periodStart, periodEnd] = useMemo(
    () => computePeriodBounds(periodType, config?.week_start_day ?? 0, refDate),
    [periodType, config?.week_start_day, refDate],
  );
  const periodStartIso = toISODate(periodStart);
  const periodEndIso = toISODate(periodEnd);

  const { data: entries } = useQuery({
    queryKey: ["timesheets", "entries", periodStartIso, periodEndIso],
    queryFn: () => listMyTimesheetEntries(periodStartIso, periodEndIso),
    enabled: Boolean(config),
  });

  const { data: submissions } = useQuery({
    queryKey: ["timesheets", "submissions", "mine"],
    queryFn: listMyTimesheetSubmissions,
  });
  const currentSubmission = submissions?.find(
    (s) => s.period_start === periodStartIso && s.period_end === periodEndIso,
  );
  const isLocked = currentSubmission?.status === "approved";
  const isEditable = (entry: TimesheetEntry) => !isLocked && entry.status !== "approved";
  const totalHours = (entries ?? []).reduce((sum, e) => sum + Number(e.hours), 0);
  const canSubmitPeriod = !isLocked && (entries ?? []).some((e) => e.status === "draft");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["timesheets", "entries"] });
    queryClient.invalidateQueries({ queryKey: ["timesheets", "submissions"] });
  };

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<TimesheetEntryInput> }) =>
      updateTimesheetEntry(id, payload),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTimesheetEntry,
    onSuccess: () => {
      invalidate();
      setPendingDelete(null);
      setEditing(null);
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => submitTimesheetPeriod(periodStartIso),
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  function onFormSubmit(values: TimesheetEntryInput) {
    if (!editing) return;
    updateMutation.mutate({
      id: editing.id,
      payload: {
        hours: values.hours,
        is_billable: values.is_billable,
        work_type: values.work_type,
        description: values.description,
      },
    });
  }

  return (
    <>
      <PageHeader
        title="Drafts"
        subtitle="Review everything you've logged for the period before submitting it for approval."
      />

      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }} flexWrap="wrap" gap={1}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <IconButton onClick={() => setRefDate(shiftPeriod(periodType, refDate, -1))} size="small">
            <ChevronLeftIcon />
          </IconButton>
          <Typography variant="h3">{formatPeriodLabel(periodStart, periodEnd)}</Typography>
          <IconButton onClick={() => setRefDate(shiftPeriod(periodType, refDate, 1))} size="small">
            <ChevronRightIcon />
          </IconButton>
          {currentSubmission && (
            <Chip
              label={STATUS_LABEL[currentSubmission.status]}
              color={STATUS_COLOR[currentSubmission.status]}
              size="small"
              sx={{ ml: 1 }}
            />
          )}
        </Stack>
        <Button variant="contained" onClick={() => submitMutation.mutate()} disabled={!canSubmitPeriod || submitMutation.isPending}>
          Submit Period
        </Button>
      </Stack>

      {currentSubmission?.status === "rejected" && currentSubmission.rejection_reason && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Rejected: {currentSubmission.rejection_reason}. Edit the entries below and resubmit.
        </Alert>
      )}
      {!canSubmitPeriod && !isLocked && (entries ?? []).length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Nothing logged for this period yet — add time from the My Timesheet calendar first.
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Project</TableCell>
              <TableCell>Hours</TableCell>
              <TableCell>Billable</TableCell>
              <TableCell>Work type</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(entries ?? []).map((entry) => (
              <TableRow key={entry.id} hover>
                <TableCell>{entry.entry_date}</TableCell>
                <TableCell>{entry.project_name}</TableCell>
                <TableCell>{entry.hours}</TableCell>
                <TableCell>{entry.is_billable ? "Yes" : "No"}</TableCell>
                <TableCell>{entry.work_type.replace("_", " ")}</TableCell>
                <TableCell>{entry.description ?? "—"}</TableCell>
                <TableCell>
                  <Chip label={entry.status.replace("_", " ")} size="small" color={STATUS_COLOR[entry.status]} />
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => setEditing(entry)} disabled={!isEditable(entry)}>
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => setPendingDelete(entry)} disabled={!isEditable(entry)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {(entries ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No entries for this period.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
        Total: {totalHours.toFixed(2)} hours
      </Typography>

      <TimesheetEntryFormDialog
        open={Boolean(editing)}
        projects={myProjects ?? []}
        editing={editing}
        defaultDate={editing?.entry_date ?? periodStartIso}
        errorMessage={errorMessage}
        submitting={updateMutation.isPending}
        deleting={deleteMutation.isPending}
        onClose={() => setEditing(null)}
        onSubmit={onFormSubmit}
        onDelete={() => editing && setPendingDelete(editing)}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete timesheet entry"
        description={`Remove ${pendingDelete?.hours ?? ""} hours logged on ${pendingDelete?.entry_date ?? ""}?`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </>
  );
}
