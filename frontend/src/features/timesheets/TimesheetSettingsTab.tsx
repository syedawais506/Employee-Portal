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
  require_project_and_description: boolean;
  warn_on_weekend: boolean;
  require_finance_approval: boolean;
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
      require_project_and_description: true,
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
      require_project_and_description: config.require_project_and_description,
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
      require_project_and_description: values.require_project_and_description,
      warn_on_weekend: values.warn_on_weekend,
      require_finance_approval: values.require_finance_approval,
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
            name="require_project_and_description"
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
  );
}
