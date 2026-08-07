import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";

import type { Department } from "@/types";

interface DepartmentFormValues {
  name: string;
  parent_department_id: string;
  cost_center_code: string;
}

interface DepartmentFormDialogProps {
  open: boolean;
  initial?: Department | null;
  departments: Department[];
  errorMessage?: string | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: { name: string; parent_department_id: string | null; cost_center_code: string | null }) => void;
}

export function DepartmentFormDialog({
  open,
  initial,
  departments,
  errorMessage,
  submitting,
  onClose,
  onSubmit,
}: DepartmentFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<DepartmentFormValues>({
    defaultValues: { name: "", parent_department_id: "", cost_center_code: "" },
  });

  useEffect(() => {
    if (open) {
      reset({
        name: initial?.name ?? "",
        parent_department_id: initial?.parent_department_id ?? "",
        cost_center_code: initial?.cost_center_code ?? "",
      });
    }
  }, [open, initial, reset]);

  function submit(values: DepartmentFormValues) {
    onSubmit({
      name: values.name,
      parent_department_id: values.parent_department_id || null,
      cost_center_code: values.cost_center_code || null,
    });
  }

  const selectableParents = departments.filter((d) => d.id !== initial?.id);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initial ? "Edit Department" : "New Department"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
          <Controller
            name="name"
            control={control}
            rules={{ required: "Name is required" }}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Department name"
                autoFocus
                fullWidth
                error={Boolean(fieldState.error)}
                helperText={fieldState.error?.message}
              />
            )}
          />
          <Controller
            name="parent_department_id"
            control={control}
            render={({ field }) => (
              <TextField {...field} select label="Parent department" fullWidth>
                <MenuItem value="">None</MenuItem>
                {selectableParents.map((dept) => (
                  <MenuItem key={dept.id} value={dept.id}>
                    {dept.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
          <Controller
            name="cost_center_code"
            control={control}
            render={({ field }) => <TextField {...field} label="Cost center code" fullWidth />}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(submit)} disabled={submitting}>
          {initial ? "Save changes" : "Create department"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
