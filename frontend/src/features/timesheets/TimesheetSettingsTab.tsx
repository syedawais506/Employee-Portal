import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import {
  Alert,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  Grid,
  IconButton,
  MenuItem,
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
import {
  createTimesheetReminderRule,
  deleteTimesheetReminderRule,
  getTimesheetConfig,
  listTimesheetReminderRules,
  updateTimesheetConfig,
  updateTimesheetReminderRule,
  type TimesheetConfigUpdateInput,
  type TimesheetReminderRuleInput,
  type TimesheetReminderRuleUpdateInput,
} from "@/api/timesheets";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { TimesheetReminderRuleFormDialog } from "@/features/timesheets/TimesheetReminderRuleFormDialog";
import type { TimesheetReminderRule } from "@/types";

const WEEKDAYS = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];

interface FormValues {
  period_type: string;
  week_start_day: number;
  min_hours_per_day: string;
  max_hours_per_day: string;
  require_description: boolean;
  warn_on_weekend: boolean;
  require_finance_approval: boolean;
}

function ReminderRulesSection() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<TimesheetReminderRule | null>(null);
  const [pendingDelete, setPendingDelete] = useState<TimesheetReminderRule | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: rules } = useQuery({
    queryKey: ["timesheets", "reminder-rules"],
    queryFn: listTimesheetReminderRules,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["timesheets", "reminder-rules"] });

  const createMutation = useMutation({
    mutationFn: (payload: TimesheetReminderRuleInput) => createTimesheetReminderRule(payload),
    onSuccess: () => {
      invalidate();
      setFormOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; payload: TimesheetReminderRuleUpdateInput }) =>
      updateTimesheetReminderRule(vars.id, vars.payload),
    onSuccess: () => {
      invalidate();
      setFormOpen(false);
      setEditing(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTimesheetReminderRule(id),
    onSuccess: () => {
      invalidate();
      setPendingDelete(null);
    },
  });

  const takenLocations = (rules ?? []).map((rule) => rule.location);

  return (
    <Paper variant="outlined" sx={{ p: 3, maxWidth: 640, mt: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h3">Submission Reminders</Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => {
            setEditing(null);
            setErrorMessage(null);
            setFormOpen(true);
          }}
        >
          Add Rule
        </Button>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Configure a reminder cadence per employee location — e.g. weekly for US employees, monthly for India. Cadence
        is calendar-anchored (the most recently fully-elapsed week or month, not a rolling day count) and, once past
        grace days, re-fires every day until a submission covers that period. The "Default" rule applies to any
        location with no rule of its own.
      </Typography>
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorMessage}
        </Alert>
      )}
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Applies to</TableCell>
              <TableCell>Cadence</TableCell>
              <TableCell>Grace days</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(rules ?? []).map((rule) => (
              <TableRow key={rule.id}>
                <TableCell>{rule.location ?? "Default (all other locations)"}</TableCell>
                <TableCell sx={{ textTransform: "capitalize" }}>{rule.cadence}</TableCell>
                <TableCell>{rule.grace_days}</TableCell>
                <TableCell>
                  <Chip
                    label={rule.enabled ? "Enabled" : "Disabled"}
                    size="small"
                    color={rule.enabled ? "success" : "default"}
                  />
                </TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={() => {
                      setEditing(rule);
                      setErrorMessage(null);
                      setFormOpen(true);
                    }}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => setPendingDelete(rule)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {(rules ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 3, color: "text.secondary" }}>
                  No reminder rules configured — employees won't receive submission reminders.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <TimesheetReminderRuleFormDialog
        open={formOpen}
        editing={editing}
        takenLocations={takenLocations}
        submitting={createMutation.isPending || updateMutation.isPending}
        onClose={() => setFormOpen(false)}
        onSubmit={(values) => {
          if (editing) {
            updateMutation.mutate({ id: editing.id, payload: values as TimesheetReminderRuleUpdateInput });
          } else {
            createMutation.mutate(values as TimesheetReminderRuleInput);
          }
        }}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete reminder rule"
        description={`Remove the rule for ${pendingDelete?.location ?? "the default (all other locations)"}? Those employees will stop receiving submission reminders.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </Paper>
  );
}

export function TimesheetSettingsTab() {
  const queryClient = useQueryClient();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data: config } = useQuery({ queryKey: ["timesheets", "config"], queryFn: getTimesheetConfig });

  const { control, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: {
      period_type: "weekly",
      week_start_day: 0,
      min_hours_per_day: "",
      max_hours_per_day: "",
      require_description: false,
      warn_on_weekend: true,
      require_finance_approval: false,
    },
  });

  useEffect(() => {
    if (!config) return;
    reset({
      period_type: config.period_type,
      week_start_day: config.week_start_day,
      min_hours_per_day: config.min_hours_per_day ?? "",
      max_hours_per_day: config.max_hours_per_day ?? "",
      require_description: config.require_description,
      warn_on_weekend: config.warn_on_weekend,
      require_finance_approval: config.require_finance_approval,
    });
  }, [config, reset]);

  const updateMutation = useMutation({
    mutationFn: (payload: TimesheetConfigUpdateInput) => updateTimesheetConfig(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timesheets", "config"] });
      setSuccessMessage("Timesheet settings saved.");
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  function onSubmit(values: FormValues) {
    setSuccessMessage(null);
    updateMutation.mutate({
      period_type: values.period_type,
      week_start_day: Number(values.week_start_day),
      min_hours_per_day: values.min_hours_per_day || null,
      max_hours_per_day: values.max_hours_per_day || null,
      require_description: values.require_description,
      warn_on_weekend: values.warn_on_weekend,
      require_finance_approval: values.require_finance_approval,
    });
  }

  return (
    <>
      <Paper variant="outlined" sx={{ p: 3, maxWidth: 640 }}>
        <Typography variant="h3" sx={{ mb: 2 }}>
          Timesheet Rules
        </Typography>
        {successMessage && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {successMessage}
          </Alert>
        )}
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Controller
              name="period_type"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Period type" fullWidth>
                  <MenuItem value="daily">Daily</MenuItem>
                  <MenuItem value="weekly">Weekly</MenuItem>
                  <MenuItem value="monthly">Monthly</MenuItem>
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="week_start_day"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Week starts on" fullWidth>
                  {WEEKDAYS.map((day) => (
                    <MenuItem key={day.value} value={day.value}>
                      {day.label}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="min_hours_per_day"
              control={control}
              render={({ field }) => (
                <TextField {...field} type="number" label="Min hours / day" fullWidth helperText="Optional" />
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="max_hours_per_day"
              control={control}
              render={({ field }) => (
                <TextField {...field} type="number" label="Max hours / day" fullWidth helperText="Optional" />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="require_description"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox {...field} checked={field.value} />}
                  label="Require a description on every entry"
                />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="warn_on_weekend"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox {...field} checked={field.value} />}
                  label="Flag weekend entries in the timesheet view"
                />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="require_finance_approval"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox {...field} checked={field.value} />}
                  label="Require a Finance sign-off after Manager approval"
                />
              )}
            />
          </Grid>
        </Grid>
        <Button variant="contained" sx={{ mt: 3 }} onClick={handleSubmit(onSubmit)} disabled={updateMutation.isPending}>
          Save Settings
        </Button>
      </Paper>

      <ReminderRulesSection />
    </>
  );
}
