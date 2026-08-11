import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import {
  Alert,
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

import type { TimesheetEntryInput } from "@/api/timesheets";
import type { MyProject, TimesheetEntry } from "@/types";

interface TimesheetEntryFormDialogProps {
  open: boolean;
  projects: MyProject[];
  editing: TimesheetEntry | null;
  defaultDate: string;
  errorMessage?: string | null;
  submitting?: boolean;
  deleting?: boolean;
  onClose: () => void;
  onSubmit: (values: TimesheetEntryInput) => void;
  onDelete?: () => void;
}

export function TimesheetEntryFormDialog({
  open,
  projects,
  editing,
  defaultDate,
  errorMessage,
  submitting,
  deleting,
  onClose,
  onSubmit,
  onDelete,
}: TimesheetEntryFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<TimesheetEntryInput>({
    defaultValues: {
      project_id: "",
      entry_date: defaultDate,
      hours: "",
      is_billable: true,
      work_type: "office",
      description: "",
    },
  });

  useEffect(() => {
    if (!open) return;
    if (editing) {
      reset({
        project_id: editing.project_id,
        entry_date: editing.entry_date,
        hours: editing.hours,
        is_billable: editing.is_billable,
        work_type: editing.work_type,
        description: editing.description ?? "",
      });
    } else {
      reset({
        project_id: "",
        entry_date: defaultDate,
        hours: "",
        is_billable: true,
        work_type: "office",
        description: "",
      });
    }
  }, [open, editing, defaultDate, reset]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{editing ? "Edit Timesheet Entry" : "Log Time"}</DialogTitle>
      <DialogContent>
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12} sm={6}>
            <Controller
              name="project_id"
              control={control}
              rules={{ required: "Project is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  select
                  label="Project"
                  fullWidth
                  disabled={Boolean(editing)}
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                >
                  {projects.map((project) => (
                    <MenuItem key={project.id} value={project.id}>
                      {project.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="entry_date"
              control={control}
              rules={{ required: true }}
              render={({ field }) => (
                <TextField
                  {...field}
                  type="date"
                  label="Date"
                  fullWidth
                  disabled={Boolean(editing)}
                  InputLabelProps={{ shrink: true }}
                />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="hours"
              control={control}
              rules={{ required: "Hours are required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  type="number"
                  label="Hours"
                  fullWidth
                  inputProps={{ step: "0.25", min: "0.25", max: "24" }}
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="work_type"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Work type" fullWidth>
                  <MenuItem value="office">Office</MenuItem>
                  <MenuItem value="remote">Remote</MenuItem>
                  <MenuItem value="client_site">Client site</MenuItem>
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  value={field.value ?? ""}
                  label="Description (optional)"
                  fullWidth
                  multiline
                  minRows={2}
                />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="is_billable"
              control={control}
              render={({ field }) => (
                <FormControlLabel control={<Checkbox {...field} checked={field.value} />} label="Billable" />
              )}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        {editing && onDelete && (
          <Button color="error" onClick={onDelete} disabled={deleting} sx={{ mr: "auto" }}>
            Delete
          </Button>
        )}
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(onSubmit)} disabled={submitting}>
          {editing ? "Save changes" : "Save as Draft"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
