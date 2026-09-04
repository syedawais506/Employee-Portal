import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Button, Card, CardContent, Chip, CircularProgress, Grid, IconButton, Stack, Typography } from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { listDepartments } from "@/api/departments";
import { getEmployee, listEmployees, setEmployeeRoles, updateEmployee } from "@/api/employees";
import { listRoles } from "@/api/roles";
import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import { EmployeeFormDialog, type EmployeeFormValues } from "@/features/employees/EmployeeFormDialog";
import { useAuthStore } from "@/store/authStore";

const ONBOARDING_STATUS_LABEL: Record<string, string> = {
  invited: "Onboarding: Invited",
  submitted: "Onboarding: Submitted",
  hr_approved: "Onboarding: HR Approved",
  completed: "Onboarding Complete",
};

function Field({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1">{value || "—"}</Typography>
    </Box>
  );
}

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const canManageRoles = useAuthStore((state) => state.hasPermission("role", "update"));

  const { data: employee, isLoading } = useQuery({
    queryKey: ["employees", id],
    queryFn: () => getEmployee(id as string),
    enabled: Boolean(id),
  });

  const { data: departments } = useQuery({ queryKey: ["departments", "all"], queryFn: () => listDepartments(1, 100) });
  const { data: managers } = useQuery({
    queryKey: ["employees", "managers"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });
  const { data: roles } = useQuery({ queryKey: ["roles"], queryFn: listRoles, enabled: canManageRoles });

  const updateMutation = useMutation({
    mutationFn: async (values: EmployeeFormValues) => {
      await updateEmployee(id as string, {
        first_name: values.first_name,
        last_name: values.last_name,
        phone: values.phone || null,
        department_id: values.department_id || null,
        designation: values.designation || null,
        manager_id: values.manager_id || null,
        employment_type: values.employment_type,
        location: values.location || null,
        birth_date: values.birth_date || null,
        status: values.status,
      });
      const currentRoleIds = employee?.roles.map((role) => role.id).sort() ?? [];
      const nextRoleIds = [...values.role_ids].sort();
      if (canManageRoles && JSON.stringify(currentRoleIds) !== JSON.stringify(nextRoleIds)) {
        await setEmployeeRoles(id as string, values.role_ids);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees", id] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setEditOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  if (isLoading || !employee) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/employees")} sx={{ mb: 2 }}>
        Back to Employees
      </Button>

      <PageHeader
        title={`${employee.first_name} ${employee.last_name}`}
        subtitle={employee.employee_code}
        actions={
          <Stack direction="row" spacing={1}>
            {employee.onboarding_status !== "completed" && (
              <PermissionGate module="onboarding" action="view">
                <Button size="small" variant="outlined" onClick={() => navigate(`/onboarding/review/${employee.id}`)}>
                  Review Onboarding
                </Button>
              </PermissionGate>
            )}
            <PermissionGate module="employee" action="update">
              <IconButton onClick={() => setEditOpen(true)}>
                <EditOutlinedIcon />
              </IconButton>
            </PermissionGate>
          </Stack>
        }
      />

      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
            <Chip label={employee.status.replace("_", " ")} size="small" color={employee.status === "active" ? "success" : "default"} />
            <Chip label={employee.employment_type.replace("_", " ")} size="small" variant="outlined" />
            {employee.location && <Chip label={employee.location} size="small" variant="outlined" />}
            <Chip
              label={ONBOARDING_STATUS_LABEL[employee.onboarding_status] ?? employee.onboarding_status}
              size="small"
              color={employee.onboarding_status === "completed" ? "success" : "warning"}
              variant="outlined"
            />
          </Stack>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <Field label="Email" value={employee.email} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Phone" value={employee.phone ?? ""} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Department" value={employee.department?.name ?? ""} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Designation" value={employee.designation ?? ""} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field
                label="Manager"
                value={employee.manager ? `${employee.manager.first_name} ${employee.manager.last_name}` : ""}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Joining Date" value={employee.joining_date ?? ""} />
            </Grid>
            <Grid item xs={12}>
              <Typography variant="caption" color="text.secondary">
                Roles
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                {employee.roles.length > 0 ? (
                  employee.roles.map((role) => <Chip key={role.id} label={role.name} size="small" />)
                ) : (
                  <Typography variant="body1">—</Typography>
                )}
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <EmployeeFormDialog
        open={editOpen}
        mode="edit"
        initial={employee}
        departments={departments?.items ?? []}
        managers={managers?.items ?? []}
        roles={roles ?? []}
        canManageRoles={canManageRoles}
        errorMessage={errorMessage}
        submitting={updateMutation.isPending}
        onClose={() => setEditOpen(false)}
        onSubmit={(values) => updateMutation.mutate(values)}
      />
    </>
  );
}
