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
  FormGroup,
  Grid,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";

import { EMPLOYEE_LOCATIONS, type Department, type EmployeeDetail, type EmployeeSummary, type Role } from "@/types";

export interface EmployeeFormValues {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  department_id: string;
  designation: string;
  manager_id: string;
  employment_type: string;
  location: string;
  joining_date: string;
  birth_date: string;
  status: string;
  role_ids: string[];
}

interface EmployeeFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  initial?: EmployeeDetail | null;
  departments: Department[];
  managers: EmployeeSummary[];
  roles: Role[];
  canManageRoles?: boolean;
  errorMessage?: string | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: EmployeeFormValues) => void;
}

const EMPLOYMENT_TYPES = ["full_time", "part_time", "contract", "intern"];
const STATUSES = ["active", "on_leave", "exited"];

export function EmployeeFormDialog({
  open,
  mode,
  initial,
  departments,
  managers,
  roles,
  canManageRoles = mode === "create",
  errorMessage,
  submitting,
  onClose,
  onSubmit,
}: EmployeeFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<EmployeeFormValues>({
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      phone: "",
      department_id: "",
      designation: "",
      manager_id: "",
      employment_type: "full_time",
      location: "",
      joining_date: "",
      birth_date: "",
      status: "active",
      role_ids: [],
    },
  });

  useEffect(() => {
    if (open) {
      reset({
        email: initial?.email ?? "",
        first_name: initial?.first_name ?? "",
        last_name: initial?.last_name ?? "",
        phone: initial?.phone ?? "",
        department_id: initial?.department?.id ?? "",
        designation: initial?.designation ?? "",
        manager_id: initial?.manager?.id ?? "",
        employment_type: initial?.employment_type ?? "full_time",
        location: initial?.location ?? "",
        joining_date: initial?.joining_date ?? "",
        birth_date: initial?.birth_date ?? "",
        status: initial?.status ?? "active",
        role_ids: initial?.roles.map((role) => role.id) ?? [],
      });
    }
  }, [open, initial, reset]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{mode === "create" ? "New Employee" : "Edit Employee"}</DialogTitle>
      <DialogContent>
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={6}>
            <Controller
              name="first_name"
              control={control}
              rules={{ required: "Required" }}
              render={({ field, fieldState }) => (
                <TextField {...field} label="First name" fullWidth error={Boolean(fieldState.error)} helperText={fieldState.error?.message} />
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="last_name"
              control={control}
              rules={{ required: "Required" }}
              render={({ field, fieldState }) => (
                <TextField {...field} label="Last name" fullWidth error={Boolean(fieldState.error)} helperText={fieldState.error?.message} />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="email"
              control={control}
              rules={{ required: "Required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Email"
                  type="email"
                  fullWidth
                  disabled={mode === "edit"}
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="phone"
              control={control}
              render={({ field }) => <TextField {...field} label="Phone" fullWidth />}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="designation"
              control={control}
              render={({ field }) => <TextField {...field} label="Designation" fullWidth />}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="department_id"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Department" fullWidth>
                  <MenuItem value="">None</MenuItem>
                  {departments.map((dept) => (
                    <MenuItem key={dept.id} value={dept.id}>
                      {dept.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="manager_id"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Manager" fullWidth>
                  <MenuItem value="">None</MenuItem>
                  {managers
                    .filter((m) => m.id !== initial?.id)
                    .map((m) => (
                      <MenuItem key={m.id} value={m.id}>
                        {m.first_name} {m.last_name}
                      </MenuItem>
                    ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="employment_type"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Employment type" fullWidth>
                  {EMPLOYMENT_TYPES.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type.replace("_", " ")}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="location"
              control={control}
              render={({ field }) => (
                <TextField {...field} select label="Location" fullWidth>
                  <MenuItem value="">None</MenuItem>
                  {EMPLOYEE_LOCATIONS.map((location) => (
                    <MenuItem key={location} value={location}>
                      {location}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={6}>
            {mode === "create" ? (
              <Controller
                name="joining_date"
                control={control}
                render={({ field }) => (
                  <TextField {...field} type="date" label="Joining date" fullWidth InputLabelProps={{ shrink: true }} />
                )}
              />
            ) : (
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <TextField {...field} select label="Status" fullWidth>
                    {STATUSES.map((status) => (
                      <MenuItem key={status} value={status}>
                        {status.replace("_", " ")}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            )}
          </Grid>
          <Grid item xs={6}>
            <Controller
              name="birth_date"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  type="date"
                  label="Birthday (optional)"
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  helperText="Shown in the Birthdays This Week dashboard widget — leave blank to opt out"
                />
              )}
            />
          </Grid>

          {canManageRoles && roles.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                Roles
              </Typography>
              {mode === "edit" && (
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                  Granting the Admin role gives this employee full access to this company's data and settings.
                </Typography>
              )}
              <Controller
                name="role_ids"
                control={control}
                render={({ field }) => (
                  <FormGroup row>
                    {roles.map((role) => (
                      <FormControlLabel
                        key={role.id}
                        control={
                          <Checkbox
                            checked={field.value.includes(role.id)}
                            onChange={(event) => {
                              field.onChange(
                                event.target.checked
                                  ? [...field.value, role.id]
                                  : field.value.filter((id) => id !== role.id),
                              );
                            }}
                          />
                        }
                        label={role.name}
                      />
                    ))}
                  </FormGroup>
                )}
              />
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(onSubmit)} disabled={submitting}>
          {mode === "create" ? "Create employee" : "Save changes"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
