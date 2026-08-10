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

import type { ProjectInput } from "@/api/projects";
import type { Client, EmployeeSummary } from "@/types";

interface ProjectFormDialogProps {
  open: boolean;
  clients: Client[];
  employees: EmployeeSummary[];
  errorMessage?: string | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: ProjectInput) => void;
}

interface FormValues {
  name: string;
  client_id: string;
  budget: string;
  is_billable: boolean;
  start_date: string;
  end_date: string;
  member_employee_ids: string[];
}

export function ProjectFormDialog({
  open,
  clients,
  employees,
  errorMessage,
  submitting,
  onClose,
  onSubmit,
}: ProjectFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: {
      name: "",
      client_id: "",
      budget: "",
      is_billable: true,
      start_date: "",
      end_date: "",
      member_employee_ids: [],
    },
  });

  function handleClose() {
    reset();
    onClose();
  }

  function submit(values: FormValues) {
    onSubmit({
      name: values.name,
      client_id: values.client_id || null,
      budget: values.budget || null,
      is_billable: values.is_billable,
      start_date: values.start_date || null,
      end_date: values.end_date || null,
      member_ids: values.member_employee_ids.map((employee_id) => ({ employee_id, role_on_project: "member" })),
    });
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>New Project</DialogTitle>
      <DialogContent>
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12}>
            <Controller
              name="name"
              control={control}
              rules={{ required: "Project name is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Project name"
                  autoFocus
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="client_id"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Client" fullWidth>
                  <MenuItem value="">None</MenuItem>
                  {clients.map((client) => (
                    <MenuItem key={client.id} value={client.id}>
                      {client.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="budget"
              control={control}
              render={({ field }) => <TextField {...field} label="Budget" type="number" fullWidth />}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="start_date"
              control={control}
              render={({ field }) => (
                <TextField {...field} type="date" label="Start date" fullWidth InputLabelProps={{ shrink: true }} />
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="end_date"
              control={control}
              render={({ field }) => (
                <TextField {...field} type="date" label="End date" fullWidth InputLabelProps={{ shrink: true }} />
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
          <Grid item xs={12}>
            <Controller
              name="member_employee_ids"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Team members"
                  fullWidth
                  SelectProps={{ multiple: true }}
                  helperText="You can also add or remove members later from the project page"
                >
                  {employees.map((employee) => (
                    <MenuItem key={employee.id} value={employee.id}>
                      {employee.first_name} {employee.last_name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(submit)} disabled={submitting}>
          Create project
        </Button>
      </DialogActions>
    </Dialog>
  );
}
