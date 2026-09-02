import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Paper, Stack, TextField, Typography } from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getAttendanceSettings, updateAttendanceSettings } from "@/api/attendance";

export function AttendanceSettingsTab() {
  const queryClient = useQueryClient();
  const [shiftStart, setShiftStart] = useState("");
  const [shiftEnd, setShiftEnd] = useState("");
  const [gracePeriod, setGracePeriod] = useState(15);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: settings } = useQuery({ queryKey: ["attendance", "settings"], queryFn: getAttendanceSettings });

  useEffect(() => {
    if (!settings) return;
    setShiftStart(settings.shift_start.slice(0, 5));
    setShiftEnd(settings.shift_end.slice(0, 5));
    setGracePeriod(settings.grace_period_minutes);
  }, [settings]);

  const saveMutation = useMutation({
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

      <Paper variant="outlined" sx={{ p: 3, maxWidth: 480 }}>
        <Typography variant="h3" sx={{ mb: 1 }}>
          Shift Hours
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Used to flag late check-ins (after the grace period) and compute overtime at check-out. Applies company-wide
          — there's no per-department override yet.
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
          <Button variant="contained" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            Save
          </Button>
        </Stack>
      </Paper>
    </>
  );
}
