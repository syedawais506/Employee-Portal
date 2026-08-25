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
  TextField,
} from "@mui/material";

import type { LeaveTypeInput } from "@/api/leave";
import type { LeaveType } from "@/types";

interface LeaveTypeFormDialogProps {
  open: boolean;
  editing: LeaveType | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: LeaveTypeInput) => void;
}

const EMPTY_VALUES: LeaveTypeInput = {
  name: "",
  is_paid: true,
  annual_quota_days: null,
  max_carry_forward_days: 0,
  requires_attachment: false,
};

export function LeaveTypeFormDialog({ open, editing, submitting, onClose, onSubmit }: LeaveTypeFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<LeaveTypeInput>({ defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(editing ? { ...editing } : EMPTY_VALUES);
  }, [open, editing, reset]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{editing ? "Edit Leave Type" : "New Leave Type"}</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
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
          <Grid item xs={12} sm={6}>
            <Controller
              name="annual_quota_days"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  value={field.value ?? ""}
                  onChange={(event) => field.onChange(event.target.value === "" ? null : Number(event.target.value))}
                  type="number"
                  label="Annual quota (days)"
                  fullWidth
                  helperText="Leave blank for unlimited/untracked"
                />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="max_carry_forward_days"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  onChange={(event) => field.onChange(Number(event.target.value))}
                  type="number"
                  label="Max carry-forward (days)"
                  fullWidth
                />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="is_paid"
              control={control}
              render={({ field }) => (
                <FormControlLabel control={<Checkbox {...field} checked={field.value} />} label="Paid leave" />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="requires_attachment"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={<Checkbox {...field} checked={field.value} />}
                  label="Requires a supporting document"
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
