import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import PersonRemoveIcon from "@mui/icons-material/PersonRemove";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { listEmployees } from "@/api/employees";
import { addProjectMember, getProject, removeProjectMember, updateProject } from "@/api/projects";
import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import type { ProjectRole } from "@/types";

const STATUS_OPTIONS = ["active", "on_hold", "completed", "cancelled"];

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

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [newMemberId, setNewMemberId] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<ProjectRole>("member");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: project, isLoading } = useQuery({
    queryKey: ["projects", id],
    queryFn: () => getProject(id as string),
    enabled: Boolean(id),
  });

  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["projects", id] });
    queryClient.invalidateQueries({ queryKey: ["projects"] });
  }

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateProject(id as string, { status }),
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const addMemberMutation = useMutation({
    mutationFn: () => addProjectMember(id as string, { employee_id: newMemberId, role_on_project: newMemberRole }),
    onSuccess: () => {
      invalidate();
      setNewMemberId("");
      setNewMemberRole("member");
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (employeeId: string) => removeProjectMember(id as string, employeeId),
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  if (isLoading || !project) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  const availableEmployees = (employees?.items ?? []).filter(
    (employee) => !project.members.some((member) => member.employee_id === employee.id),
  );

  return (
    <>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/projects")} sx={{ mb: 2 }}>
        Back to Projects
      </Button>

      <PageHeader
        title={project.name}
        subtitle={project.client?.name ?? "No client"}
        actions={
          <PermissionGate module="project" action="update">
            <TextField
              select
              size="small"
              value={project.status}
              onChange={(event) => statusMutation.mutate(event.target.value)}
              sx={{ minWidth: 160 }}
            >
              {STATUS_OPTIONS.map((status) => (
                <MenuItem key={status} value={status}>
                  {status.replace("_", " ")}
                </MenuItem>
              ))}
            </TextField>
          </PermissionGate>
        }
      />

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
            <Chip label={project.status.replace("_", " ")} size="small" />
            <Chip label={project.is_billable ? "Billable" : "Non-billable"} size="small" variant="outlined" />
          </Stack>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <Field label="Client" value={project.client?.name ?? ""} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Budget" value={project.budget ? `$${project.budget}` : ""} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="Start date" value={project.start_date ?? ""} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Field label="End date" value={project.end_date ?? ""} />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h3" sx={{ mb: 2 }}>
            Team Members
          </Typography>
          <Stack spacing={1} sx={{ mb: 3 }}>
            {project.members.map((member) => (
              <Stack key={member.employee_id} direction="row" justifyContent="space-between" alignItems="center">
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2">
                    {member.first_name} {member.last_name}
                  </Typography>
                  <Chip label={member.role_on_project} size="small" variant="outlined" />
                </Stack>
                <PermissionGate module="project" action="update">
                  <IconButton size="small" onClick={() => removeMemberMutation.mutate(member.employee_id)}>
                    <PersonRemoveIcon fontSize="small" />
                  </IconButton>
                </PermissionGate>
              </Stack>
            ))}
            {project.members.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No members assigned yet.
              </Typography>
            )}
          </Stack>

          <PermissionGate module="project" action="update">
            <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
              <TextField
                select
                size="small"
                label="Add member"
                value={newMemberId}
                onChange={(event) => setNewMemberId(event.target.value)}
                sx={{ minWidth: 220 }}
              >
                {availableEmployees.map((employee) => (
                  <MenuItem key={employee.id} value={employee.id}>
                    {employee.first_name} {employee.last_name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                size="small"
                label="Role"
                value={newMemberRole}
                onChange={(event) => setNewMemberRole(event.target.value as ProjectRole)}
                sx={{ minWidth: 140 }}
              >
                <MenuItem value="member">Member</MenuItem>
                <MenuItem value="manager">Manager</MenuItem>
              </TextField>
              <Button
                variant="contained"
                startIcon={<PersonAddIcon />}
                disabled={!newMemberId || addMemberMutation.isPending}
                onClick={() => addMemberMutation.mutate()}
              >
                Add
              </Button>
            </Stack>
          </PermissionGate>
        </CardContent>
      </Card>
    </>
  );
}
