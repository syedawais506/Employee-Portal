import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getAttendanceSettings, updateAttendanceSettings } from "@/api/attendance";

export function AttendanceSettingsTab() {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState(true);
  const [mode, setMode] = useState<"check_in_out" | "timesheet">("check_in_out");
  const [shiftStart, setShiftStart] = useState("");
  const [shiftEnd, setShiftEnd] = useState("");
  const [gracePeriod, setGracePeriod] = useState(15);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: settings } = useQuery({ queryKey: ["attendance", "settings"], queryFn: getAttendanceSettings });

  useEffect(() => {
    if (!settings) return;
    setEnabled(settings.enabled);
    setMode(settings.mode);
    setShiftStart(settings.shift_start.slice(0, 5));
    setShiftEnd(settings.shift_end.slice(0, 5));
    setGracePeriod(settings.grace_period_minutes);
  }, [settings]);

  const moduleMutation = useMutation({
    mutationFn: () => updateAttendanceSettings({ enabled, mode }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attendance", "settings"] });
      setSuccessMessage("Attendance settings saved.");
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const shiftMutation = useMutation({
    mutationFn: () =>
      updateAttendanceSettings({
        shift_start: `${shiftStart}:00`,
        shift_end: `${shiftEnd}:00`,
        grace_period_minutes: gracePeriod,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attendance", "settings"] });
      setSuccessMessage("Shift settings saved.");
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  return (
    <Stack spacing={3}>
      {successMessage && (
        <Alert severity="success" onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 3, maxWidth: 480 }}>
        <Typography variant="h3" sx={{ mb: 1 }}>
          Attendance Tracking
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Turn attendance off entirely, or choose how it's tracked. When disabled, employees stop seeing an
          Attendance page at all.
        </Typography>
        <Stack spacing={2}>
          <FormControlLabel
            control={<Switch checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />}
            label="Enable attendance tracking for this company"
          />
          <TextField
            select
            label="Tracking method"
            fullWidth
            size="small"
            disabled={!enabled}
            value={mode}
            onChange={(event) => setMode(event.target.value as "check_in_out" | "timesheet")}
            helperText={
              mode === "timesheet"
                ? "Employees don't check in/out — a day is marked present automatically when they submit a timesheet covering it."
                : "Employees check in and out themselves each day."
            }
          >
            <MenuItem value="check_in_out">Check-in / check-out</MenuItem>
            <MenuItem value="timesheet">Timesheet-based</MenuItem>
          </TextField>
          <Button
            variant="contained"
            onClick={() => moduleMutation.mutate()}
            disabled={moduleMutation.isPending}
            sx={{ alignSelf: "flex-start" }}
          >
            Save
          </Button>
        </Stack>
      </Paper>

      {mode === "check_in_out" && (
        <Paper variant="outlined" sx={{ p: 3, maxWidth: 480 }}>
          <Typography variant="h3" sx={{ mb: 1 }}>
            Shift Hours
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Used to flag late check-ins (after the grace period) and compute overtime at check-out. Applies
            company-wide — there's no per-department override yet.
          </Typography>
          <Stack spacing={2}>
            <TextField
              label="Shift start"
              type="time"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={shiftStart}
              onChange={(event) => setShiftStart(event.target.value)}
            />
            <TextField
              label="Shift end"
              type="time"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={shiftEnd}
              onChange={(event) => setShiftEnd(event.target.value)}
            />
            <TextField
              label="Grace period (minutes)"
              type="number"
              fullWidth
              size="small"
              value={gracePeriod}
              onChange={(event) => setGracePeriod(Number(event.target.value))}
            />
            <Button
              variant="contained"
              onClick={() => shiftMutation.mutate()}
              disabled={shiftMutation.isPending}
              sx={{ alignSelf: "flex-start" }}
            >
              Save
            </Button>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
