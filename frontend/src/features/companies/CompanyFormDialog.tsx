import { Controller, useForm } from "react-hook-form";
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from "@mui/material";

import type { CompanyInput } from "@/api/companies";

interface CompanyFormDialogProps {
  open: boolean;
  errorMessage?: string | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: CompanyInput) => void;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function CompanyFormDialog({ open, errorMessage, submitting, onClose, onSubmit }: CompanyFormDialogProps) {
  const { control, handleSubmit, reset, setValue, watch } = useForm<CompanyInput>({
    defaultValues: { name: "", slug: "", admin_email: "", admin_first_name: "", admin_last_name: "" },
  });

  const name = watch("name");

  function handleClose() {
    reset();
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>New Company</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          {errorMessage && <Alert severity="error">{errorMessage}</Alert>}

          <Controller
            name="name"
            control={control}
            rules={{ required: "Company name is required" }}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Company name"
                autoFocus
                fullWidth
                error={Boolean(fieldState.error)}
                helperText={fieldState.error?.message}
                onChange={(event) => {
                  field.onChange(event);
                  setValue("slug", slugify(event.target.value));
                }}
              />
            )}
          />
          <Controller
            name="slug"
            control={control}
            rules={{ required: "Slug is required", pattern: { value: /^[a-z0-9-]+$/, message: "Lowercase letters, numbers, and hyphens only" } }}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Slug"
                fullWidth
                helperText={fieldState.error?.message ?? `Used in identifiers, e.g. ${slugify(name || "your-company")}`}
                error={Boolean(fieldState.error)}
              />
            )}
          />
          <Controller
            name="admin_first_name"
            control={control}
            rules={{ required: "First name is required" }}
            render={({ field, fieldState }) => (
              <TextField {...field} label="Admin first name" fullWidth error={Boolean(fieldState.error)} helperText={fieldState.error?.message} />
            )}
          />
          <Controller
            name="admin_last_name"
            control={control}
            rules={{ required: "Last name is required" }}
            render={({ field, fieldState }) => (
              <TextField {...field} label="Admin last name" fullWidth error={Boolean(fieldState.error)} helperText={fieldState.error?.message} />
            )}
          />
          <Controller
            name="admin_email"
            control={control}
            rules={{ required: "Admin email is required" }}
            render={({ field, fieldState }) => (
              <TextField
                {...field}
                label="Admin email"
                type="email"
                fullWidth
                error={Boolean(fieldState.error)}
                helperText={fieldState.error?.message ?? "They'll receive an email to set their password."}
              />
            )}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(onSubmit)} disabled={submitting}>
          Create company
        </Button>
      </DialogActions>
    </Dialog>
  );
}
