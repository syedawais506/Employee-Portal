import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  Grid,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getTimesheetConfig, updateTimesheetConfig, type TimesheetConfigUpdateInput } from "@/api/timesheets";

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
  reminder_enabled: boolean;
  reminder_after_days: number;
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
      reminder_enabled: false,
      reminder_after_days: 3,
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
      reminder_enabled: config.reminder_enabled,
      reminder_after_days: config.reminder_after_days,
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
      reminder_enabled: values.reminder_enabled,
      reminder_after_days: Number(values.reminder_after_days),
    });
  }

  return (
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

      <Typography variant="h3" sx={{ mt: 4, mb: 1 }}>
        Submission Reminders
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        When enabled, anyone whose most recent submission has gone stale past the threshold below gets an email and
        an in-app reminder every day until they submit again — not just once.
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Controller
            name="reminder_enabled"
            control={control}
            render={({ field }) => (
              <FormControlLabel
                control={<Checkbox {...field} checked={field.value} />}
                label="Remind employees who haven't submitted a timesheet recently"
              />
            )}
          />
        </Grid>
        <Grid item xs={6}>
          <Controller
            name="reminder_after_days"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                type="number"
                label="Remind after (days)"
                fullWidth
                inputProps={{ min: 1, max: 90 }}
                helperText="Days since their last submission before the reminder starts"
              />
            )}
          />
        </Grid>
      </Grid>
      <Button variant="contained" sx={{ mt: 3 }} onClick={handleSubmit(onSubmit)} disabled={updateMutation.isPending}>
        Save Settings
      </Button>
    </Paper>
  );
}
