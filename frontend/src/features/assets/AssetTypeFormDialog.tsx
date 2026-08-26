import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from "@mui/material";

import type { AssetType } from "@/types";

interface FormValues {
  name: string;
}

interface AssetTypeFormDialogProps {
  open: boolean;
  editing: AssetType | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (name: string) => void;
}

export function AssetTypeFormDialog({ open, editing, submitting, onClose, onSubmit }: AssetTypeFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<FormValues>({ defaultValues: { name: "" } });

  useEffect(() => {
    if (!open) return;
    reset({ name: editing?.name ?? "" });
  }, [open, editing, reset]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{editing ? "Edit Asset Type" : "New Asset Type"}</DialogTitle>
      <DialogContent>
        <Controller
          name="name"
          control={control}
          rules={{ required: "Name is required" }}
          render={({ field, fieldState }) => (
            <TextField
              {...field}
              label="Name"
              fullWidth
              autoFocus
              sx={{ mt: 1 }}
              error={Boolean(fieldState.error)}
              helperText={fieldState.error?.message}
            />
          )}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit((values) => onSubmit(values.name))} disabled={submitting}>
          {editing ? "Save changes" : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
