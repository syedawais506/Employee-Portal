import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem, TextField } from "@mui/material";

import type { HolidayUpdateInput } from "@/api/leave";
import { EMPLOYEE_LOCATIONS, type Holiday } from "@/types";

interface HolidayFormDialogProps {
  open: boolean;
  editing: Holiday | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: HolidayUpdateInput) => void;
}

interface FormValues {
  date: string;
  name: string;
  location: string;
}

const EMPTY_VALUES: FormValues = { date: "", name: "", location: "" };

export function HolidayFormDialog({ open, editing, submitting, onClose, onSubmit }: HolidayFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<FormValues>({ defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(editing ? { date: editing.date, name: editing.name, location: editing.location ?? "" } : EMPTY_VALUES);
  }, [open, editing, reset]);

  function submit(values: FormValues) {
    onSubmit({
      date: values.date,
      name: values.name,
      location: values.location || null,
      clear_location: values.location === "",
    });
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{editing ? "Edit Holiday" : "New Holiday"}</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12}>
            <Controller
              name="date"
              control={control}
              rules={{ required: true }}
              render={({ field }) => (
                <TextField {...field} type="date" label="Date" fullWidth InputLabelProps={{ shrink: true }} />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="name"
              control={control}
              rules={{ required: "Name is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Name"
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          </Grid>
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
                  helperText="Only employees at this location will see it and have it excluded from business-day counts"
                >
                  <MenuItem value="">All locations</MenuItem>
                  {EMPLOYEE_LOCATIONS.map((location) => (
                    <MenuItem key={location} value={location}>
                      {location}
                    </MenuItem>
                  ))}
                </TextField>
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
