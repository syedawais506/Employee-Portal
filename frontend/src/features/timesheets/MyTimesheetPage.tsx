import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
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
  createTimesheetEntry,
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

export function MyTimesheetPage() {
  const queryClient = useQueryClient();
  const [refDate, setRefDate] = useState(new Date());
  const [formState, setFormState] = useState<{ open: boolean; editing: TimesheetEntry | null }>({
    open: false,
    editing: null,
  });
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

  const { data: entries, isLoading } = useQuery({
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
  const totalHours = (entries ?? []).reduce((sum, e) => sum + Number(e.hours), 0);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["timesheets", "entries"] });
    queryClient.invalidateQueries({ queryKey: ["timesheets", "submissions"] });
  };

  const createMutation = useMutation({
    mutationFn: createTimesheetEntry,
    onSuccess: () => {
      invalidate();
      setFormState({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<TimesheetEntryInput> }) =>
      updateTimesheetEntry(id, payload),
    onSuccess: () => {
      invalidate();
      setFormState({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTimesheetEntry,
    onSuccess: () => {
      invalidate();
      setPendingDelete(null);
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => submitTimesheetPeriod(periodStartIso),
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  function openCreate() {
    setErrorMessage(null);
    setFormState({ open: true, editing: null });
  }

  function openEdit(entry: TimesheetEntry) {
    setErrorMessage(null);
    setFormState({ open: true, editing: entry });
  }

  function onFormSubmit(values: TimesheetEntryInput) {
    if (formState.editing) {
      updateMutation.mutate({ id: formState.editing.id, payload: { hours: values.hours, is_billable: values.is_billable, work_type: values.work_type, description: values.description } });
    } else {
      createMutation.mutate(values);
    }
  }

  const canSubmitPeriod = !isLocked && (entries ?? []).some((e) => e.status === "draft");

  return (
    <>
      <PageHeader title="My Timesheet" subtitle="Log hours against your assigned projects and submit for approval." />

      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
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
        <Stack direction="row" spacing={1.5}>
          <Button variant="outlined" startIcon={<AddIcon />} onClick={openCreate} disabled={isLocked}>
            Log Time
          </Button>
          <Button
            variant="contained"
            onClick={() => submitMutation.mutate()}
            disabled={!canSubmitPeriod || submitMutation.isPending}
          >
            Submit Period
          </Button>
        </Stack>
      </Stack>

      {currentSubmission?.status === "rejected" && currentSubmission.rejection_reason && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Rejected: {currentSubmission.rejection_reason}. Edit the entries below and resubmit.
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
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(entries ?? []).map((entry) => (
              <TableRow key={entry.id} hover>
                <TableCell>
                  {entry.entry_date}
                  {entry.is_weekend && <Chip label="Weekend" size="small" sx={{ ml: 1 }} />}
                </TableCell>
                <TableCell>{entry.project_name}</TableCell>
                <TableCell>{entry.hours}</TableCell>
                <TableCell>{entry.is_billable ? "Yes" : "No"}</TableCell>
                <TableCell>{entry.work_type.replace("_", " ")}</TableCell>
                <TableCell>{entry.description ?? "—"}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => openEdit(entry)} disabled={isLocked}>
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => setPendingDelete(entry)} disabled={isLocked}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && (entries ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No time logged for this period yet.
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
        open={formState.open}
        projects={myProjects ?? []}
        editing={formState.editing}
        defaultDate={periodStartIso}
        errorMessage={errorMessage}
        submitting={createMutation.isPending || updateMutation.isPending}
        onClose={() => setFormState({ open: false, editing: null })}
        onSubmit={onFormSubmit}
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
