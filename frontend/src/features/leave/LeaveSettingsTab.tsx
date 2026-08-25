import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import {
  Alert,
  Button,
  Checkbox,
  FormControlLabel,
  Grid,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import {
  createHoliday,
  createLeaveType,
  deleteHoliday,
  deleteLeaveType,
  getLeaveSettings,
  listHolidays,
  listLeaveTypes,
  runLeaveCarryForward,
  updateHoliday,
  updateLeaveSettings,
  updateLeaveType,
  type HolidayUpdateInput,
  type LeaveTypeInput,
} from "@/api/leave";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { HolidayFormDialog } from "@/features/leave/HolidayFormDialog";
import { LeaveTypeFormDialog } from "@/features/leave/LeaveTypeFormDialog";
import type { Holiday, LeaveType } from "@/types";

export function LeaveSettingsTab() {
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: settings } = useQuery({ queryKey: ["leave", "settings"], queryFn: getLeaveSettings });
  const { data: leaveTypes } = useQuery({ queryKey: ["leave", "types"], queryFn: listLeaveTypes });
  const { data: holidays } = useQuery({ queryKey: ["leave", "holidays"], queryFn: () => listHolidays() });

  const [leaveTypeForm, setLeaveTypeForm] = useState<{ open: boolean; editing: LeaveType | null }>({
    open: false,
    editing: null,
  });
  const [pendingDeleteType, setPendingDeleteType] = useState<LeaveType | null>(null);
  const [holidayForm, setHolidayForm] = useState<{ open: boolean; editing: Holiday | null }>({
    open: false,
    editing: null,
  });
  const [pendingDeleteHoliday, setPendingDeleteHoliday] = useState<Holiday | null>(null);
  const [carryForwardYear, setCarryForwardYear] = useState(new Date().getFullYear());

  const settingsMutation = useMutation({
    mutationFn: (requireHrApproval: boolean) => updateLeaveSettings({ require_hr_leave_approval: requireHrApproval }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave", "settings"] });
      setSuccessMessage("Leave settings saved.");
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const leaveTypeMutation = useMutation({
    mutationFn: ({ id, payload }: { id?: string; payload: LeaveTypeInput }) =>
      id ? updateLeaveType(id, payload) : createLeaveType(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave", "types"] });
      setLeaveTypeForm({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteLeaveTypeMutation = useMutation({
    mutationFn: deleteLeaveType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave", "types"] });
      setPendingDeleteType(null);
    },
    onError: (error) => {
      setErrorMessage(extractApiErrorMessage(error));
      setPendingDeleteType(null);
    },
  });

  const holidayMutation = useMutation({
    mutationFn: ({ id, payload }: { id?: string; payload: HolidayUpdateInput }) =>
      id
        ? updateHoliday(id, payload)
        : createHoliday({ date: payload.date ?? "", name: payload.name ?? "", location: payload.location }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave", "holidays"] });
      setHolidayForm({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteHolidayMutation = useMutation({
    mutationFn: deleteHoliday,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave", "holidays"] });
      setPendingDeleteHoliday(null);
    },
  });

  const carryForwardMutation = useMutation({
    mutationFn: () => runLeaveCarryForward(carryForwardYear),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leave", "balances"] });
      setSuccessMessage(`Carried forward balances from ${carryForwardYear} into ${carryForwardYear + 1}.`);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  return (
    <>
      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 3, mb: 4, maxWidth: 640 }}>
        <Typography variant="h3" sx={{ mb: 2 }}>
          Approval Chain
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={settings?.require_hr_leave_approval ?? false}
              onChange={(event) => settingsMutation.mutate(event.target.checked)}
            />
          }
          label="Require an HR sign-off after Manager approval"
        />
      </Paper>

      <Paper variant="outlined" sx={{ p: 3, mb: 4, maxWidth: 640 }}>
        <Typography variant="h3" sx={{ mb: 2 }}>
          Carry Forward
        </Typography>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={6}>
            <TextField
              type="number"
              label="From year"
              fullWidth
              size="small"
              value={carryForwardYear}
              onChange={(event) => setCarryForwardYear(Number(event.target.value))}
            />
          </Grid>
          <Grid item xs={6}>
            <Button
              variant="contained"
              onClick={() => carryForwardMutation.mutate()}
              disabled={carryForwardMutation.isPending}
            >
              Run Carry Forward
            </Button>
          </Grid>
        </Grid>
      </Paper>

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="h3">Leave Types</Typography>
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setLeaveTypeForm({ open: true, editing: null })}
        >
          Add Leave Type
        </Button>
      </Stack>
      <Paper variant="outlined" sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Paid</TableCell>
              <TableCell>Annual quota</TableCell>
              <TableCell>Max carry-forward</TableCell>
              <TableCell>Requires document</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(leaveTypes ?? []).map((leaveType) => (
              <TableRow key={leaveType.id} hover>
                <TableCell>{leaveType.name}</TableCell>
                <TableCell>{leaveType.is_paid ? "Yes" : "No"}</TableCell>
                <TableCell>{leaveType.annual_quota_days ?? "Unlimited"}</TableCell>
                <TableCell>{leaveType.max_carry_forward_days}</TableCell>
                <TableCell>{leaveType.requires_attachment ? "Yes" : "No"}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => setLeaveTypeForm({ open: true, editing: leaveType })}>
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => setPendingDeleteType(leaveType)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {(leaveTypes ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No leave types yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="h3">Holidays</Typography>
        <Button size="small" startIcon={<AddIcon />} onClick={() => setHolidayForm({ open: true, editing: null })}>
          Add Holiday
        </Button>
      </Stack>
      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Applies to</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(holidays ?? []).map((holiday) => (
              <TableRow key={holiday.id} hover>
                <TableCell>{holiday.date}</TableCell>
                <TableCell>{holiday.name}</TableCell>
                <TableCell>{holiday.location ?? "All locations"}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => setHolidayForm({ open: true, editing: holiday })}>
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => setPendingDeleteHoliday(holiday)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {(holidays ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No holidays configured yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <LeaveTypeFormDialog
        open={leaveTypeForm.open}
        editing={leaveTypeForm.editing}
        submitting={leaveTypeMutation.isPending}
        onClose={() => setLeaveTypeForm({ open: false, editing: null })}
        onSubmit={(payload) => leaveTypeMutation.mutate({ id: leaveTypeForm.editing?.id, payload })}
      />
      <ConfirmDialog
        open={Boolean(pendingDeleteType)}
        title="Delete leave type"
        description={`Delete "${pendingDeleteType?.name ?? ""}"? This is only possible if no requests reference it.`}
        confirmLabel="Delete"
        destructive
        loading={deleteLeaveTypeMutation.isPending}
        onClose={() => setPendingDeleteType(null)}
        onConfirm={() => pendingDeleteType && deleteLeaveTypeMutation.mutate(pendingDeleteType.id)}
      />

      <HolidayFormDialog
        open={holidayForm.open}
        editing={holidayForm.editing}
        submitting={holidayMutation.isPending}
        onClose={() => setHolidayForm({ open: false, editing: null })}
        onSubmit={(payload) => holidayMutation.mutate({ id: holidayForm.editing?.id, payload })}
      />
      <ConfirmDialog
        open={Boolean(pendingDeleteHoliday)}
        title="Delete holiday"
        description={`Remove "${pendingDeleteHoliday?.name ?? ""}" from the holiday calendar?`}
        confirmLabel="Delete"
        destructive
        loading={deleteHolidayMutation.isPending}
        onClose={() => setPendingDeleteHoliday(null)}
        onConfirm={() => pendingDeleteHoliday && deleteHolidayMutation.mutate(pendingDeleteHoliday.id)}
      />
    </>
  );
}
