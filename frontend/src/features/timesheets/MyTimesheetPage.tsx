import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { Alert, Button, Chip, IconButton, Stack, Typography } from "@mui/material";

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
import { TimesheetCalendar } from "@/features/timesheets/TimesheetCalendar";
import { TimesheetEntryFormDialog } from "@/features/timesheets/TimesheetEntryFormDialog";
import type { TimesheetEntry } from "@/types";
import { computePeriodBounds, formatPeriodLabel, getMonthGridDates, shiftPeriod, toISODate } from "@/utils/timesheetPeriod";

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
  const [formState, setFormState] = useState<{ open: boolean; editing: TimesheetEntry | null; date: string }>({
    open: false,
    editing: null,
    date: toISODate(new Date()),
  });
  const [pendingDelete, setPendingDelete] = useState<TimesheetEntry | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: config } = useQuery({ queryKey: ["timesheets", "config"], queryFn: getTimesheetConfig });
  const { data: myProjects } = useQuery({ queryKey: ["projects", "mine"], queryFn: listMyProjects });

  const periodType = config?.period_type ?? "weekly";
  const weekStartDay = config?.week_start_day ?? 0;
  const [periodStart, periodEnd] = useMemo(
    () => computePeriodBounds(periodType, weekStartDay, refDate),
    [periodType, weekStartDay, refDate],
  );
  const periodStartIso = toISODate(periodStart);
  const periodEndIso = toISODate(periodEnd);

  const gridDates = useMemo(() => getMonthGridDates(refDate, weekStartDay), [refDate, weekStartDay]);
  const gridStartIso = toISODate(gridDates[0]);
  const gridEndIso = toISODate(gridDates[gridDates.length - 1]);

  const { data: entries } = useQuery({
    queryKey: ["timesheets", "entries", gridStartIso, gridEndIso],
    queryFn: () => listMyTimesheetEntries(gridStartIso, gridEndIso),
    enabled: Boolean(config),
  });

  const entriesByDate = useMemo(() => {
    const map: Record<string, TimesheetEntry[]> = {};
    for (const entry of entries ?? []) {
      (map[entry.entry_date] ??= []).push(entry);
    }
    return map;
  }, [entries]);

  const { data: submissions } = useQuery({
    queryKey: ["timesheets", "submissions", "mine"],
    queryFn: listMyTimesheetSubmissions,
  });
  const currentSubmission = submissions?.find(
    (s) => s.period_start === periodStartIso && s.period_end === periodEndIso,
  );
  const isLocked = currentSubmission?.status === "approved";

  const periodEntries = (entries ?? []).filter((e) => e.entry_date >= periodStartIso && e.entry_date <= periodEndIso);
  const periodTotalHours = periodEntries.reduce((sum, e) => sum + Number(e.hours), 0);
  const canSubmitPeriod = !isLocked && periodEntries.some((e) => e.status === "draft");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["timesheets", "entries"] });
    queryClient.invalidateQueries({ queryKey: ["timesheets", "submissions"] });
  };

  const createMutation = useMutation({
    mutationFn: createTimesheetEntry,
    onSuccess: () => {
      invalidate();
      setFormState((s) => ({ ...s, open: false, editing: null }));
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<TimesheetEntryInput> }) =>
      updateTimesheetEntry(id, payload),
    onSuccess: () => {
      invalidate();
      setFormState((s) => ({ ...s, open: false, editing: null }));
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTimesheetEntry,
    onSuccess: () => {
      invalidate();
      setPendingDelete(null);
      setFormState((s) => ({ ...s, open: false, editing: null }));
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => submitTimesheetPeriod(periodStartIso),
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  function openCreate(dateIso: string) {
    setErrorMessage(null);
    setFormState({ open: true, editing: null, date: dateIso });
  }

  function openEdit(entry: TimesheetEntry) {
    setErrorMessage(null);
    setFormState({ open: true, editing: entry, date: entry.entry_date });
  }

  function onFormSubmit(values: TimesheetEntryInput) {
    if (formState.editing) {
      updateMutation.mutate({
        id: formState.editing.id,
        payload: {
          hours: values.hours,
          is_billable: values.is_billable,
          work_type: values.work_type,
          description: values.description,
        },
      });
    } else {
      createMutation.mutate(values);
    }
  }

  return (
    <>
      <PageHeader
        title="My Timesheet"
        subtitle="Click a date to log hours against your assigned projects, then submit the period for approval."
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
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Typography variant="body2" color="text.secondary">
            {periodTotalHours.toFixed(2)}h this period
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={() => {
              const todayIso = toISODate(new Date());
              const defaultDate = todayIso >= periodStartIso && todayIso <= periodEndIso ? todayIso : periodStartIso;
              openCreate(defaultDate);
            }}
            disabled={isLocked}
          >
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

      <TimesheetCalendar
        days={gridDates}
        currentMonth={refDate.getMonth()}
        periodStart={periodStart}
        periodEnd={periodEnd}
        weekStartDay={weekStartDay}
        entriesByDate={entriesByDate}
        warnOnWeekend={config?.warn_on_weekend ?? true}
        isLocked={isLocked}
        onDayClick={openCreate}
        onEntryClick={openEdit}
      />

      <TimesheetEntryFormDialog
        open={formState.open}
        projects={myProjects ?? []}
        editing={formState.editing}
        defaultDate={formState.date}
        errorMessage={errorMessage}
        submitting={createMutation.isPending || updateMutation.isPending}
        deleting={deleteMutation.isPending}
        onClose={() => setFormState((s) => ({ ...s, open: false, editing: null }))}
        onSubmit={onFormSubmit}
        onDelete={() => formState.editing && setPendingDelete(formState.editing)}
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
