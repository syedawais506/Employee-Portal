import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";

import type { LeaveRequestInput } from "@/api/leave";
import type { EmployeeSummary, LeaveType } from "@/types";

interface FormValues {
  leave_type_id: string;
  start_date: string;
  end_date: string;
  reason: string;
  employee_id: string;
}

interface LeaveRequestFormDialogProps {
  open: boolean;
  leaveTypes: LeaveType[];
  employees: EmployeeSummary[];
  canActForOthers: boolean;
  defaultDate: string;
  errorMessage?: string | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: LeaveRequestInput) => void;
}

export function LeaveRequestFormDialog({
  open,
  leaveTypes,
  employees,
  canActForOthers,
  defaultDate,
  errorMessage,
  submitting,
  onClose,
  onSubmit,
}: LeaveRequestFormDialogProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  const { control, handleSubmit, reset, watch } = useForm<FormValues>({
    defaultValues: { leave_type_id: "", start_date: defaultDate, end_date: defaultDate, reason: "", employee_id: "" },
  });

  useEffect(() => {
    if (!open) return;
    reset({ leave_type_id: "", start_date: defaultDate, end_date: defaultDate, reason: "", employee_id: "" });
    setFile(null);
  }, [open, defaultDate, reset]);

  const selectedLeaveType = leaveTypes.find((lt) => lt.id === watch("leave_type_id"));

  function submit(values: FormValues) {
    onSubmit({
      leave_type_id: values.leave_type_id,
      start_date: values.start_date,
      end_date: values.end_date,
      reason: values.reason || undefined,
      employee_id: values.employee_id || undefined,
      file,
    });
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Request Leave</DialogTitle>
      <DialogContent>
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          {canActForOthers && (
            <Grid item xs={12}>
              <Controller
                name="employee_id"
                control={control}
                render={({ field }) => (
                  <TextField {...field} select label="On behalf of" fullWidth helperText="Leave blank to file for yourself">
                    <MenuItem value="">Myself</MenuItem>
                    {employees.map((employee) => (
                      <MenuItem key={employee.id} value={employee.id}>
                        {employee.first_name} {employee.last_name}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Grid>
          )}
          <Grid item xs={12}>
            <Controller
              name="leave_type_id"
              control={control}
              rules={{ required: "Leave type is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  select
                  label="Leave type"
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                >
                  {leaveTypes.map((leaveType) => (
                    <MenuItem key={leaveType.id} value={leaveType.id}>
                      {leaveType.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="start_date"
              control={control}
              rules={{ required: true }}
              render={({ field }) => (
                <TextField {...field} type="date" label="From" fullWidth InputLabelProps={{ shrink: true }} />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="end_date"
              control={control}
              rules={{ required: true }}
              render={({ field }) => (
                <TextField {...field} type="date" label="To" fullWidth InputLabelProps={{ shrink: true }} />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="reason"
              control={control}
              render={({ field }) => <TextField {...field} label="Reason (optional)" fullWidth multiline minRows={2} />}
            />
          </Grid>
          <Grid item xs={12}>
            <input
              type="file"
              hidden
              ref={fileInputRef}
              accept="application/pdf,image/png,image/jpeg"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                event.target.value = "";
              }}
            />
            <Button startIcon={<AttachFileIcon />} onClick={() => fileInputRef.current?.click()}>
              {file ? "Replace attachment" : "Attach document"}
            </Button>
            {file && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {file.name}
              </Typography>
            )}
            {selectedLeaveType?.requires_attachment && !file && (
              <Typography variant="caption" color="warning.main" display="block">
                {selectedLeaveType.name} requires a supporting document.
              </Typography>
            )}
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(submit)} disabled={submitting}>
          Submit Request
        </Button>
      </DialogActions>
    </Dialog>
  );
}
