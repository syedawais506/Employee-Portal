import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import {
  Alert,
  Button,
  Chip,
  Grid,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { listMyProjects } from "@/api/projects";
import {
  deleteTimesheetEntry,
  getTimesheetConfig,
  listMyTimesheetEntries,
  submitTimesheetPeriod,
  updateTimesheetEntry,
  type TimesheetEntryInput,
} from "@/api/timesheets";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { TimesheetEntryFormDialog } from "@/features/timesheets/TimesheetEntryFormDialog";
import type { TimesheetEntry } from "@/types";
import { computePeriodBounds, toISODate } from "@/utils/timesheetPeriod";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  draft: "default",
  submitted: "info",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
};

export function DraftsTab() {
  const queryClient = useQueryClient();
  const { data: config } = useQuery({ queryKey: ["timesheets", "config"], queryFn: getTimesheetConfig });

  const defaultRange = useMemo(() => {
    const [start, end] = computePeriodBounds(config?.period_type ?? "weekly", config?.week_start_day ?? 0, new Date());
    return { from: toISODate(start), to: toISODate(end) };
  }, [config]);

  const [range, setRange] = useState(defaultRange);
  const [editing, setEditing] = useState<TimesheetEntry | null>(null);
  const [pendingDelete, setPendingDelete] = useState<TimesheetEntry | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: myProjects } = useQuery({ queryKey: ["projects", "mine"], queryFn: listMyProjects });

  const rangeValid = Boolean(range.from) && Boolean(range.to) && range.from <= range.to;
  const { data: entries } = useQuery({
    queryKey: ["timesheets", "entries", range.from, range.to],
    queryFn: () => listMyTimesheetEntries(range.from, range.to),
    enabled: rangeValid,
  });

  const isEditable = (entry: TimesheetEntry) => entry.status === "draft" || entry.status === "rejected";
  const totalHours = (entries ?? []).reduce((sum, e) => sum + Number(e.hours), 0);
  const canSubmit = rangeValid && (entries ?? []).some((e) => isEditable(e));

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
    mutationFn: () => submitTimesheetPeriod(range.from, range.to),
    onSuccess: () => {
      invalidate();
      setErrorMessage(null);
      setSuccessMessage(`Submitted ${range.from} – ${range.to} for approval.`);
    },
    onError: (error) => {
      setSuccessMessage(null);
      setErrorMessage(extractApiErrorMessage(error));
    },
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
        subtitle="Pick a date range to review what you've logged, then submit whatever's still draft or rejected."
      />

      <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
        <Grid item xs={6} sm={3}>
          <TextField
            type="date"
            label="From"
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
            value={range.from}
            onChange={(event) => {
              setSuccessMessage(null);
              setRange((r) => ({ ...r, from: event.target.value }));
            }}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <TextField
            type="date"
            label="To"
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
            value={range.to}
            onChange={(event) => {
              setSuccessMessage(null);
              setRange((r) => ({ ...r, to: event.target.value }));
            }}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <Stack direction="row" spacing={1.5} justifyContent={{ sm: "flex-end" }}>
            <Button
              variant="contained"
              onClick={() => submitMutation.mutate()}
              disabled={!canSubmit || submitMutation.isPending}
            >
              Submit
            </Button>
          </Stack>
        </Grid>
      </Grid>

      {!rangeValid && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          "To" must be on or after "From".
        </Alert>
      )}
      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}
      {rangeValid && (entries ?? []).length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Nothing logged in this range yet — add time from the My Timesheet calendar first.
        </Alert>
      )}

      <Paper variant="outlined">
        <TableContainer>
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
            {rangeValid && (entries ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No entries in this range.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        </TableContainer>
      </Paper>

      <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
        Total: {totalHours.toFixed(2)} hours
      </Typography>

      <TimesheetEntryFormDialog
        open={Boolean(editing)}
        projects={myProjects ?? []}
        editing={editing}
        defaultDate={editing?.entry_date ?? range.from}
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
