import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  MenuItem,
  TextField,
} from "@mui/material";

import type { TimesheetReminderRuleInput, TimesheetReminderRuleUpdateInput } from "@/api/timesheets";
import { EMPLOYEE_LOCATIONS, type TimesheetReminderRule } from "@/types";

interface TimesheetReminderRuleFormDialogProps {
  open: boolean;
  editing: TimesheetReminderRule | null;
  takenLocations: (string | null)[];
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: TimesheetReminderRuleInput | TimesheetReminderRuleUpdateInput) => void;
}

interface FormValues {
  location: string;
  cadence: "weekly" | "monthly";
  grace_days: string;
  enabled: boolean;
}

const EMPTY_VALUES: FormValues = { location: "", cadence: "weekly", grace_days: "0", enabled: true };

export function TimesheetReminderRuleFormDialog({
  open,
  editing,
  takenLocations,
  submitting,
  onClose,
  onSubmit,
}: TimesheetReminderRuleFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<FormValues>({ defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(
      editing
        ? {
            location: editing.location ?? "",
            cadence: editing.cadence,
            grace_days: String(editing.grace_days),
            enabled: editing.enabled,
          }
        : EMPTY_VALUES,
    );
  }, [open, editing, reset]);

  function submit(values: FormValues) {
    if (editing) {
      onSubmit({ enabled: values.enabled, cadence: values.cadence, grace_days: Number(values.grace_days) });
    } else {
      onSubmit({
        location: values.location || null,
        enabled: values.enabled,
        cadence: values.cadence,
        grace_days: Number(values.grace_days),
      });
    }
  }

  const availableLocations = EMPLOYEE_LOCATIONS.filter((location) => !takenLocations.includes(location));
  const defaultAlreadyTaken = takenLocations.includes(null);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{editing ? "Edit Reminder Rule" : "New Reminder Rule"}</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12}>
            <Controller
              name="location"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Applies to"
                  fullWidth
                  disabled={Boolean(editing)}
                  helperText={
                    editing
                      ? "Location can't be changed after creation — delete and recreate the rule instead"
                      : "Which employees this cadence applies to, by their Location field"
                  }
                >
                  <MenuItem value="" disabled={!editing && defaultAlreadyTaken}>
                    Default (all other locations)
                  </MenuItem>
                  {(editing ? EMPLOYEE_LOCATIONS : availableLocations).map((location) => (
                    <MenuItem key={location} value={location}>
                      {location}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="cadence"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Cadence" fullWidth>
                  <MenuItem value="weekly">Weekly</MenuItem>
                  <MenuItem value="monthly">Monthly</MenuItem>
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="grace_days"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  type="number"
                  label="Grace days"
                  fullWidth
                  inputProps={{ min: 0, max: 30 }}
                  helperText="Days after the period ends before nagging starts"
                />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="enabled"
              control={control}
              render={({ field }) => (
                <FormControlLabel control={<Checkbox {...field} checked={field.value} />} label="Enabled" />
              )}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(submit)} disabled={submitting}>
          {editing ? "Save changes" : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
