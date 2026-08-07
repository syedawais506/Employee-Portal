import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Grid, Stack, TextField, Typography } from "@mui/material";

import { apiClient, extractApiErrorMessage } from "@/api/client";
import { getMyProfile } from "@/api/employees";
import { PageHeader } from "@/components/PageHeader";
import { useAuthStore } from "@/store/authStore";
import type { EmployeeDetail } from "@/types";

async function updateMyPhone(phone: string): Promise<EmployeeDetail> {
  const response = await apiClient.patch<EmployeeDetail>("/employees/me", { phone });
  return response.data;
}

export function MyProfilePage() {
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();
  const [phone, setPhone] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: employee, isLoading } = useQuery({
    queryKey: ["employees", "me"],
    queryFn: getMyProfile,
    enabled: Boolean(user?.employee_id),
  });

  useEffect(() => {
    if (employee) setPhone(employee.phone ?? "");
  }, [employee]);

  const mutation = useMutation({
    mutationFn: updateMyPhone,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees", "me"] }),
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  if (!user?.employee_id) {
    return (
      <Box>
        <PageHeader title="My Profile" />
        <Typography color="text.secondary">
          Super Admin accounts don't have an employee profile — they operate at the platform level.
        </Typography>
      </Box>
    );
  }

  if (isLoading || !employee) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader title="My Profile" subtitle={employee.employee_code} />
      <Card variant="outlined" sx={{ maxWidth: 560 }}>
        <CardContent>
          {errorMessage && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errorMessage}
            </Alert>
          )}
          <Stack spacing={2}>
            <Stack direction="row" spacing={1}>
              <Chip label={employee.status.replace("_", " ")} size="small" />
              <Chip label={employee.designation ?? "No designation"} size="small" variant="outlined" />
            </Stack>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField label="First name" value={employee.first_name} fullWidth disabled />
              </Grid>
              <Grid item xs={6}>
                <TextField label="Last name" value={employee.last_name} fullWidth disabled />
              </Grid>
              <Grid item xs={12}>
                <TextField label="Email" value={employee.email} fullWidth disabled />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Phone"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  fullWidth
                />
              </Grid>
            </Grid>
            <Box>
              <Button variant="contained" onClick={() => mutation.mutate(phone)} disabled={mutation.isPending}>
                Save changes
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
