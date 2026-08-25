import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, TextField } from "@mui/material";

import type { HolidayInput } from "@/api/leave";
import type { Holiday } from "@/types";

interface HolidayFormDialogProps {
  open: boolean;
  editing: Holiday | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: HolidayInput) => void;
}

const EMPTY_VALUES: HolidayInput = { date: "", name: "" };

export function HolidayFormDialog({ open, editing, submitting, onClose, onSubmit }: HolidayFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<HolidayInput>({ defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(editing ? { date: editing.date, name: editing.name } : EMPTY_VALUES);
  }, [open, editing, reset]);

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
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(onSubmit)} disabled={submitting}>
          {editing ? "Save changes" : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
